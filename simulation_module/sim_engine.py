"""
TrafficFlow Simulation Engine v2.0
- Smart adaptive signal control (queue + wait time + density scoring)
- Green Wave corridor coordination
- Vision module integration (optional)
- CO2 tracking and results output

--- NEW FEATURES (v2.1) ---
- Emergency Vehicle Priority System (Feature 1)
- Multi-Lane Traffic System (Feature 2)
- Traffic Efficiency Score (Feature 3)
"""
import os
import sys
import json
import time
import random  # NEW: for emergency vehicle and multi-lane simulation

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
import traci

from green_wave import detect_corridors, apply_green_wave, get_corridor_info

# ── Mode Selection ────────────────────────────────────────
# "adaptive"      → Smart scoring (queue + wait + density)
# "static"        → Default fixed signal timings
# "vision_linked" → Adaptive + live vehicle injection from camera
MODE = os.environ.get("SIM_MODE", "adaptive")

# ── GUI toggle ────────────────────────────────────────────
# Set SIM_GUI=1 environment variable to open SUMO visual window
USE_GUI = os.environ.get("SIM_GUI", "0") == "1"

# ── Start SUMO ────────────────────────────────────────────
if not os.path.exists(config.SIM_CONFIG):
    sys.exit(f"ERROR: Config file not found at {config.SIM_CONFIG}")

sumo_binary = config.SUMO_GUI_BIN if USE_GUI else config.SUMO_BIN
sumoCmd = [sumo_binary, "-c", config.SIM_CONFIG]
if USE_GUI:
    sumoCmd += ["--start", "--quit-on-end"]  # auto-start, auto-close
traci.start(sumoCmd)
print("✅ SUMO Simulation Started" + (" (GUI mode)" if USE_GUI else " (headless)"))

# ── Discover Traffic Lights ───────────────────────────────
traffic_lights = traci.trafficlight.getIDList()
if not traffic_lights:
    print("❌ No traffic lights found.")
    traci.close()
    sys.exit()

print(f"🚦 Found {len(traffic_lights)} traffic lights")
print(f"🔧 Running in {MODE.upper()} mode\n")


# ══════════════════════════════════════════════════════════
# FEATURE 2: Multi-Lane Traffic System 🚗
# ══════════════════════════════════════════════════════════
# Configuration: number of lanes per direction
LANE_CONFIG = {
    "north": 3,
    "south": 2,
    "east": 4,
    "west": 3,
}

DIRECTIONS = list(LANE_CONFIG.keys())


def simulate_multi_lane_traffic():
    """
    Simulate per-lane vehicle counts for each direction.
    Returns a dict with lane-wise counts and aggregated totals.
    Example: {"north": {"lanes": [10, 5, 7], "total": 22}, ...}
    """
    lane_data = {}
    for direction, num_lanes in LANE_CONFIG.items():
        # Random vehicle count per lane (0-20 vehicles)
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


# ══════════════════════════════════════════════════════════
# FEATURE 1: Emergency Vehicle Priority System 🚑
# ══════════════════════════════════════════════════════════
EMERGENCY_PROBABILITY = 0.03  # 3% chance per check cycle

# Track emergency state across the simulation
emergency_active = False
emergency_direction = None
emergency_events = []  # Log of all emergency events for the dashboard


def check_emergency_vehicle():
    """
    Simulate ambulance detection with a low random probability.
    Returns (is_detected: bool, direction: str or None).
    """
    if random.random() < EMERGENCY_PROBABILITY:
        direction = random.choice(DIRECTIONS)
        return True, direction
    return False, None


def handle_emergency_priority(tl_id, direction, traci_module):
    """
    Override normal signal logic: force green for the emergency direction.
    Uses the first green phase available on the traffic light.
    """
    try:
        logic = traci_module.trafficlight.getAllProgramLogics(tl_id)
        if not logic:
            return
        phases = logic[0].phases
        # Find the first phase with green
        green_phases = [i for i, p in enumerate(phases) if 'G' in p.state]
        if green_phases:
            traci_module.trafficlight.setPhase(tl_id, green_phases[0])
            traci_module.trafficlight.setPhaseDuration(tl_id, 60)  # Extended green
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
# FEATURE 3: Traffic Efficiency Score 📊
# ══════════════════════════════════════════════════════════
def calculate_efficiency(active_vehicles, idle_vehicles):
    """
    Calculate traffic efficiency as (moving / total) * 100.
    Moving vehicles = active - idle (those not halted).
    """
    total = active_vehicles
    if total <= 0:
        return 100.0  # No vehicles = perfect efficiency
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
        """Count vehicles on controlled lanes."""
        return sum(traci.lane.getLastStepVehicleNumber(l) for l in self.lanes)

    def get_queue_length(self):
        """Count halted vehicles (speed < 0.1 m/s) on controlled lanes."""
        return sum(traci.lane.getLastStepHaltingNumber(l) for l in self.lanes)

    def get_waiting_time(self):
        """Total waiting time across controlled lanes."""
        return sum(traci.lane.getWaitingTime(l) for l in self.lanes)

    def compute_score(self):
        """
        Multi-factor score combining density, queue, and wait time.
        Higher score = more congested = needs longer green.
        """
        density = self.get_vehicle_density()
        queue = self.get_queue_length()
        wait = self.get_waiting_time()

        score = (queue * 2.0) + (wait * 1.5) + (density * 1.0)
        return score, density, queue, wait

    def optimize_signal(self, lane_data=None):
        """
        Set green phase duration based on multi-factor score.
        MODIFIED: optionally factor in aggregated multi-lane totals.
        """
        score, density, queue, wait = self.compute_score()

        # FEATURE 2 INTEGRATION: boost score if multi-lane data shows heavy load
        if lane_data:
            max_direction_total = max(info["total"] for info in lane_data.values())
            # Add a lane-based bonus so the signal reacts to high directional volume
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


controllers = [TrafficController(tl) for tl in traffic_lights]

# ── Green Wave Setup ──────────────────────────────────────
corridors = detect_corridors(traci)
if corridors:
    print(f"🌊 Detected {len(corridors)} Green Wave corridors")
    apply_green_wave(traci, corridors)
else:
    print("ℹ️  No Green Wave corridors detected (independent intersections)")

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
step_data = []          # Per-step metrics for dashboard
baseline_idle = 0       # For CO2 calculation
ai_idle = 0

# NEW: Track efficiency and lane data across the simulation
efficiency_history = []
latest_lane_data = {}
latest_efficiency = 100.0

# ── Simulation Loop ──────────────────────────────────────
sim_start = time.time()
step = 0

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    step += 1

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

    # ── FEATURE 2: Multi-lane simulation (every 20 steps) ──
    if step % 20 == 0:
        latest_lane_data = simulate_multi_lane_traffic()

    # ── FEATURE 1: Emergency vehicle check (every 50 steps) ──
    if step % 50 == 0:
        detected, emg_direction = check_emergency_vehicle()
        if detected:
            emergency_active = True
            emergency_direction = emg_direction
            print(f"\n  🚑 Ambulance detected at {emg_direction.upper()}")
            print(f"  🚦 PRIORITY MODE ACTIVATED")
            # Override ALL traffic lights to give priority
            for controller in controllers:
                handle_emergency_priority(controller.tl_id, emg_direction, traci)
            # Record the emergency event
            emergency_events.append({
                "step": step,
                "direction": emg_direction,
            })
        else:
            # Return to normal if no emergency
            if emergency_active:
                print(f"  ✅ Emergency handled. Returning to normal signal logic.")
                emergency_active = False
                emergency_direction = None

    # ── Adaptive control (every 20 steps) ──
    # MODIFIED: pass lane_data to optimize_signal for Feature 2 integration
    if MODE in ("adaptive", "vision_linked") and step % 20 == 0:
        if not emergency_active:  # Skip if emergency override is active
            for controller in controllers:
                controller.optimize_signal(lane_data=latest_lane_data)

    # ── Vision-linked injection (every 30 steps) ──
    if MODE == "vision_linked" and step % 30 == 0:
        try:
            from dynamic_routes import inject_vehicles, fetch_vision_data
            lane_counts, _ = fetch_vision_data()
            inject_vehicles(traci, step, lane_counts)
        except Exception:
            pass

    # ── FEATURE 3: Efficiency calculation (every 10 steps) ──
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
            "efficiency": latest_efficiency,  # NEW: per-step efficiency
        })

    # ── Progress log (every 200 steps) ──
    if step % 200 == 0:
        active = len(traci.vehicle.getIDList())
        print(f"  Step {step:>5} | Active: {active:>4} | Delay: {total_delay:>6} | Efficiency: {latest_efficiency:.1f}%")
        # Log multi-lane data every 200 steps
        if latest_lane_data:
            log_multi_lane(latest_lane_data)

# ── Final Summary ─────────────────────────────────────────
sim_duration = time.time() - sim_start
num_vehicles = len(vehicle_set)
avg_delay = total_delay / num_vehicles if num_vehicles > 0 else 0

# CO2 Calculation (FR-12)
# If running adaptive mode, estimate baseline as 1.4× the adaptive idle
if MODE != "static":
    baseline_idle = int(ai_idle * 1.4)

saved_idle = max(baseline_idle - ai_idle, 0)
saved_co2 = saved_idle * config.EMISSION_FACTOR  # kg CO2

# FEATURE 3: Final efficiency score (average across simulation)
avg_efficiency = sum(efficiency_history) / len(efficiency_history) if efficiency_history else 0.0

print("\n" + "=" * 50)
print("       PERFORMANCE SUMMARY")
print("=" * 50)
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
print(f"  🚑 Emergency Events:     {len(emergency_events)}")
print("=" * 50)

# ── Save Results for Dashboard ────────────────────────────
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

    # ── NEW: Feature 1 – Emergency Vehicle Data ──
    "emergency_events": emergency_events,
    "emergency_active": emergency_active,
    "emergency_direction": emergency_direction,

    # ── NEW: Feature 2 – Multi-Lane Data (last snapshot) ──
    "lane_config": LANE_CONFIG,
    "lane_data": latest_lane_data,

    # ── NEW: Feature 3 – Efficiency Score ──
    "efficiency": round(avg_efficiency, 2),
}

with open(config.RESULTS_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n📊 Results saved to {config.RESULTS_FILE}")

traci.close()
print("✅ Simulation Ended Cleanly")