import gymnasium as gym
import numpy as np
from gymnasium import spaces
import random
from typing import Dict, Any
import time

class TrafficIntersectionEnv(gym.Env):
    """
    Gymnasium-compatible environment for 4-way intersection traffic signal control.
    State: normalized queue lengths [N,S,E,W].
    Action: 0='N-S Green', 1='E-W Green'.
    Reward: queue reduction + fairness.
    """
    def __init__(self, max_episode_steps=1000):
        super().__init__()
        
        self.max_episode_steps = max_episode_steps
        self.current_step = 0
        
        # Realistic params
        self.max_queue = 100
        self.discharge_rates = {'NS': 12, 'EW': 12}
        self.arrival_rates = [1.5, 4.5]  # low/peak Poisson lambda
        self.peak_hour_prob = 0.4
        
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        
        self.action_meanings = ['N-S Green', 'E-W Green']
        self.last_action = None
        self.queues = np.zeros(4, dtype=np.float32)
        self.last_total_queue = 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.queues = np.random.poisson(3, 4).astype(np.float32)
        self.last_total_queue = np.sum(self.queues)
        self.last_action = None
        obs = self._get_obs()
        return obs, {}

    def step(self, action):
        # Handle string action from agent fallback
        if isinstance(action, str):
            if 'N-S' in action.upper():
                action = 0
            else:
                action = 1
        
        self.last_action = int(action)
        
        # Discharge array: [N, S, E, W]
        discharge = np.zeros(4)
        if action == 0:  # N-S
            discharge[0] = self.discharge_rates['NS']
            discharge[1] = self.discharge_rates['NS']
        elif action == 1:  # E-W
            discharge[2] = self.discharge_rates['EW']
            discharge[3] = self.discharge_rates['EW']
        
        # Arrivals Poisson
        is_peak = random.random() < self.peak_hour_prob
        lam = self.arrival_rates[1] if is_peak else self.arrival_rates[0]
        arrivals = np.random.poisson(lam, 4)
        
        # Update queues
        for i in range(4):
            self.queues[i] = np.clip(self.queues[i] + arrivals[i] - discharge[i], 0, self.max_queue)
        
        self.current_step += 1
        
        # Reward
        total_queue = np.sum(self.queues)
        reduction = self.last_total_queue - total_queue
        fairness = -np.std(self.queues) * 0.2
        reward = reduction + fairness
        
        self.last_total_queue = total_queue
        obs = self._get_obs()
        
        terminated = total_queue > 400
        truncated = self.current_step >= self.max_episode_steps
        
        info = {
            'queues_raw': self.queues.tolist(), 
            'action_meaning': self.action_meanings[int(action)]
        }
        
        return obs, reward, terminated, truncated, info

    def _get_obs(self):
        return self.queues / self.max_queue

    def render(self):
        print(f"Step {self.current_step} | Queues N/S/E/W: {self.queues.tolist()} | Phase: {self.action_meanings[self.last_action] if self.last_action is not None else 'None'}")

# Backward compatibility wrapper
class IntersectionSimulator:
    def __init__(self, intersection_id):
        self.env = TrafficIntersectionEnv()
        self.intersection_id = intersection_id
        print(f"[SIM] Gym-wrapped simulator for {self.intersection_id}")

    @property
    def queues(self):
        return dict(zip(['N','S','E','W'], self.env.queues.tolist()))

    def step(self, action=None):
        if action is None:
            action = self.env.action_space.sample()
        obs, rew, term, trunc, info = self.env.step(action)
        self.env.render()
        return dict(zip(['N','S','E','W'], info['queues_raw']))

    def run_loop(self, steps=10):
        obs, _ = self.env.reset()
        for i in range(steps):
            print(f"--- Step {i+1} ---")
            self.step()
            time.sleep(0.5)
            if self.env.current_step >= self.env.max_episode_steps:
                obs, _ = self.env.reset()

if __name__ == "__main__":
    # Test
    env = TrafficIntersectionEnv()
    obs, _ = env.reset()
    print("Obs shape:", obs.shape)
    for _ in range(5):
        action = env.action_space.sample()
        obs, rew, term, trunc, info = env.step(action)
        print(f"Action: {action} ({env.action_meanings[action]}), Reward: {rew:.2f}")
        if term or trunc:
            obs, _ = env.reset()
            print("Episode reset")
