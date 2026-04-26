# 🚦 Smart Traffic Control Management System

> **AI-powered adaptive traffic signal control system** combining real-time computer vision (YOLOv8) with microscopic traffic simulation (SUMO) to reduce congestion, optimize signal timings, and cut CO₂ emissions.

🚀 **Enhanced Version:** Now supports multi-junction control, emergency vehicle prioritization, and real-time dynamic analytics.

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
* Independent signal control at each junction

---

## 🚗 Multi-Lane Traffic Modeling

* Each direction supports multiple lanes
* Example:

```
NORTH: [13, 20, 18] → Total: 51
```

* Improves congestion accuracy and realism

---

## 🚑 Emergency Vehicle (Ambulance System)

* Real ambulance integrated into SUMO simulation
* Features:

  * Visual injection into traffic
  * Route traversal
  * Signal priority override
  * Automatic recovery

Flow:

```
🚑 Ambulance detected → 🚦 Signals turn GREEN → 🚗 Path cleared
```

* Dashboard shows:

  * Live ambulance alerts
  * Emergency logs

---

## 📊 Real-Time Dynamic Dashboard

* Auto-refresh enabled (near real-time)
* Continuously updates:

  * Traffic efficiency
  * Vehicle count
  * Congestion levels
  * Emergency events

---

## 📈 Advanced Traffic Analytics

* Traffic Efficiency Score
* Active vs Idle Vehicles
* CO₂ Emission Savings
* Delay Tracking
* Congestion Distribution

---

## 🌍 Real-World Map Integration

* Uses OSM → SUMO conversion
* Supports:

  * Multiple intersections
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

## 🔄 Real-Time Data Flow

```
SUMO Simulation → results.json → Streamlit Dashboard → Live Updates
```

---

## 🏗️ System Architecture

```
Vision Module → Vehicle Count → Simulation Engine → Dashboard
```

---

## ⚙️ Installation

```bash
git clone https://github.com/Ujjwal226/Smart-Traffic-Management-System.git
cd TrafficFlow-AI-GreenWave

git lfs install
git lfs pull

pip install -r requirements.txt
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

---

## 🧪 Demo Workflow

1. Start simulation
2. Open dashboard
3. Observe:

   * Multi-junction signals
   * Multi-lane traffic
   * Ambulance priority
   * Real-time analytics

---

## 📊 Performance Results

* 2000+ vehicles simulated
* 25–30% delay reduction
* ~28% CO₂ reduction

---

## 🧩 Modules Deep Dive

### 🎥 Vision Module

* YOLOv8-based vehicle detection
* FastAPI backend

### 🚗 Simulation Module

* SUMO + TraCI
* Adaptive signal control
* Emergency vehicle handling

### 📊 Dashboard

* Streamlit + Plotly
* Real-time visualization

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
