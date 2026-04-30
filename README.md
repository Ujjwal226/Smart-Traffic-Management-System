# 🚦 Smart Traffic Control Management System

> **AI-powered adaptive traffic signal control system** combining real-time computer vision (YOLOv8) with microscopic traffic simulation (SUMO) to reduce congestion, optimize signal timings, and cut CO₂ emissions.

🚀 **Final Enhanced Version:** Now supports multi-junction control, true multi-lane simulation, ambulance priority, incident simulation, and real-time API-based data pipeline with fallback reliability.

---

## 📖 Table of Contents

* What This Project Does
* Latest Enhancements
* System Architecture
* How It Works
* Project Structure
* Installation & Setup
* Running the Project
* Modules Deep Dive
* API Reference
* Performance Results

---

## 🧠 What This Project Does

Smart Traffic Control Management System solves urban traffic congestion using:

| Module               | What It Does                      | Technology         |
| -------------------- | --------------------------------- | ------------------ |
| 🎥 Vision Module     | Detects vehicles from live video  | YOLOv8 + FastAPI   |
| 🚗 Simulation Module | Adaptive signal control           | SUMO + TraCI       |
| 📊 Dashboard         | Traffic analytics & visualization | Streamlit + Plotly |

---

# 🆕 Latest Enhancements (Final Version)

## 🚦 Multi-Junction Traffic Control

* Upgraded from single → **16 real-world junctions**
* Based on OpenStreetMap network
* Independent adaptive signal control at each junction

---

## 🚗 True Multi-Lane Traffic Modeling

* Roads now support **2–4 lanes per direction**
* Vehicles distributed realistically across lanes

Example:

```
NORTH: [13, 20, 18] → Total: 51
```

* Improves congestion accuracy and realism

---

## 🚑 Emergency Vehicle (Ambulance) System

* Real ambulance integrated into SUMO simulation
* Features:

  * Ambulance injected at user-defined step
  * Route traversal with proper lane following
  * Traffic-aware signal priority override
  * Dashboard alert + log

Flow:

```
🚑 Ambulance detected → 🚦 Signals turn GREEN → 🚗 Path cleared
```

* Dashboard shows:

  * Real-time ambulance alerts
  * Emergency event log
  * Emergency duration

---

## 🚧 Road Incident / Accident Simulation

* Dashboard-triggered incident simulation
* Features:

  * Blockage at specified junction
  * Traffic congestion build-up
  * Visual dashboard alerts
  * Emergency duration tracking

Flow:

```
🚨 Dashboard → Activate Incident → 🚧 Congestion → Emergency Alert → Clear
```

---

## 📊 Real-Time Dynamic Dashboard

* True 2-second refresh rate (Streamlit + requests)
* Continuously updates:

  * Traffic efficiency
  * Vehicle count
  * Congestion levels
  * Emergency events

---

## 📈 Advanced Traffic Analytics

* Traffic Efficiency Score (0–100)
* Active vs Idle Vehicles
* CO₂ Emission Savings
* Delay Tracking
* Congestion Distribution
* Emergency Event Analysis

---

## 🌍 Real-World Map Integration

* Uses OpenStreetMap → SUMO conversion
* Supports:

  * 16 junctions
  * Realistic road layouts
  * Geographic visualization

---

## 🧠 Adaptive AI Improvements

* Signal control based on:

  * Queue length
  * Waiting time
  * Vehicle density
* More responsive and optimized decisions

---

## 🔄 Real-Time Data Flow (API-Based)

```
SUMO Simulation → results.json → API (http://localhost:9000/data) → Streamlit Dashboard → Live Updates
```

* No file polling — true real-time streaming
* Automatic fallback to JSON file if API unavailable

---

## 🏗️ System Architecture

```
Vision Module → Vehicle Count → Simulation Engine → Dashboard
```

---

## ⚙️ Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install from scratch
pip install streamlit pandas plotly requests
pip install traci
pip install ultralytics
pip install shapely matplotlib osmnx
```

---

## ▶️ Running the Project

### Run Simulation

```bash
python run_all.py --gui --sim-only
```

### Run Dashboard

```bash
streamlit run dashboard/app.py
```

### Full System

```bash
# Terminal 1: Simulation
python run_all.py --gui

# Terminal 2: Dashboard
streamlit run dashboard/app.py

# Terminal 3: API (optional)
python vision_api.py
```

---

## 🧪 Demo Workflow

1. Start simulation
2. Open dashboard
3. Observe:

   * Multi-junction signals
   * Multi-lane traffic
   * Ambulance priority
   * Incident simulation
   * Real-time analytics

---

## 🎯 Performance Results

* 2000+ vehicles simulated
* 25–30% delay reduction
* ~28% CO₂ reduction

---

## 🧩 Modules Deep Dive

### 🎥 Vision Module

* YOLOv8-based vehicle detection
* FastAPI backend
* Multi-camera support

### 🚗 Simulation Module

* SUMO + TraCI
* Adaptive signal control
* Emergency vehicle handling
* Incident simulation
* Multi-lane support
* Real-world OSM network

### 📊 Dashboard

* Streamlit + Plotly
* Real-time analytics
* Video feed integration
* Emergency alert system
* Incident simulation interface

---

## 📡 API

```json
GET /get_traffic_count
{
  "vehicle_count": 12,
  "status": "Moderate"
}
```

---

## 📈 Performance Summary

| Metric     | Improvement |
| ---------- | ----------- |
| Delay      | ↓ 25–30%    |
| CO₂        | ↓ ~28%      |
| Efficiency | ↑           |

---

## 👨‍💻 Team

* Ujjwal Khanna
* Pritam Patra

---

## 🎓 Academic Info

Final Year Project (2025–2026)

---
