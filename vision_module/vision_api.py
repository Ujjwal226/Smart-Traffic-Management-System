"""
TrafficFlow Vision API — Real-time vehicle detection using YOLOv8.
Provides REST endpoints for per-lane vehicle counts and congestion status.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from datetime import datetime
import cv2
import config

app = FastAPI(title="TrafficFlow Vision API", version="2.0")

# Allow dashboard to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO(config.YOLO_MODEL)
cap = cv2.VideoCapture(config.VIDEO_PATH)

# Get frame dimensions for lane splitting
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
mid_x = frame_width // 2
mid_y = frame_height // 2


def classify_to_lane(cx, cy):
    """Map a detection's center point to a lane/quadrant."""
    if cy < mid_y:
        return "north" if cx < mid_x else "east"
    else:
        return "west" if cx < mid_x else "south"


def get_congestion_status(count):
    if count > 15:
        return "High Congestion"
    elif count > 7:
        return "Moderate"
    return "Clear"


def process_frame():
    """Read one frame, run YOLO, return per-lane counts."""
    global cap
    success, frame = cap.read()

    if not success:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, frame = cap.read()
        if not success:
            return None, {"north": 0, "south": 0, "east": 0, "west": 0}, 0

    results = model(frame, classes=config.DETECTION_CLASSES, verbose=False)
    boxes = results[0].boxes

    lane_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
    total = 0

    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        lane = classify_to_lane(cx, cy)
        lane_counts[lane] += 1
        total += 1

    return frame, lane_counts, total


@app.get("/")
def home():
    return {"message": "TrafficFlow Vision API v2.0 running. Go to /docs to test."}


@app.get("/get_traffic_count")
def get_traffic_count():
    """Returns per-lane vehicle count and congestion status."""
    _, lane_counts, total = process_frame()

    return {
        "intersection": "Main_Street_Cam",
        "timestamp": datetime.now().isoformat(),
        "total_vehicles": total,
        "lanes": lane_counts,
        "status": get_congestion_status(total),
        "vehicle_count": total,  # backward compat
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": "yolov8n", "video": config.VIDEO_PATH}