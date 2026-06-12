import os

# Optional: Ray RLlib for Production
try:
    import ray
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.tune.registry import register_env
    is_ray_available = True
except ImportError:
    print("[WARN] Ray/RLlib not found. RL Trainer disabled (Heuristic mode logic only).")
    is_ray_available = False
    PPOConfig = None

try:
    from simulation.traffic_sim import TrafficIntersectionEnv
except ImportError:
    TrafficIntersectionEnv = None

class RLlibTrainer:
    """
    Ray RLlib Trainer for Traffic Optimization.
    Replaces Stable-Baselines3 with a scalable, multi-agent capable framework.
    """
    def __init__(self, model_dir="./brain/models/rllib_traffic"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        if is_ray_available:
            # Initialize Ray
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True)
                
            # Register the environment
            register_env("TrafficIntersectionEnv", lambda config: TrafficIntersectionEnv())
            print(f"[RL] RLlib Trainer initialized. Directory: {self.model_dir}")
        else:
            print("[RL] RL Training not supported in this environment.")

    def train(self, total_timesteps=100000):
        """Train PPO policy using Ray RLlib."""
        print(f"[RL] Building RLlib PPO Configuration...")
        
        config = (
            PPOConfig()
            .environment(env="TrafficIntersectionEnv")
            .framework("torch")
            .rollouts(num_rollout_workers=2)  # Parallel workers
            .resources(num_gpus=0)           # Set to 1 if GPU available
            .training(
                lr=3e-4,
                train_batch_size=4000,
                sgd_minibatch_size=128,
                num_sgd_iter=10
            )
        )
        
        algo = config.build()
        
        print(f"[RL] Starting RLlib training for {total_timesteps} iterations...")
        # Note: RLlib 'train()' is usually one iteration. 
        # We'll loop through iterations equivalent to timesteps
        iterations = total_timesteps // 4000
        
        for i in range(iterations):
            result = algo.train()
            print(f"Iteration {i}: reward_mean={result.get('episode_reward_mean'):.2f}")
            
            if i % 10 == 0:
                checkpoint_dir = algo.save(self.model_dir)
                print(f"Saved checkpoint to {checkpoint_dir}")
        
        final_checkpoint = algo.save(self.model_dir)
        print(f"[RL] Training complete! Final checkpoint: {final_checkpoint}")
        return algo

if __name__ == "__main__":
    trainer = RLlibTrainer()
    trainer.train(total_timesteps=50000)
