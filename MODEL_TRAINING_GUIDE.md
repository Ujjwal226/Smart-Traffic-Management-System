# TrafficFlow AI: Model Fine-Tuning Guide

While **TrafficFlow AI – GreenWave** uses the pre-trained `yolov8n.pt` model (which is already excellent at detecting cars, buses, motorcycles, and trucks), real-world deployments often require **Domain Adaptation**. 

Fine-tuning your own model is highly recommended for:
- Unique camera angles (e.g., top-down fisheye lenses).
- Adverse weather or night-time traffic detection.
- Localized vehicle classes (e.g., auto-rickshaws, emergency vehicles).

---

## 🚀 1. Preparing Your Dataset

The most important step in fine-tuning is gathering high-quality data from your actual deployment environment.

1. **Extract Frames:** Extract video frames from your target traffic cameras at different times of day.
2. **Annotate Data:** Use a tool like **[Roboflow](https://roboflow.com/)** or **[CVAT](https://www.cvat.ai/)** to draw bounding boxes around the vehicles you want to track.
3. **Export to YOLOv8 Format:** Export your dataset. It should have an `images/` directory and a `labels/` directory (containing `.txt` files with bounding box coordinates).
4. **Place in Project:** Copy the dataset into the project folder, for example `vision_module/traffic_dataset/`.

---

## ⚙️ 2. Configure `dataset.yaml`

We have provided a template configuration file at `vision_module/dataset.yaml`. Open this file and adjust the paths to point to your new dataset:

```yaml
path: ./traffic_dataset
train: images/train
val: images/val

names:
  0: car
  1: motorcycle
  2: bus
  3: truck
  # Add or merge your custom classes here!
```

---

## 🏋️ 3. Train the Model

We have included a ready-to-use training script that utilizes the `ultralytics` library. Because you are on a Mac, the script is configured to use **MPS (Apple Silicon / Metal Performance Shaders)** for blazing-fast hardware acceleration.

Run the following command from the root directory:

```bash
python3 vision_module/train.py
```

### What to expect during training:
- **Epochs:** By default, it runs for 50 epochs.
- **Early Stopping:** If the model stops improving for 10 epochs, it will halt automatically to prevent overfitting (`patience=10`).
- **Output:** The training logs, loss curves, and validation metrics will be saved in `vision_module/greenwave_models/custom_traffic_run/`.

---

## ✅ 4. Deploy Custom Weights

Once training completes, YOLO automatically selects the best epoch. 
You will see an output message pointing to:
`vision_module/greenwave_models/custom_traffic_run/weights/best.pt`

To use your new model in the GreenWave pipeline:
1. Copy `best.pt` into the `vision_module/` directory.
2. Open `config.py` in the root directory.
3. Update the `YOLO_WEIGHTS` variable:

```python
# Change this:
YOLO_WEIGHTS = os.path.join(VISION_DIR, "yolov8n.pt")

# To this:
YOLO_WEIGHTS = os.path.join(VISION_DIR, "best.pt")
```

Restart the Vision API module or use `run_all.py`. Your adaptive traffic system will now use your hyper-optimized, fine-tuned AI model!
