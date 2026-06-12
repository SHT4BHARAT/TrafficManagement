import yaml
import os
import sys
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env.sumo_env import SumoTrafficEnv

def collect_data():
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    env = SumoTrafficEnv(config)
    dataset = []
    
    print("Starting data collection (50k timesteps, 9 features)...")
    
    total_samples = 0
    while total_samples < 50000:
        state, _ = env.reset()
        done = False
        while not done and total_samples < 50000:
            action = env.action_space.sample()
            next_state, reward, terminated, truncated, _ = env.step(action)
            dataset.append(next_state)
            total_samples += 1
            done = terminated or truncated
            if total_samples % 5000 == 0:
                print(f"Collected {total_samples} samples...")
        
        if total_samples >= 50000:
            break
            
    env.close()
    
    os.makedirs("data/raw", exist_ok=True)
    np.save("data/raw/traffic_data_50k.npy", np.array(dataset))
    print(f"Data collection complete. Shape: {np.array(dataset).shape}")
    print(f"Features: [q_N, q_S, q_E, q_W, q_NR, q_SR, q_ER, q_WR, ped]")

if __name__ == "__main__":
    collect_data()
