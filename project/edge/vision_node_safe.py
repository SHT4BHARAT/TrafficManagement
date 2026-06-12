import time
import random
import logging
from typing import Dict
import numpy as np

logger = logging.getLogger("VisionNodeSafe")

def simulate_edge_vision(sim_state):
    """
    Sim fallback - safe for RL demo without cv2/ultralytics.
    Returns metadata for brain.agent.
    """
    total_vehicles = sum(sim_state.values())
    
    metadata = {
        "intersection_id": "INT_001",
        "timestamp": time.time(),
        "source": "sim_safe",
        "counts": sim_state.copy(),
        "total": total_vehicles,
        "ambulance": 1 if random.random() < 0.03 else 0
    }
    logger.info(f"[VISION] Safe metadata: {metadata['counts']}")
    return metadata

# Optional real vision (comment if deps fail)
"""
try:
    import cv2
    from ultralytics import YOLO
    from .live_camera_feed import TrafficCameraScraper
    # Full YOLO code here
    HAS_VISION = True
except ImportError:
    HAS_VISION = False
    print("[VISION] Optional deps missing - using sim fallback")
"""

if __name__ == "__main__":
    test_state = {"N": 5, "S": 3, "E": 8, "W": 2}
    print(simulate_edge_vision(test_state))
    print("Safe Vision Node ready (uncomment for YOLO).")
