"""
Real-time traffic video viewer with YOLOv8 detection and lane overlay.
Press 'q' to quit.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ultralytics import YOLO
import cv2
import config

model = YOLO(config.YOLO_MODEL)
cap = cv2.VideoCapture(config.VIDEO_PATH)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
mid_x = frame_width // 2
mid_y = frame_height // 2

LANE_COLORS = {
    "north": (0, 255, 0),
    "south": (0, 0, 255),
    "east": (255, 165, 0),
    "west": (255, 255, 0),
}


def classify_to_lane(cx, cy):
    if cy < mid_y:
        return "north" if cx < mid_x else "east"
    else:
        return "west" if cx < mid_x else "south"


while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model(frame, classes=config.DETECTION_CLASSES, verbose=False)
    annotated = results[0].plot()

    # Draw lane dividers
    cv2.line(annotated, (mid_x, 0), (mid_x, frame_height), (255, 255, 255), 2)
    cv2.line(annotated, (0, mid_y), (frame_width, mid_y), (255, 255, 255), 2)

    # Count per lane
    lane_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        lane = classify_to_lane((x1 + x2) / 2, (y1 + y2) / 2)
        lane_counts[lane] += 1

    # Lane labels
    labels = [
        ("NORTH: " + str(lane_counts["north"]), (mid_x // 2 - 40, 30)),
        ("EAST: " + str(lane_counts["east"]), (mid_x + mid_x // 2 - 30, 30)),
        ("WEST: " + str(lane_counts["west"]), (mid_x // 2 - 40, mid_y + 30)),
        ("SOUTH: " + str(lane_counts["south"]), (mid_x + mid_x // 2 - 30, mid_y + 30)),
    ]
    for text, pos in labels:
        lane_name = text.split(":")[0].strip().lower()
        color = LANE_COLORS.get(lane_name, (255, 255, 255))
        cv2.putText(annotated, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    total = sum(lane_counts.values())
    status = "HIGH" if total > 15 else "MODERATE" if total > 7 else "CLEAR"
    cv2.putText(annotated, f"TOTAL: {total} | {status}", (10, frame_height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.imshow("TrafficFlow AI - Live Detection", annotated)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()