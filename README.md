# 🚦 Smart Traffic Control Management System

> **AI-powered adaptive traffic signal control system** combining real-time computer vision (YOLOv8) with microscopic traffic simulation (SUMO) to reduce congestion, optimize signal timings, and cut CO₂ emissions.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![SUMO](https://img.shields.io/badge/SUMO-1.20+-green.svg)](https://eclipse.dev/sumo/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple.svg)](https://docs.ultralytics.com)

---

## 📖 Table of Contents

- [What This Project Does](#what-this-project-does)
- [System Architecture](#system-architecture)
- [How It Works (Step-by-Step)](#how-it-works-step-by-step)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Project](#running-the-project)
  - [One-Click Launch](#1-one-click-launch-recommended)
  - [Visual Simulation (SUMO GUI)](#2-visual-simulation-sumo-gui)
  - [Individual Components](#3-run-individual-components)
- [Live Dashboard (Free Hosting)](#live-dashboard-free-hosting)
- [Modules Deep Dive](#modules-deep-dive)
- [API Reference](#api-reference)
- [Performance Results](#performance-results)
- [Configuration Reference](#configuration-reference)


---

## What This Project Does

 **Smart Traffic Control Management System solves urban traffic congestion** using two AI-powered modules:

| Module | What It Does | Technology |
|--------|-------------|------------|
| **🎥 Vision Module** | Detects & counts vehicles from live video in real-time | YOLOv8 + FastAPI |
| **🚗 Simulation Module** | Simulates real road networks and adapts traffic light timings | SUMO + TraCI |
| **📊 Dashboard** | Visualizes traffic data, CO₂ savings, and congestion maps | Streamlit + Plotly |

### The Problem
Traditional traffic lights use **fixed timers** — they can't adapt to actual traffic conditions. This causes:
- Unnecessary waiting at empty intersections
- Long queues building up during peak hours
- Wasted fuel and increased CO₂ from idling vehicles

### Our Solution
GreenWave uses **AI to dynamically adjust traffic signals** based on:
1. **Vehicle density** (how many cars are on each road)
2. **Queue length** (how many cars are stopped/waiting)
3. **Waiting time** (how long vehicles have been stuck)
4. **Green Wave coordination** (synchronizing adjacent traffic lights for continuous flow)

---

## System Architecture

```
╔═══════════════════════════════════════════════════════════════╗
║                   TrafficFlow AI – GreenWave                  ║
╠═══════════════════════╦═══════════════════════════════════════╣
║                       ║                                       ║
║   🎥 VISION MODULE    ║     🚗 SIMULATION MODULE              ║
║                       ║                                       ║
║  ┌──────────────────┐ ║  ┌─────────────────────────────────┐  ║
║  │  traffic.mp4     │ ║  │  Real Road Network (OSM → SUMO) │  ║
║  │  (Camera Feed)   │ ║  │           ↓                     │  ║
║  │       ↓          │ ║  │  Vehicle Routes (.rou.xml)      │  ║
║  │  YOLOv8 Nano     │ ║  │           ↓                     │  ║
║  │  (Detection AI)  │ ║  │  🧠 Adaptive Controller         │  ║
║  │       ↓          │ ║  │  (Score-based signal timing)    │  ║
║  │  Vehicle Count   │ ║  │           ↓                     │  ║
║  │       ↓          │ ║  │  🌊 Green Wave Coordinator      │  ║
║  │  FastAPI Server  │─║──│  (Phase offset optimization)    │  ║
║  │  /get_traffic_   │ ║  │           ↓                     │  ║
║  │     count        │ ║  │  📊 Performance Metrics          │  ║
║  └──────────────────┘ ║  └─────────────────────────────────┘  ║
║                       ║              ↓                        ║
╠═══════════════════════╩═══════════════════════════════════════╣
║                                                               ║
║   📊 STREAMLIT DASHBOARD (results.json → Interactive Charts)  ║
║   • KPI Cards  • CO₂ Gauge  • Congestion Analysis  • Map     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## How It Works (Step-by-Step)

### 1️⃣ Vision Pipeline (Vehicle Detection)

```
Video Frame → YOLOv8 Model → Bounding Boxes → Count Cars/Buses/Trucks → REST API
```

1. **Frame Capture** — Reads frames from `data/traffic.mp4` (or any camera feed)
2. **YOLOv8 Inference** — Detects vehicles using a pre-trained YOLO model
3. **Filtering** — Only counts cars (class 2), buses (class 5), trucks (class 7)
4. **Classification** — Maps count to congestion level:

   | Vehicle Count | Status |
   |:---:|:---:|
   | > 15 | 🔴 High Congestion |
   | 8–15 | 🟡 Moderate |
   | ≤ 7 | 🟢 Clear |

5. **API Response** — Returns JSON via FastAPI at `http://localhost:8000/get_traffic_count`

### 2️⃣ Simulation Pipeline (Adaptive Traffic Control)

```
Road Network → SUMO Simulation → Adaptive AI Controller → Optimized Signal Timings
```

1. **Network Loading** — Loads real Delhi road network from OpenStreetMap
2. **Vehicle Generation** — Creates realistic traffic demand (12 vehicles/km/lane)
3. **Simulation Loop** — Steps through 2000 seconds of traffic

4. **Smart Scoring** (every 20 steps):
   ```
   Score = (Queue × 2.0) + (Wait Time × 1.5) + (Density × 1.0)
   ```
   
   | Score | Green Phase Duration |
   |:---:|:---:|
   | > 100 | 55 seconds (very congested) |
   | 51–100 | 45 seconds |
   | 21–50 | 35 seconds |
   | 11–20 | 25 seconds |
   | ≤ 10 | 15 seconds (clear) |

5. **Green Wave** — Adjacent traffic lights are phase-offset so a vehicle hitting green at one intersection will also hit green at the next

6. **Metrics** — Tracks delay, idle time, CO₂ emissions, and saves to `results.json`

### 3️⃣ Dashboard (Visualization)

The Streamlit dashboard reads `results.json` and displays:
- **KPI Cards** — Total vehicles, CO₂ saved, average delay, simulation runtime
- **Active vs Idle chart** — Shows traffic flow over time
- **CO₂ Gauge** — Percentage reduction vs baseline
- **Congestion Analysis** — Ratio chart + pie breakdown (high/moderate/clear)
- **Interactive Map** — Traffic light locations on OpenStreetMap

---

## Project Structure

```
TrafficFlow-AI-GreenWave/
│
├── 📄 run_all.py                    # 🚀 One-click launcher (sim + dashboard)
├── 📄 config.py                     # ⚙️ Central configuration
├── 📄 requirements.txt              # 📦 Python dependencies
├── 📄 results.json                  # 📊 Simulation output (auto-generated)
│
├── 🎥 vision_module/                # Computer Vision subsystem
│   ├── vision_api.py               # FastAPI server for vehicle detection
│   ├── show_video.py               # Real-time video viewer with detections
│   └── yolov8n.pt                  # Pre-trained YOLOv8 Nano model (6.2 MB)
│
├── 🚗 simulation_module/           # Traffic Simulation subsystem
│   ├── sim_engine.py               # Main simulation engine (adaptive/static)
│   ├── green_wave.py               # Green Wave corridor coordination
│   ├── dynamic_routes.py           # Vision-linked vehicle injection
│   ├── osm.sumocfg                 # SUMO configuration file
│   ├── osm.net.xml                 # Road network (from OpenStreetMap)
│   ├── osm.rou.xml                 # Vehicle route definitions
│   └── map.osm                     # Raw OpenStreetMap data
│
├── 📊 dashboard/                    # Streamlit Dashboard
│   └── app.py                      # Interactive analytics dashboard
│
├── 📁 data/
│   └── traffic.mp4                 # Sample traffic video (~56 MB)
│
├── 📁 .streamlit/
│   └── config.toml                 # Streamlit theme & server config
│
└── 📁 2026-02-25-00-09-38/         # SUMO network build artifacts
    ├── build.bat                   # Trip generation script
    └── ...                         # Simulation outputs
```

---

## Installation & Setup

### Prerequisites

| Requirement | Version | How to Install |
|------------|---------|---------------|
| **Python** | ≥ 3.8 | [python.org](https://python.org) |
| **SUMO** | ≥ 1.20.0 | `pip install eclipse-sumo` (recommended) OR [downloads](https://sumo.dlr.de/docs/Downloads.php) |
| **Git LFS** | Latest | `brew install git-lfs` (macOS) or [git-lfs.com](https://git-lfs.com) |

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/Ujjwal226/Smart-Traffic-Management-System.git
cd TrafficFlow-AI-GreenWave

# 2. Install Git LFS (for large files: model + video)
git lfs install
git lfs pull

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Verify SUMO is installed
python -c "import config; print(f'SUMO found at: {config.SUMO_HOME}')"
```

> **Note:** If SUMO was installed via `pip install eclipse-sumo`, it's auto-detected. Otherwise set `SUMO_HOME`:
> ```bash
> export SUMO_HOME="/path/to/sumo"  # macOS/Linux
> set SUMO_HOME=C:\path\to\sumo     # Windows
> ```

---

## Running the Project

### 1. One-Click Launch (Recommended)

**For macOS Users:** You can simply double-click the `Start_Simulation.command` file in the project folder to launch everything instantly!

Or from the terminal:
```bash
# Run simulation + open dashboard in one command
python run_all.py

# Choose a specific mode:
python run_all.py --mode adaptive       # AI-optimized (default)
python run_all.py --mode static         # Fixed timers (baseline)
python run_all.py --mode vision_linked  # Camera-connected
```

### 2. Using a Live Camera Feed (Real Physical World)

Want to tap into the actual real world? You can process video from your local webcam or any live IP/RTSP traffic camera!

```bash
# Use your laptop's built-in webcam instead of the recorded video
python run_all.py --mode vision_linked --live-cam 0

# Use a live IP traffic camera (e.g. RTSP or HTTP stream)
python run_all.py --mode vision_linked --live-cam "http://192.168.1.100/video.mjpg"
```
*Note: Make sure `--mode vision_linked` is active, otherwise the simulation will run on its standard adaptive AI logic rather than listening to camera data.*

### 3. Visual Simulation (SUMO GUI)

See the traffic flow in real-time with the SUMO graphical interface (enhanced with the "real world" aesthetic and realistic vehicle rendering):

![SUMO Simulation](sumo_simulation.png)

```bash
# Launch with visual simulation window
python run_all.py --gui

# GUI + specific mode
python run_all.py --gui --mode adaptive
```

This opens a **SUMO window** where you can watch:
- 🚗 Cars moving through the road network
- 🚦 Traffic lights changing adaptively
- 📊 Real-time vehicle counts

> **Tip:** Use `--sim-only` to run just the simulation without launching the dashboard:
> ```bash
> python run_all.py --gui --sim-only
> ```

### 3. Run Individual Components

#### Vision API (Vehicle Detection Server)
```bash
cd vision_module
uvicorn vision_api:app --reload --port 8000
```
- **Swagger Docs:** http://localhost:8000/docs
- **API Endpoint:** http://localhost:8000/get_traffic_count

#### Video Viewer (Real-time Detection Display)
```bash
python vision_module/show_video.py    # Press 'q' to quit
```

#### Simulation Only
```bash
python simulation_module/sim_engine.py
```

#### Dashboard Only (reads existing results.json)
```bash
python run_all.py --skip-sim
# OR directly:
streamlit run dashboard/app.py
```

---


## Modules Deep Dive

### 🎥 Vision Module

**`vision_api.py`** — FastAPI server that processes video frames through YOLOv8:

```python
# Key detection logic
model = YOLO("yolov8n.pt")
results = model(frame)

# Filter for vehicles only
vehicle_classes = [2, 5, 7]  # car, bus, truck
count = sum(1 for box in results.boxes if int(box.cls) in vehicle_classes)
```

**`show_video.py`** — Opens a window showing live detection with bounding boxes drawn on vehicles.

### 🚗 Simulation Module

**`sim_engine.py`** — Core engine with the `TrafficController` class:

```python
class TrafficController:
    def compute_score(self):
        """Multi-factor congestion score"""
        score = (queue × 2.0) + (wait_time × 1.5) + (density × 1.0)
        return score

    def optimize_signal(self):
        """Adjust green phase based on score"""
        if score > 100: duration = 55   # Very congested
        elif score > 50: duration = 45
        elif score > 20: duration = 35
        elif score > 10: duration = 25
        else: duration = 15              # Clear
```

**`green_wave.py`** — Coordinates adjacent traffic lights:
- Detects corridors of sequential intersections
- Calculates optimal phase offsets based on distance and speed
- Creates a "wave of green lights" for smooth traffic flow

**`dynamic_routes.py`** — Links vision data to simulation:
- Fetches real-time counts from the Vision API
- Injects vehicles into the simulation based on actual camera data

### 📊 Dashboard

**`dashboard/app.py`** — Streamlit app with:
- Dark theme with neon accent colors
- Interactive Plotly charts
- Folium map with traffic light locations
- Auto-refresh capability (5-second intervals)

---

## API Reference

### `GET /` — Health Check

```json
{
  "message": "Vision API is running. Go to /docs to test it."
}
```

### `GET /get_traffic_count` — Vehicle Detection

```json
{
  "intersection": "Main_Street_Cam",
  "timestamp": "Live",
  "vehicle_count": 12,
  "status": "Moderate"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `intersection` | string | Camera/intersection identifier |
| `timestamp` | string | Always `"Live"` for real-time feeds |
| `vehicle_count` | integer | Number of detected vehicles |
| `status` | string | `"Clear"`, `"Moderate"`, or `"High Congestion"` |

---

## Performance Results

### Adaptive vs Static Comparison

```
╔══════════════════════════════════════════════╗
║           PERFORMANCE SUMMARY                ║
╠══════════════════════════════════════════════╣
║  Mode:                    ADAPTIVE           ║
║  Total Vehicles:          1,000+             ║
║  CO₂ Saved:               ~28%              ║
║  Avg Delay Reduction:     ~25-30%           ║
║  Green Wave Corridors:    Auto-detected      ║
╚══════════════════════════════════════════════╝
```

The adaptive controller consistently outperforms fixed timers by:
- **Reducing average delay** by 25-30%
- **Cutting idle time** significantly through dynamic adjustments
- **Saving CO₂ emissions** proportional to reduced idling

---

## Configuration Reference

### Simulation Parameters

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `MODE` | `sim_engine.py` / `SIM_MODE` env | `"adaptive"` | `adaptive`, `static`, or `vision_linked` |
| `USE_GUI` | `SIM_GUI` env var | `"0"` | Set to `"1"` for SUMO visual window |
| Sim duration | `config.py` `SIM_DURATION` | 2000s | Simulation length in seconds |
| Scoring weights | `sim_engine.py` | queue×2, wait×1.5, density×1 | Multi-factor scoring |
| Optimization interval | `sim_engine.py` | Every 20 steps | How often signals re-optimize |

### Vision Parameters

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| Detection classes | `config.py` | `[2, 5, 7]` | COCO IDs: car, bus, truck |
| High threshold | `vision_api.py` | > 15 vehicles | "High Congestion" level |
| Moderate threshold | `vision_api.py` | > 7 vehicles | "Moderate" level |
| API port | `config.py` | 8000 | Vision API server port |

### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SIM_MODE` | `adaptive` / `static` / `vision_linked` | Controller mode |
| `SIM_GUI` | `0` / `1` | Enable SUMO graphical window |
| `SUMO_HOME` | Path to SUMO | Auto-detected if pip-installed |

---

## Team

Built  by **Ujjwal Khanna & Pritam Patra**

---



This project is provided for **educational and research purposes**.
