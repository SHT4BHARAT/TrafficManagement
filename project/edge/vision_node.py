import time
import random

def simulate_edge_vision(sim_state):
    """
    Simulates a YOLOv8 detection on an NVIDIA Jetson node.
    Converts raw simulation state into refined metadata.
    """
    # Extract vehicle counts from sim_state (N, S, E, W)
    total_vehicles = sum(sim_state.values())
    
    metadata = {
        "intersection_id": "INT_001",
        "timestamp": time.time(),
        "counts": sim_state.copy(),
        "total": total_vehicles,
        "ambulance": 0 if random.random() > 0.05 else 1
    }
    return metadata

if __name__ == "__main__":
    print("Starting Edge Vision Simulation node...")
    simulate_edge_vision()
