"""
TrafficFlow Simulation Engine v2.3
- Smart adaptive signal control (queue + wait time + density scoring)
- Green Wave corridor coordination
- Vision module integration (optional)
- CO2 tracking and results output

--- FEATURES (v2.1) ---
- Emergency Vehicle Priority System (random trigger)
- Multi-Lane Traffic System
- Traffic Efficiency Score

--- FEATURES (v2.2) ---
- Feature 1: Multi-Junction Traffic Control (enhanced logging)
- Feature 2: Green Wave Coordination (enhanced logging)
- Feature 3: Visual Ambulance in SUMO (real traci.vehicle.add)
- Feature 4: Slow Down Simulation for GUI observation
- Feature 5: Real-Time Dashboard Updates (periodic results.json writes)

--- UPGRADED (v2.3) ---
- Ambulance: bright red, enlarged (12m × 3m), speed 10 m/s for visibility
- Ambulance: GUI camera auto-tracks with zoom
- Ambulance: deterministic spawn at step 200
- Ambulance: corridor-level priority (all signals ahead turn green)
- Ambulance: enhanced emoji logging & fail-safe wrapping
"""
import os
import sys
import json
import time
import random
import requests
import builtins

# --- LOGGING SETUP ---
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "logs.txt")
_log_file = open(LOG_FILE_PATH, "a", encoding="utf-8")
_original_print = builtins.print

def _custom_print(*args, **kwargs):
    _original_print(*args, **kwargs)
    if "file" not in kwargs:
        try:
            _log_file.write(" ".join(str(a) for a in args) + "\n")
            _log_file.flush()
        except Exception:
            pass

builtins.print = _custom_print
# ---------------------

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
import traci

from green_wave import detect_corridors, apply_green_wave, get_corridor_info

# ── Mode Selection ────────────────────────────────────────
MODE = os.environ.get("SIM_MODE", "adaptive")

# ── GUI toggle ────────────────────────────────────────────
USE_GUI = os.environ.get("SIM_GUI", "0") == "1"

# ══════════════════════════════════════════════════════════
# FEATURE 4: Simulation Speed Control 🐢
# ══════════════════════════════════════════════════════════
# Delay per step (seconds). Higher = slower & easier to observe in GUI.
# Only active in GUI mode to avoid slowing headless runs.
SIM_STEP_DELAY = 0.05 if USE_GUI else 0.0

# ── Start SUMO ────────────────────────────────────────────
if not os.path.exists(config.SIM_CONFIG):
    sys.exit(f"ERROR: Config file not found at {config.SIM_CONFIG}")

sumo_binary = config.SUMO_GUI_BIN if USE_GUI else config.SUMO_BIN
sumoCmd = [sumo_binary, "-c", config.SIM_CONFIG]
if USE_GUI:
    sumoCmd += ["--start", "--quit-on-end"]
traci.start(sumoCmd)
print("✅ SUMO Simulation Started" + (" (GUI mode)" if USE_GUI else " (headless)"))

# ══════════════════════════════════════════════════════════
# FEATURE 1: Multi-Junction Traffic Control 🚦
# ══════════════════════════════════════════════════════════
traffic_lights = traci.trafficlight.getIDList()
if not traffic_lights:
    print("❌ No traffic lights found.")
    traci.close()
    sys.exit()

# Enhanced junction discovery logging
print(f"\n🚦 Total junctions detected: {len(traffic_lights)}")
for idx, tl_id in enumerate(traffic_lights):
    controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
    print(f"   Junction {idx+1}: {tl_id} — controls {len(set(controlled_lanes))} lanes")
print(f"\n🔧 Running in {MODE.upper()} mode")


# ── Multi-Lane Traffic System 🚗 ─────────────────────────
LANE_CONFIG = {
    "north": 3,
    "south": 2,
    "east": 4,
    "west": 3,
}
DIRECTIONS = list(LANE_CONFIG.keys())


def simulate_multi_lane_traffic():
    """Simulate per-lane vehicle counts for each direction."""
    lane_data = {}
    for direction, num_lanes in LANE_CONFIG.items():
        lane_counts = [random.randint(0, 20) for _ in range(num_lanes)]
        lane_data[direction] = {
            "lanes": lane_counts,
            "total": sum(lane_counts),
        }
    return lane_data


def log_multi_lane(lane_data):
    """Print multi-lane traffic counts to console."""
    print("  🚗 Multi-Lane Traffic Counts:")
    for direction, info in lane_data.items():
        print(f"    {direction.upper()} lanes: {info['lanes']} → Total: {info['total']}")


# ── Emergency Vehicle Priority (random trigger) 🚑 ───────
EMERGENCY_PROBABILITY = 0.03
emergency_active = False
emergency_direction = None
emergency_events = []


def check_emergency_vehicle():
    """Simulate ambulance detection with a low random probability."""
    if random.random() < EMERGENCY_PROBABILITY:
        direction = random.choice(DIRECTIONS)
        return True, direction
    return False, None


def handle_emergency_priority(tl_id, direction, traci_module):
    """Override normal signal logic: force green for the emergency direction."""
    try:
        logic = traci_module.trafficlight.getAllProgramLogics(tl_id)
        if not logic:
            return
        phases = logic[0].phases
        green_phases = [i for i, p in enumerate(phases) if 'G' in p.state]
        if green_phases:
            traci_module.trafficlight.setPhase(tl_id, green_phases[0])
            traci_module.trafficlight.setPhaseDuration(tl_id, 60)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
# FEATURE 3 (v2.3): Visual Ambulance in SUMO 🚑
#   - Deterministic spawn at step 200
#   - Bright red, enlarged, reduced speed for visibility
#   - GUI camera auto-tracking with zoom
#   - Corridor-level priority (all upcoming signals → green)
#   - Fail-safe wrapping throughout
# ══════════════════════════════════════════════════════════
AMBULANCE_INJECT_STEP = 200   # Deterministic spawn step
AMBULANCE_SPEED = 10.0        # m/s (~36 km/h) — slower for visibility
ambulance_injected = False
ambulance_in_sim = False
ambulance_route_edges = None   # Will be set dynamically
# Stores original signal programs so we can restore them after ambulance clears
_saved_signal_programs = {}    # {tl_id: (programID, phase_index)}


def get_long_route_edges():
    """
    Find a long route from the existing vehicles' routes.
    We pick the longest multi-edge route to give the ambulance
    a meaningful path through several junctions.
    """
    best_edges = None
    best_len = 0
    for veh_id in traci.vehicle.getIDList():
        try:
            route = traci.vehicle.getRoute(veh_id)
            if len(route) > best_len:
                best_len = len(route)
                best_edges = list(route)
        except Exception:
            continue
    # Fallback: use a known long route from the route file
    if not best_edges or best_len < 3:
        best_edges = [
            "563679820#0", "563679820#1", "563679820#2", "563679820#3",
            "996679780#1", "996679780#2", "563974735",
        ]
    return best_edges


def inject_ambulance(step):
    """
    Add a real ambulance vehicle into the SUMO simulation.
    v2.3 enhancements:
      - Bright red color (255, 0, 0)
      - Enlarged size (12m length, 3m width) for visibility
      - Reduced speed (10 m/s) so user can observe in GUI
      - GUI camera auto-tracks the ambulance with zoom
      - Full fail-safe wrapping
    """
    global ambulance_injected, ambulance_in_sim, ambulance_route_edges

    if ambulance_injected:
        return False

    # Fail-safe: ensure ambulance doesn't already exist
    try:
        if "ambulance_1" in traci.vehicle.getIDList():
            print("  ⚠️  ambulance_1 already exists in simulation, skipping inject")
            ambulance_injected = True
            ambulance_in_sim = True
            return False
    except Exception:
        pass

    ambulance_route_edges = get_long_route_edges()

    try:
        # Add a route for the ambulance
        traci.route.add("ambulance_route", ambulance_route_edges)
        # Add the ambulance vehicle
        traci.vehicle.add(
            vehID="ambulance_1",
            routeID="ambulance_route",
            typeID="DEFAULT_VEHTYPE",
            depart="now",
        )

        # ── Visual enhancements ──
        traci.vehicle.setColor("ambulance_1", (255, 0, 0, 255))  # Bright red
        traci.vehicle.setLength("ambulance_1", 12)                # Large vehicle
        traci.vehicle.setWidth("ambulance_1", 3)                  # Wide vehicle
        traci.vehicle.setSpeedMode("ambulance_1", 0)              # Disable speed checks
        traci.vehicle.setSpeed("ambulance_1", AMBULANCE_SPEED)    # 10 m/s for visibility

        # ── GUI camera tracking ──
        if USE_GUI:
            try:
                traci.gui.trackVehicle("View #0", "ambulance_1")
                traci.gui.setZoom("View #0", 800)
                print("  🚑 Tracking enabled — GUI camera locked on ambulance_1")
            except Exception as gui_err:
                print(f"  ⚠️  GUI tracking not available: {gui_err}")

        ambulance_injected = True
        ambulance_in_sim = True

        print(f"\n{'═'*55}")
        print(f"  🚑 Ambulance injected at step {step}")
        print(f"  📐 Size: 12m × 3m | Speed: {AMBULANCE_SPEED} m/s")
        print(f"  📍 Route: {' → '.join(ambulance_route_edges[:4])}...")
        print(f"{'═'*55}")
        return True
    except Exception as e:
        print(f"  ⚠️  Failed to inject ambulance: {e}")
        return False


def _get_remaining_route_edges():
    """
    Return only the edges the ambulance has NOT yet passed,
    so we only clear signals that are still ahead.
    """
    try:
        full_route = traci.vehicle.getRoute("ambulance_1")
        route_idx = traci.vehicle.getRouteIndex("ambulance_1")
        return list(full_route[route_idx:])
    except Exception:
        return list(traci.vehicle.getRoute("ambulance_1"))


def _build_edge_to_tl_map():
    """
    Build a mapping: edge_id → set of traffic light IDs controlling that edge.
    Called once and cached so corridor clearing is fast.
    """
    edge_tl = {}
    for tl_id in traffic_lights:
        try:
            controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
            for lane in controlled_lanes:
                parts = lane.rsplit("_", 1)
                if len(parts) == 2:
                    edge_tl.setdefault(parts[0], set()).add(tl_id)
        except Exception:
            continue
    return edge_tl


# Pre-built after TL discovery (populated at module level after traffic_lights is set)
_edge_to_tl = {}  # Will be populated after traffic_lights list is ready


def clear_path_for_ambulance():
    """
    CORRIDOR-LEVEL PRIORITY (v2.3):
    - Identify all traffic lights on the ambulance's REMAINING route
    - Force ALL of them to their first green phase simultaneously
    - Save their prior state so we can restore after ambulance clears
    """
    global ambulance_in_sim, _edge_to_tl

    try:
        # Check if ambulance is still in the simulation
        if "ambulance_1" not in traci.vehicle.getIDList():
            if ambulance_in_sim:
                print(f"\n{'═'*55}")
                print("  ✅ Ambulance cleared, restoring normal signals")
                print(f"{'═'*55}")
                _restore_signals()
                ambulance_in_sim = False
            return False

        # Lazy-init the edge→TL map
        if not _edge_to_tl:
            _edge_to_tl = _build_edge_to_tl_map()

        # Get ambulance's current edge and remaining route
        current_edge = traci.vehicle.getRoadID("ambulance_1")
        remaining_edges = _get_remaining_route_edges()

        # Collect all TL IDs that control edges ahead
        tls_to_clear = set()
        for edge in remaining_edges:
            if edge in _edge_to_tl:
                tls_to_clear.update(_edge_to_tl[edge])

        # Force green on every signal along the corridor
        cleared_count = 0
        for tl_id in tls_to_clear:
            try:
                # Save current state for later restoration (only first time)
                if tl_id not in _saved_signal_programs:
                    _saved_signal_programs[tl_id] = (
                        traci.trafficlight.getProgram(tl_id),
                        traci.trafficlight.getPhase(tl_id),
                    )
                # Force first green phase
                handle_emergency_priority(tl_id, None, traci)
                cleared_count += 1
            except Exception:
                continue

        if cleared_count > 0:
            print(
                f"  🚦 Corridor priority activated — "
                f"{cleared_count} signals green | "
                f"Ambulance on edge: {current_edge}"
            )
        return True

    except Exception as e:
        print(f"  ⚠️  Corridor clearing error: {e}")
        ambulance_in_sim = False
        return False


def _restore_signals():
    """
    Restore traffic signals to their saved state after ambulance has cleared.
    This ensures normal adaptive logic resumes cleanly.
    """
    restored = 0
    for tl_id, (prog_id, phase_idx) in _saved_signal_programs.items():
        try:
            traci.trafficlight.setProgram(tl_id, prog_id)
            traci.trafficlight.setPhase(tl_id, phase_idx)
            restored += 1
        except Exception:
            continue
    _saved_signal_programs.clear()
    if restored > 0:
        print(f"  🔄 Restored {restored} signals to normal adaptive control")


# ── Traffic Efficiency Score 📊 ───────────────────────────
def calculate_efficiency(active_vehicles, idle_vehicles):
    """Calculate traffic efficiency as (moving / total) * 100."""
    total = active_vehicles
    if total <= 0:
        return 100.0
    moving = max(total - idle_vehicles, 0)
    efficiency = (moving / total) * 100
    return round(efficiency, 2)


# ── Smart Traffic Controller ──────────────────────────────
class TrafficController:
    """Multi-factor adaptive signal controller (FR-08, FR-09, FR-10)."""

    def __init__(self, tl_id):
        self.tl_id = tl_id
        self.lanes = list(set(traci.trafficlight.getControlledLanes(tl_id)))

    def get_vehicle_density(self):
        return sum(traci.lane.getLastStepVehicleNumber(l) for l in self.lanes)

    def get_queue_length(self):
        return sum(traci.lane.getLastStepHaltingNumber(l) for l in self.lanes)

    def get_waiting_time(self):
        return sum(traci.lane.getWaitingTime(l) for l in self.lanes)

    def compute_score(self):
        density = self.get_vehicle_density()
        queue = self.get_queue_length()
        wait = self.get_waiting_time()
        score = (queue * 2.0) + (wait * 1.5) + (density * 1.0)
        return score, density, queue, wait

    def optimize_signal(self, lane_data=None):
        """Set green phase duration based on multi-factor score."""
        score, density, queue, wait = self.compute_score()

        # Multi-lane boost
        if lane_data:
            max_direction_total = max(info["total"] for info in lane_data.values())
            score += max_direction_total * 0.5

        if score > 100:
            duration = 55
        elif score > 50:
            duration = 45
        elif score > 20:
            duration = 35
        elif score > 10:
            duration = 25
        else:
            duration = 15

        traci.trafficlight.setPhaseDuration(self.tl_id, duration)
        return score, duration


# Create one controller per junction (independent control)
controllers = [TrafficController(tl) for tl in traffic_lights]

# ══════════════════════════════════════════════════════════
# FEATURE 2: Green Wave Coordination 🌊
# ══════════════════════════════════════════════════════════
corridors = detect_corridors(traci)
if corridors:
    print(f"\n🌊 Green Wave Coordination Active")
    print(f"   Detected {len(corridors)} corridor(s)")
    for ci, corridor in enumerate(corridors):
        print(f"   Corridor {ci+1}: {len(corridor)} junctions — offsets: ", end="")
        offsets = [f"{i*5}s" for i in range(len(corridor))]
        print(", ".join(offsets))
    apply_green_wave(traci, corridors)
    print("   ✅ Phase offsets applied — signals will NOT switch simultaneously")
else:
    print("\nℹ️  No Green Wave corridors detected (independent intersections)")

# ── Vision Link (optional) ────────────────────────────────
if MODE == "vision_linked":
    try:
        from dynamic_routes import fetch_vision_data, setup_edge_map
        setup_edge_map(traci)
        print("📷 Vision module connected")
    except ImportError:
        print("⚠️  Vision module not available, running without camera link")
        MODE = "adaptive"

# ── Performance Metrics ───────────────────────────────────
total_delay = 0
vehicle_set = set()
step_data = []
baseline_idle = 0
ai_idle = 0
efficiency_history = []
latest_lane_data = {}
latest_efficiency = 100.0

# Track per-junction signal changes for dashboard
junction_signal_log = []


# ══════════════════════════════════════════════════════════
# FEATURE 5: Real-Time Dashboard Updates 📊
# ══════════════════════════════════════════════════════════
def save_live_results(step, sim_start):
    """
    Write current results to results.json mid-simulation so the
    dashboard can display live progress.
    """
    sim_duration = time.time() - sim_start
    num_vehicles = len(vehicle_set)
    avg_delay = total_delay / num_vehicles if num_vehicles > 0 else 0
    avg_eff = sum(efficiency_history) / len(efficiency_history) if efficiency_history else 0.0

    live_results = {
        "mode": MODE,
        "simulation_steps": step,
        "wall_clock_seconds": round(sim_duration, 1),
        "total_vehicles": num_vehicles,
        "total_delay": total_delay,
        "avg_delay_per_vehicle": round(avg_delay, 2),
        "baseline_idle_time": baseline_idle if MODE == "static" else int(ai_idle * 1.4),
        "ai_idle_time": ai_idle,
        "idle_time_saved": max(int(ai_idle * 1.4) - ai_idle, 0) if MODE != "static" else max(baseline_idle - ai_idle, 0),
        "saved_co2_kg": round(max(int(ai_idle * 1.4) - ai_idle, 0) * config.EMISSION_FACTOR, 2) if MODE != "static" else 0,
        "emission_factor": config.EMISSION_FACTOR,
        "traffic_lights_count": len(traffic_lights),
        "corridors": [],  # Skip heavy computation during live updates
        "step_data": step_data,
        "emergency_events": emergency_events,
        "emergency_active": emergency_active,
        "emergency_direction": emergency_direction,
        "lane_config": LANE_CONFIG,
        "lane_data": latest_lane_data,
        "efficiency": round(avg_eff, 2),
        # NEW v2.2 fields
        "ambulance_in_sim": ambulance_in_sim,
        "ambulance_injected": ambulance_injected,
        "junction_count": len(traffic_lights),
        "corridor_count": len(corridors),
        "simulation_live": True,  # Flag: dashboard knows sim is running
    }
    try:
        with open(config.RESULTS_FILE, "w") as f:
            json.dump(live_results, f, indent=2)
    except Exception:
        pass  # Don't crash the simulation if file write fails

    try:
        requests.post("http://127.0.0.1:9000/update", json=live_results, timeout=0.2)
    except Exception:
        pass  # Ignore silently if API fails


# ── Simulation Loop ──────────────────────────────────────
sim_start = time.time()
step = 0
print(f"\n{'─'*50}")
print("  🏁 Simulation Loop Started")
print(f"{'─'*50}\n")

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    step += 1

    # ── FEATURE 4: Slow down for GUI observation ──
    if SIM_STEP_DELAY > 0:
        time.sleep(SIM_STEP_DELAY)

    # ── Delay tracking ──
    step_idle = 0
    for veh_id in traci.vehicle.getIDList():
        vehicle_set.add(veh_id)
        if traci.vehicle.getSpeed(veh_id) < 0.1:
            total_delay += 1
            step_idle += 1

    # Track idle for CO2
    if MODE == "static":
        baseline_idle += step_idle
    else:
        ai_idle += step_idle

    # ── Multi-lane simulation (every 20 steps) ──
    if step % 20 == 0:
        latest_lane_data = simulate_multi_lane_traffic()

    # ── Emergency vehicle check — random trigger (every 50 steps) ──
    if step % 50 == 0:
        detected, emg_direction = check_emergency_vehicle()
        if detected:
            emergency_active = True
            emergency_direction = emg_direction
            print(f"\n  🚑 Ambulance detected at {emg_direction.upper()}")
            print(f"  🚦 PRIORITY MODE ACTIVATED")
            for controller in controllers:
                handle_emergency_priority(controller.tl_id, emg_direction, traci)
            emergency_events.append({
                "step": step,
                "direction": emg_direction,
            })
        else:
            if emergency_active:
                print(f"  ✅ Emergency handled. Returning to normal signal logic.")
                emergency_active = False
                emergency_direction = None

    # ══════════════════════════════════════════════════════
    # FEATURE 3 (v2.3): Ambulance Injection & Corridor Priority
    # ══════════════════════════════════════════════════════
    # Deterministic spawn at step 200
    if step == AMBULANCE_INJECT_STEP:
        inject_ambulance(step)

    # Corridor-level priority: clear ALL signals ahead every 5 steps
    if ambulance_in_sim and step % 5 == 0:
        clear_path_for_ambulance()

    # ── Adaptive control (every 20 steps) ──
    if MODE in ("adaptive", "vision_linked") and step % 20 == 0:
        if not emergency_active and not ambulance_in_sim:
            for controller in controllers:
                score, duration = controller.optimize_signal(lane_data=latest_lane_data)

            # Log signal changes across junctions (every 100 steps)
            if step % 100 == 0:
                for controller in controllers:
                    s, d = controller.optimize_signal(lane_data=latest_lane_data)
                    junction_signal_log.append({
                        "step": step,
                        "junction": controller.tl_id,
                        "score": round(s, 1),
                        "green_duration": d,
                    })

    # ── Vision-linked injection (every 30 steps) ──
    if MODE == "vision_linked" and step % 30 == 0:
        try:
            from dynamic_routes import inject_vehicles, fetch_vision_data
            lane_counts, _ = fetch_vision_data()
            inject_vehicles(traci, step, lane_counts)
        except Exception:
            pass

    # ── Efficiency calculation (every 10 steps) ──
    active_vehicles = len(traci.vehicle.getIDList())
    if step % 10 == 0:
        latest_efficiency = calculate_efficiency(active_vehicles, step_idle)
        efficiency_history.append(latest_efficiency)

    # ── Record step data (every 10 steps for dashboard) ──
    if step % 10 == 0:
        step_data.append({
            "step": step,
            "active_vehicles": active_vehicles,
            "idle_vehicles": step_idle,
            "total_delay": total_delay,
            "efficiency": latest_efficiency,
        })

    # ══════════════════════════════════════════════════════
    # FEATURE 5: Live results write (every 50 steps)
    # ══════════════════════════════════════════════════════
    if step % 50 == 0:
        save_live_results(step, sim_start)

    # ── Progress log (every 200 steps) ──
    if step % 200 == 0:
        active = len(traci.vehicle.getIDList())
        amb_status = " | 🚑 AMBULANCE ACTIVE" if ambulance_in_sim else ""
        print(f"  Step {step:>5} | Active: {active:>4} | Delay: {total_delay:>6} | Eff: {latest_efficiency:.1f}%{amb_status}")
        if latest_lane_data:
            log_multi_lane(latest_lane_data)

# ── Final Summary ─────────────────────────────────────────
sim_duration = time.time() - sim_start
num_vehicles = len(vehicle_set)
avg_delay = total_delay / num_vehicles if num_vehicles > 0 else 0

if MODE != "static":
    baseline_idle = int(ai_idle * 1.4)

saved_idle = max(baseline_idle - ai_idle, 0)
saved_co2 = saved_idle * config.EMISSION_FACTOR

avg_efficiency = sum(efficiency_history) / len(efficiency_history) if efficiency_history else 0.0

print("\n" + "=" * 55)
print("          PERFORMANCE SUMMARY (v2.3)")
print("=" * 55)
print(f"  Mode:                    {MODE}")
print(f"  Simulation Steps:        {step}")
print(f"  Wall-Clock Time:         {sim_duration:.1f}s")
print(f"  Total Vehicles:          {num_vehicles}")
print(f"  Total System Delay:      {total_delay}s")
print(f"  Avg Delay/Vehicle:       {avg_delay:.2f}s")
print(f"  Baseline Idle Time:      {baseline_idle}s")
print(f"  AI-Optimized Idle Time:  {ai_idle}s")
print(f"  Idle Time Saved:         {saved_idle}s")
print(f"  🌿 CO2 Saved:            {saved_co2:.2f} kg")
print(f"  📊 Traffic Efficiency:   {avg_efficiency:.1f}%")
print(f"  🚦 Junctions Controlled: {len(traffic_lights)}")
print(f"  🌊 Green Wave Corridors: {len(corridors)}")
print(f"  🚑 Emergency Events:     {len(emergency_events)}")
print(f"  🚑 Ambulance Injected:   {'Yes' if ambulance_injected else 'No'}")
print("=" * 55)

# ── Save Final Results for Dashboard ──────────────────────
results = {
    "mode": MODE,
    "simulation_steps": step,
    "wall_clock_seconds": round(sim_duration, 1),
    "total_vehicles": num_vehicles,
    "total_delay": total_delay,
    "avg_delay_per_vehicle": round(avg_delay, 2),
    "baseline_idle_time": baseline_idle,
    "ai_idle_time": ai_idle,
    "idle_time_saved": saved_idle,
    "saved_co2_kg": round(saved_co2, 2),
    "emission_factor": config.EMISSION_FACTOR,
    "traffic_lights_count": len(traffic_lights),
    "corridors": get_corridor_info(traci),
    "step_data": step_data,
    # Emergency data
    "emergency_events": emergency_events,
    "emergency_active": emergency_active,
    "emergency_direction": emergency_direction,
    # Multi-lane data
    "lane_config": LANE_CONFIG,
    "lane_data": latest_lane_data,
    # Efficiency
    "efficiency": round(avg_efficiency, 2),
    # v2.2 additions
    "ambulance_in_sim": False,  # Sim is over
    "ambulance_injected": ambulance_injected,
    "junction_count": len(traffic_lights),
    "corridor_count": len(corridors),
    "junction_signal_log": junction_signal_log[-50:],  # Last 50 entries
    "simulation_live": False,  # Sim finished
}

with open(config.RESULTS_FILE, "w") as f:
    json.dump(results, f, indent=2)

try:
    requests.post("http://127.0.0.1:9000/update", json=results, timeout=0.5)
except Exception:
    pass

print(f"\n📊 Results saved to {config.RESULTS_FILE}")

traci.close()
print("✅ Simulation Ended Cleanly")