import numpy as np
import os
from typing import Dict, Any

# Optional: Ray RLlib for Production
try:
    import ray
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.tune.registry import register_env
    is_ray_available = True
except ImportError:
    print("[WARN] Ray/RLlib not found. Using Heuristic RL Agent (Python 3.13 Compatibility Mode).")
    is_ray_available = False
    PPOConfig = None

# Mock/Import environment for registration if needed
try:
    from simulation.traffic_sim import TrafficIntersectionEnv
except ImportError:
    TrafficIntersectionEnv = None

class TrafficRLAgent:
    """
    Production RL Agent using Ray RLlib PPO policy.
    Connects to an RLlib Algorithm instance to predict optimal traffic phases.
    """
    def __init__(self, intersection_id: str):
        self.intersection_id = intersection_id
        self.checkpoint_path = "./brain/models/rllib_traffic/checkpoint_000001"
        self.action_meanings = ['N-S Green', 'E-W Green']
        self.total_reward = 0.0
        self.last_state = None
        
        if is_ray_available:
            # Initialize Ray if not already running
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True, local_mode=True)
            self._load_algorithm()
            print(f"[BRAIN] RLlib PPO Agent initialized for {intersection_id}")
        else:
            self.algo = None
            print(f"[BRAIN] COMPATIBILITY MODE: Heuristic Agent active for {intersection_id}")

    def _load_algorithm(self):
        """Build and load RLlib Algorithm from checkpoint."""
        if not is_ray_available:
            return
        # Register the environment for Ray
        if TrafficIntersectionEnv:
            try:
                register_env("TrafficIntersectionEnv", lambda config: TrafficIntersectionEnv())
            except Exception:
                pass
        # Simple config for PPO
        config = PPOConfig().environment(env="TrafficIntersectionEnv" if TrafficIntersectionEnv else "CartPole-v1")
        config = config.framework("torch").rollouts(num_rollout_workers=0)
        
        self.algo = config.build()
        
        if os.path.exists(self.checkpoint_path):
            try:
                self.algo.restore(self.checkpoint_path)
                print(f"[BRAIN] Restored RLlib checkpoint from {self.checkpoint_path}")
            except Exception as e:
                print(f"[WARN] Failed to restore checkpoint: {e}. Using new weights.")
        else:
            print(f"[WARN] No checkpoint at {self.checkpoint_path}. Agent will use random/initial weights.")

    def _normalize_state(self, state: Any) -> Dict:
        """Standardize incoming sensor data."""
        if isinstance(state, dict):
            if 'counts' in state:
                return state['counts']
            return state
        return {'N': 0, 'S': 0, 'E': 0, 'W': 0}

    def _state_to_obs(self, state: Dict) -> np.ndarray:
        """Map queue counts to normalized [N,S,E,W] vector."""
        queues = np.array([
            state.get('N', 0),
            state.get('S', 0),
            state.get('E', 0),
            state.get('W', 0)
        ], dtype=np.float32)
        return queues / 100.0

    def compute_action(self, state: Any) -> str:
        """Predict optimal phase using Ray RLlib (or heuristic if missing)."""
        counts = self._normalize_state(state)
        obs = self._state_to_obs(counts)
        
        # RLlib compute_single_action
        if is_ray_available and self.algo:
            try:
                action = self.algo.compute_single_action(obs, explore=False)
                phase = self.action_meanings[action]
                print(f"[BRAIN] RLlib Action: {action} -> {phase}, obs: {obs}")
                self.last_state = state
                return phase
            except Exception as e:
                print(f"[ERROR] RLlib inference failed: {e}. Falling back to heuristic.")
        
        # Heuristic Fallback (Smart Mode)
        ns = counts.get('N', 0) + counts.get('S', 0)
        ew = counts.get('E', 0) + counts.get('W', 0)
        phase = self.action_meanings[0 if ns >= (ew + 2) else 1] # Slight bias to NS for stability
        if not is_ray_available:
            print(f"[BRAIN] Heuristic Action: {phase} (Ray Unavailable), obs: {obs}")
            
        self.last_state = state
        return phase

    def compute_reward(self, prev_state: Any, curr_state: Any) -> float:
        """Calculate reward based on queue reduction."""
        prev_norm = self._normalize_state(prev_state)
        curr_norm = self._normalize_state(curr_state)
        prev_sum = sum(prev_norm.values())
        curr_sum = sum(curr_norm.values())
        reward = prev_sum - curr_sum
        self.total_reward += reward
        return reward

if __name__ == "__main__":
    agent = TrafficRLAgent("INT_001")
    test_state = {"counts": {"N": 20, "S": 10, "E": 5, "W": 15}}
    print(f"RLlib Suggested Action: {agent.compute_action(test_state)}")
