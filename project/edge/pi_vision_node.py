import cv2
import time
import requests
import json
import logging
from ultralytics import YOLO

# Configuration
# Change this to the IPv4 address of your laptop running the FastAPI backend.
# E.g., if your laptop is 192.168.1.15, make it "http://192.168.1.15:8000"
SERVER_URL = "http://localhost:8000"  # Default for testing on the identical machine
API_ENDPOINT = f"{SERVER_URL}/api/controller-config"

CAMERA_ID = 0  # 0 is usually the default USB webcam or Pi Camera
CONFIDENCE_THRESHOLD = 0.5
MODEL_NAME = "yolov8n.pt"  # Nano model is essential for Raspberry Pi CPU

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("PiVision")

def main():
    logger.info(f"Loading {MODEL_NAME} for CPU inference...")
    model = YOLO(MODEL_NAME)
    
    logger.info(f"Initializing Camera {CAMERA_ID}...")
    cap = cv2.VideoCapture(CAMERA_ID)
    
    # Lower resolution for better Pi performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        logger.error(f"Failed to open camera {CAMERA_ID}. Ensure it is connected.")
        return

    # Define simple static quadrants for Northern, Southern, Eastern, Western lanes
    # This assumes a top-down traffic camera feed.
    lanes_roi = [
        {'name': 'N', 'bbox': (0.2, 0.0, 0.4, 0.4)}, # Top-middle
        {'name': 'S', 'bbox': (0.6, 0.6, 0.4, 0.4)}, # Bottom-right
        {'name': 'E', 'bbox': (0.8, 0.2, 0.2, 0.6)}, # Right-middle
        {'name': 'W', 'bbox': (0.0, 0.4, 0.2, 0.6)}, # Left-middle
    ]

    logger.info("Vision Node Active. Press 'q' to quit.")
    
    last_transmit_time = 0
    transmit_interval = 2.0  # Send data to server every 2 seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Failed to grab frame.")
            time.sleep(1)
            continue
            
        frame_h, frame_w = frame.shape[:2]
        
        # YOLO inference (automatically uses CPU on Pi)
        results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        counts = {lane['name']: 0 for lane in lanes_roi}
        total_vehicles = 0
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Class 2=car, 5=bus, 7=truck in COCO dataset
                    if int(box.cls) in [2, 5, 7]:
                        total_vehicles += 1
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        
                        # Assign vehicle to specific lane
                        for lane in lanes_roi:
                            lx1, ly1, lx2, ly2 = [b * frame_w if i % 2 == 0 else b * frame_h for i, b in enumerate(lane['bbox'])]
                            if lx1 < cx < lx2 and ly1 < cy < ly2:
                                counts[lane['name']] += 1
                                break
        
        # Display overlay for visual debugging on the Pi
        cv2.putText(frame, f"Vehicles: {total_vehicles}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Pi Vision Node", frame)

        # Transmit to Server
        current_time = time.time()
        if current_time - last_transmit_time >= transmit_interval:
            payload = {
                "mode": "manual",  # Force backend to accept our numbers
                "vps": counts
            }
            try:
                # Increased timeout to 5s because running YOLO locally maxes out laptop CPU,
                # which can cause the local FastAPI server to respond slowly.
                response = requests.post(API_ENDPOINT, json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Transmitted VPS Check: N:{counts['N']} S:{counts['S']} E:{counts['E']} W:{counts['W']}")
                else:
                    logger.warning(f"Server rejected payload. HTTP {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning("Connection to backend timed out. CPU might be overloaded.")
            except Exception as e:
                logger.error(f"Cannot reach server at {SERVER_URL}. Is backend running on laptop?")
            
            last_transmit_time = current_time

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
