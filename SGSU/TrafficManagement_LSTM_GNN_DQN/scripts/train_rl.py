import yaml
import gymnasium
import gymnasium as gym
import numpy as np
import torch
import os
import sys
from stable_baselines3 import DQN

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env.sumo_env import SumoTrafficEnv
from models.traffic_lstm import TrafficLSTM

class LSTMAugmentedEnv(gym.Wrapper):
    """
    Wraps SumoTrafficEnv to augment state with LSTM prediction.
    Input: 9 features → Output: 10 features (9 + 1 LSTM pred)
    """
    def __init__(self, env, lstm_model, seq_len):
        super(LSTMAugmentedEnv, self).__init__(env)
        self.lstm = lstm_model
        self.seq_len = seq_len
        self.buffer = []
        
        # 9 env features + 1 LSTM prediction = 10
        self.observation_space = gymnasium.spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )

    def reset(self, seed=None, options=None):
        state, info = self.env.reset(seed=seed, options=options)
        self.buffer = [state for _ in range(self.seq_len)]
        return self._augment(state), info

    def step(self, action):
        next_state, reward, terminated, truncated, info = self.env.step(action)
        self.buffer.pop(0)
        self.buffer.append(next_state)
        return self._augment(next_state), reward, terminated, truncated, info

    def _augment(self, state):
        seq = torch.FloatTensor(np.array(self.buffer)).unsqueeze(0)
        with torch.no_grad():
            pred = self.lstm(seq).item()
        return np.append(state, [pred]).astype(np.float32)

def train_dqn():
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    params = config["training"]
    lstm = TrafficLSTM(input_size=params["input_size"], 
                       hidden_size=params["hidden_size"])
    weights = os.path.join(params["checkpoint_dir"], "lstm_weights.pth")
    if os.path.exists(weights):
        lstm.load_state_dict(torch.load(weights, map_location="cpu"))
        print("Loaded pre-trained LSTM.")
    lstm.eval()

    base_env = SumoTrafficEnv(config)
    env = LSTMAugmentedEnv(base_env, lstm, params["sequence_len"])

    dqn_cfg = config["dqn"]
    model = DQN(
        dqn_cfg["policy"],
        env,
        learning_rate=dqn_cfg["learning_rate"],
        buffer_size=dqn_cfg["buffer_size"],
        batch_size=dqn_cfg["batch_size"],
        device="cpu",
        verbose=1
    )

    print(f"Training DQN ({dqn_cfg['total_timesteps']} steps, 5 phases)...")
    model.learn(total_timesteps=dqn_cfg["total_timesteps"])
    
    os.makedirs(params["checkpoint_dir"], exist_ok=True)
    model.save(os.path.join(params["checkpoint_dir"], "dqn_traffic_model"))
    print("DQN Training complete.")

if __name__ == "__main__":
    train_dqn()
