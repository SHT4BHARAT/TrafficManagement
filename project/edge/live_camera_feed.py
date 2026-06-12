import requests
import cv2
import time
import os
import logging
import numpy as np
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LiveCamera")

class TrafficCameraScraper:
    """
    Live camera frame capture using OpenCV.
    Supports HTTP JPEG/MJPEG and RTSP streams from public traffic cams.
    Production-ready for YOLO pipeline.
    """
    def __init__(self, output_dir="edge/snapshots"):
        self.output_dir = Path(output_dir).absolute()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cameras = self._get_camera_urls()
        
    def _get_camera_urls(self):
        """Public traffic camera streams (NYC, London, India demo)."""
        return {
            "NYC_TIMES_SQ": "http://207.251.86.250/mjpg/video.mjpg",  # NYC DOT public MJPEG
            "NYC_5TH_AVE": "https://trafficmp4.sinart.ro/images.php?camera=123",  # Alt
            "LONDON_BRIDGE": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov",  # Demo RTSP
            "DELHI_EXAMPLE": "https://static.intertraffic.in/cam/delhi_metro.jpg",  # Static fallback
        }
    
    def capture_live_frame(self, cam_id="NYC_TIMES_SQ", timeout=10):
        """
        Capture latest frame using OpenCV VideoCapture (handles MJPEG/RTSP/JPG).
        Returns frame as np.array or None.
        """
        url = self.cameras.get(cam_id, list(self.cameras.values())[0])
        logger.info(f"[CAMERA/{cam_id}] Capturing from {url}")
        
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            frame_path = self.output_dir / f"{cam_id}_{timestamp}.jpg"
            cv2.imwrite(str(frame_path), frame)
            logger.info(f"[CAMERA/{cam_id}] Frame saved: {frame_path}")
            return frame
        else:
            logger.error(f"[CAMERA/{cam_id}] Capture failed")
            return None
    
    def stream_loop(self, cam_id="NYC_TIMES_SQ", fps=1):
        """Continuous capture loop."""
        while True:
            frame = self.capture_live_frame(cam_id)
            if frame is not None:
                yield frame
            time.sleep(1/fps)

if __name__ == "__main__":
    scraper = TrafficCameraScraper()
    
    # Test single capture
    frame = scraper.capture_live_frame("NYC_TIMES_SQ")
    if frame is not None:
        print(f"[TEST] Captured frame shape: {frame.shape}")
    
    # List cams
    print("\nAvailable cameras:", list(scraper.cameras.keys()))
