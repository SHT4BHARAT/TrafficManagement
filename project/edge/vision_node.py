import cv2
import numpy as np
import time
from ultralytics import YOLO
from pathlib import Path
import logging
from edge.live_camera_feed import TrafficCameraScraper
from simulation.traffic_sim import IntersectionSimulator  # fallback

logger = logging.getLogger("VisionNode")

class EdgeVisionNode:
    """
    Production edge vision: YOLOv8 on live camera frames -> lane vehicle counts.
    Fallback to simulator for training/demo.
    """
    def __init__(self, model_path="yolov8n.pt", conf=0.5):
        self.model = YOLO(model_path)  # Download auto
        self.conf = conf
        self.scraper = TrafficCameraScraper()
        self.lanes_roi = [  # Approximate ROIs for 4-way int (adjust per cam)
            {'name': 'N', 'bbox': (0.2, 0.0, 0.4, 0.4)},
            {'name': 'S', 'bbox': (0.6, 0.6, 0.4, 0.4)},
            {'name': 'E', 'bbox': (0.8, 0.2, 0.2, 0.6)},
            {'name': 'W', 'bbox': (0.0, 0.4, 0.2, 0.6)},
        ]
        
    def process_frame(self, frame):
        """YOLO detect -> count per lane ROI."""
        if frame is None:
            return None
        
        # YOLO inference
        results = self.model(frame, conf=self.conf, verbose=False)
        
        counts = {lane['name']: 0 for lane in self.lanes_roi}
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Class 2=car, 5=bus, 7=truck (vehicles)
                    if int(box.cls) in [2,5,7]:
                        x1,y1,x2,y2 = box.xyxy[0].cpu().numpy()
                        cx, cy = (x1+x2)/2, (y1+y2)/2
                        frame_h, frame_w = frame.shape[:2]
                        
                        # Assign to lane ROI
                        for lane in self.lanes_roi:
                            lx1,ly1,lx2,ly2 = [b*frame_w if i%2==0 else b*frame_h for i,b in enumerate(lane['bbox'])]
                            if lx1 < cx < lx2 and ly1 < cy < ly2:
                                counts[lane['name']] += 1
                                break
        
        return counts
    
    def detect_from_camera(self, cam_id="NYC_TIMES_SQ"):
        """Live detection pipeline."""
        logger.info(f"[VISION] Live detection on {cam_id}")
        frame = self.scraper.capture_live_frame(cam_id)
        if frame is not None:
            counts = self.process_frame(frame)
            metadata = {
                "timestamp": time.time(),
                "source": "live_camera",
                "camera": cam_id,
                "counts": counts,
                "total": sum(counts.values())
            }
            return metadata
        return None
    
    def simulate_edge_vision(self, sim_state):  # Backward compat
        """Simulator fallback."""
        total = sum(sim_state.values())
        return {
            "intersection_id": "INT_001",
            "timestamp": time.time(),
            "source": "sim",
            "counts": sim_state.copy(),
            "total": total,
            "ambulance": np.random.choice([0,1], p=[0.95, 0.05])
        }

if __name__ == "__main__":
    node = EdgeVisionNode()
    
    # Test live
    live_meta = node.detect_from_camera()
    print("Live:", live_meta)
    
    # Test sim
    sim_state = {"N":3, "S":2, "E":5, "W":1}
    print("Sim:", node.simulate_edge_vision(sim_state))
    
    print("Edge Vision Node ready for production!")
