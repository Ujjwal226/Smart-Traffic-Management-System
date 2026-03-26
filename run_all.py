#!/usr/bin/env python3
"""
TrafficFlow AI – GreenWave  |  One-Click Launcher
===================================================
Runs the full pipeline:
  1. SUMO Simulation (generates results.json)
  2. Streamlit Dashboard (opens in browser)

Usage:
  python3 run_all.py                 # adaptive mode (default)
  python3 run_all.py --mode vision_linked --live-cam 0 # use local webcam!
  python3 run_all.py --mode vision_linked --live-cam "rtsp://..." # use ip cam
"""
import subprocess
import sys
import os
import argparse
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def run_simulation(mode: str, gui: bool = False, live_cam: str = None):
    """Run SUMO simulation with the chosen controller mode."""
    print(f"\n{'='*60}")
    gui_label = ' (GUI)' if gui else ''
    print(f"  🚗  Running SUMO Simulation{gui_label}  |  Mode: {mode.upper()}")
    print(f"{'='*60}\n")

    env = os.environ.copy()
    env["SIM_MODE"] = mode
    if gui:
        env["SIM_GUI"] = "1"
    if live_cam is not None:
        env["LIVE_CAM_URL"] = str(live_cam)

    sim_script = os.path.join(PROJECT_ROOT, "simulation_module", "sim_engine.py")
    result = subprocess.run(
        [sys.executable, sim_script],
        cwd=PROJECT_ROOT,
        env=env,
    )
    if result.returncode != 0:
        print("❌ Simulation failed!")
        sys.exit(1)

    results_file = os.path.join(PROJECT_ROOT, "results.json")
    if os.path.exists(results_file):
        print(f"\n✅ Simulation complete! Results saved to results.json")
    else:
        print("⚠️  Warning: results.json not found after simulation")


def run_dashboard():
    """Launch the Streamlit dashboard."""
    print(f"\n{'='*60}")
    print(f"  📊  Launching Streamlit Dashboard")
    print(f"{'='*60}\n")

    dashboard_script = os.path.join(PROJECT_ROOT, "dashboard", "app.py")
    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            dashboard_script,
            "--server.port", "8501",
            "--server.headless", "false",
        ],
        cwd=PROJECT_ROOT,
    )
    print("🌐 Dashboard running at: http://localhost:8501")
    print("   Press Ctrl+C to stop.\n")


def main():
    parser = argparse.ArgumentParser(
        description="TrafficFlow AI – GreenWave: One-Click Launcher",
    )
    parser.add_argument(
        "--mode",
        choices=["adaptive", "static", "vision_linked"],
        default="adaptive",
        help="Simulation controller mode (default: adaptive)",
    )
    parser.add_argument(
        "--skip-sim",
        action="store_true",
        help="Skip simulation and only launch dashboard",
    )
    parser.add_argument(
        "--sim-only",
        action="store_true",
        help="Run simulation only, no dashboard",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open SUMO GUI to visualize the simulation in real-time",
    )
    parser.add_argument(
        "--live-cam",
        type=str,
        help="Provide a URL to a live IP camera, or '0' for local webcam. Overrides default video.",
    )
    args = parser.parse_args()

    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     🚦  TrafficFlow AI – GreenWave                  ║
    ║     Smart Adaptive Traffic Signal Control            ║
    ╚══════════════════════════════════════════════════════╝
    """)

    if not args.skip_sim:
        run_simulation(args.mode, gui=args.gui, live_cam=args.live_cam)

    if not args.sim_only:
        run_dashboard()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down GreenWave. Goodbye!")


if __name__ == "__main__":
    main()
