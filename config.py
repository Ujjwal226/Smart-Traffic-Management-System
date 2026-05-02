"""
Central configuration for TrafficFlow AI GreenWave.
All modules import paths and settings from here.
"""
import os
import sys

# ── SUMO Configuration ──────────────────────────────────
# Locate pip-installed eclipse-sumo package using importlib (cross-platform)
def _find_sumo_home():
    # Method 1: try importlib to find the installed 'sumo' package
    try:
        import importlib.util
        spec = importlib.util.find_spec("sumo")
        if spec and spec.origin:
            pkg_dir = os.path.dirname(spec.origin)
            if os.path.isdir(os.path.join(pkg_dir, "bin")):
                return pkg_dir
    except Exception:
        pass

    # Method 2: Linux-style path (used on Mac/Linux with venv)
    pip_sumo = os.path.join(
        sys.prefix, "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages", "sumo"
    )
    if os.path.exists(pip_sumo):
        return pip_sumo

    # Method 3: Windows user site-packages (pip install --user)
    import site
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = os.path.join(sp, "sumo")
        if os.path.isdir(candidate) and os.path.isdir(os.path.join(candidate, "bin")):
            return candidate

    return None

_sumo_home = _find_sumo_home()
if _sumo_home:
    SUMO_HOME = _sumo_home
elif "SUMO_HOME" in os.environ:
    SUMO_HOME = os.environ["SUMO_HOME"]
else:
    sys.exit("ERROR: SUMO not found. Run: pip install eclipse-sumo")

os.environ["SUMO_HOME"] = SUMO_HOME

# On Windows the binaries have .exe extension
_exe = ".exe" if sys.platform == "win32" else ""
SUMO_BIN = os.path.join(SUMO_HOME, "bin", f"sumo{_exe}")
SUMO_GUI_BIN = os.path.join(SUMO_HOME, "bin", f"sumo-gui{_exe}")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")

# Add SUMO tools to Python path (for traci, sumolib)
if SUMO_TOOLS not in sys.path:
    sys.path.insert(0, SUMO_TOOLS)

# ── Project Paths ────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SIMULATION_DIR = os.path.join(PROJECT_ROOT, "simulation_module")
VISION_DIR = os.path.join(PROJECT_ROOT, "vision_module")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "dashboard")
RESULTS_FILE = os.path.join(PROJECT_ROOT, "results.json")

# ── Simulation Config ────────────────────────────────────
SIM_CONFIG = os.path.join(SIMULATION_DIR, "osm.sumocfg")
SIM_DURATION = 2000  # seconds

# ── Vision Config ────────────────────────────────────────
live_cam = os.environ.get("LIVE_CAM_URL")
if live_cam:
    # If the user passes '0', parse it as an integer for the local webcam.
    VIDEO_PATH = int(live_cam) if live_cam.isdigit() else live_cam
else:
    VIDEO_PATH = os.path.join(DATA_DIR, "traffic.mp4")

YOLO_MODEL = os.path.join(VISION_DIR, "yolov8n.pt")
DETECTION_CLASSES = [2, 5, 7]  # car, bus, truck
VISION_API_PORT = 8000

# ── Dashboard Config ─────────────────────────────────────
DASHBOARD_PORT = 8501

# ── Emission Factor (kg CO2 per idle-second per vehicle) ─
# Average passenger car: ~2.3 kg CO2/liter, ~0.8 L/hr idle = ~0.00051 kg/s
EMISSION_FACTOR = 0.00051
