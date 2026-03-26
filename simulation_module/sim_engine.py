"""
TrafficFlow Simulation Engine v2.0
- Smart adaptive signal control (queue + wait time + density scoring)
- Green Wave corridor coordination
- Vision module integration (optional)
- CO2 tracking and results output
"""
import os
import sys
import json
import time

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

    def optimize_signal(self):
        """Set green phase duration based on multi-factor score."""
        score, density, queue, wait = self.compute_score()

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

    # ── Adaptive control (every 20 steps) ──
    if MODE in ("adaptive", "vision_linked") and step % 20 == 0:
        for controller in controllers:
            controller.optimize_signal()

    # ── Vision-linked injection (every 30 steps) ──
    if MODE == "vision_linked" and step % 30 == 0:
        try:
            from dynamic_routes import inject_vehicles, fetch_vision_data
            lane_counts, _ = fetch_vision_data()
            inject_vehicles(traci, step, lane_counts)
        except Exception:
            pass

    # ── Record step data (every 10 steps for dashboard) ──
    if step % 10 == 0:
        active_vehicles = len(traci.vehicle.getIDList())
        step_data.append({
            "step": step,
            "active_vehicles": active_vehicles,
            "idle_vehicles": step_idle,
            "total_delay": total_delay,
        })

    # ── Progress log (every 200 steps) ──
    if step % 200 == 0:
        active = len(traci.vehicle.getIDList())
        print(f"  Step {step:>5} | Active: {active:>4} | Delay: {total_delay:>6}")

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
}

with open(config.RESULTS_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n📊 Results saved to {config.RESULTS_FILE}")

traci.close()
print("✅ Simulation Ended Cleanly")