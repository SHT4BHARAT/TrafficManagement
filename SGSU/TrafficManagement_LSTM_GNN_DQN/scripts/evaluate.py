import yaml
import gymnasium as gym
import torch
import numpy as np
import os
import sys
from stable_baselines3 import DQN

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env.sumo_env import SumoTrafficEnv
from models.traffic_lstm import TrafficLSTM
from agents.emergency_agent import query_traffic_agent

PHASE_NAMES = ["NORTH", "SOUTH", "EAST", "WEST", "PEDESTRIAN"]

def evaluate():
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Enable GUI
    config["simulation"]["sumo_cmd"] = \
        "C:\\Program Files (x86)\\Eclipse\\Sumo\\bin\\sumo-gui.exe"
    
    params = config["training"]
    
    # Load LSTM
    lstm = TrafficLSTM(input_size=params["input_size"],
                       hidden_size=params["hidden_size"])
    weights = os.path.join(params["checkpoint_dir"], "lstm_weights.pth")
    if os.path.exists(weights):
        lstm.load_state_dict(torch.load(weights, map_location="cpu"))
    lstm.eval()

    # Load DQN
    model_path = os.path.join(params["checkpoint_dir"], "dqn_traffic_model")
    if not os.path.exists(model_path + ".zip"):
        print("DQN weights not found.")
        return
    model = DQN.load(model_path, device="cpu")
    print("Loaded DQN Model.")

    # Environment
    env = SumoTrafficEnv(config)
    state, _ = env.reset()
    buffer = [state for _ in range(params["sequence_len"])]
    
    print("Starting India LHD 5-Phase Evaluation...")
    print(f"Phases: {PHASE_NAMES}")
    done = False
    step_count = 0
    
    while not done:
        total_queue = sum(state[0:4])
        ped_count = state[8]
        
        # Emergency: if total queue > 50 or ped > 30
        if total_queue > 50 or ped_count > 30:
            if ped_count > 30:
                action = 4  # Force pedestrian scramble
                print(f"Step {step_count}: PED SCRAMBLE (ped={int(ped_count)})")
            else:
                # Find direction with highest queue
                action = int(np.argmax(state[0:4]))
                print(f"Step {step_count}: EMERGENCY → {PHASE_NAMES[action]} "
                      f"(queue={int(state[action])})")
        else:
            # Standard DQN + LSTM
            seq = torch.FloatTensor(np.array(buffer)).unsqueeze(0)
            with torch.no_grad():
                lstm_pred = lstm(seq).item()
            aug_state = np.append(state, [lstm_pred])
            action, _ = model.predict(aug_state, deterministic=True)
            
        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        
        buffer.pop(0)
        buffer.append(next_state)
        state = next_state
        step_count += 1

    env.close()
    print(f"Evaluation complete. {step_count} steps.")

if __name__ == "__main__":
    evaluate()
