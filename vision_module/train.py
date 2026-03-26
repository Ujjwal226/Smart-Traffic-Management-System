import os
from ultralytics import YOLO

def main():
    print("🚦 GREENWAVE AI: MODEL FINE-TUNING 🚦")
    print("Starting YOLOv8 training on local traffic datastet...\n")
    
    # 1. Load a pre-trained model (starting from nano for speed)
    print("Loading base model: yolov8n.pt")
    model = YOLO("yolov8n.pt")

    # 2. Get dataset configuration path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_config = os.path.join(current_dir, "dataset.yaml")

    # 3. Train the model
    # Note: Adjust epochs, imgsz, and batch size based on your hardware.
    # For a Mac (MPS), 'mps' backend can be specified.
    print(f"\nTraining via dataset configuration: {dataset_config}")
    
    results = model.train(
        data=dataset_config,
        epochs=50,                  # Start with 50 epochs
        imgsz=640,                  # Image size
        batch=16,                   # Batch size (reduce if out of memory)
        project="greenwave_models", # Where to save results
        name="custom_traffic_run",  # Experiment name
        device="mps",               # Uses Apple Silicon (M1/M2/M3) GPU if available, else omit or use 'cpu'
        patience=10,                # Early stopping
    )

    print("\n✅ Training complete!")
    print(f"Best model weights saved locally at: {results.save_dir}/weights/best.pt")
    print("Replace 'yolov8n.pt' in config.py with your new 'best.pt' to use it.")

if __name__ == "__main__":
    main()
