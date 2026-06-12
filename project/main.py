import time
import sys
import os
import subprocess
import numpy as np

# Project root for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from edge.vision_node_safe import simulate_edge_vision
from brain.optimizer import TrafficRLAgent
from brain.llm_assistant import HQAssistantLLM
from brain.routing import CityGraphRouter
from simulation.traffic_sim import IntersectionSimulator
from core.db_client import RedisClient, TimescaleClient, Neo4jClient
from brain.rl_trainer import RLlibTrainer
from core.data_bus import bus
from core.optimization import SCOOTController, GeneticSignalOptimizer

redis_client = RedisClient()
timescale_client = TimescaleClient()

def ensure_trained_model():
    """Train RLlib model if checkpoint missing (Skip if Ray unavailable)."""
    try:
        from brain.rl_trainer import is_ray_available
    except ImportError:
        is_ray_available = False
        
    if not is_ray_available:
        print("[SYSTEM] Ray unavailable. Skipping training, using heuristic fallback.")
        return

    checkpoint_dir = "./brain/models/rllib_traffic"
    if not os.path.exists(checkpoint_dir) or not os.listdir(checkpoint_dir):
        print("[SYSTEM] No RLlib checkpoints found. Training now...")
        from brain.rl_trainer import RLlibTrainer
        trainer = RLlibTrainer(model_dir=checkpoint_dir)
        trainer.train(total_timesteps=4000)  # Quick train iteration
        print("[SYSTEM] Training complete!")

def start_system():
    """
    Full DAITFO system with auto-training.
    """
    print("\n" + "="*60)
    print("Dynamic AI Traffic Flow Optimizer (DAITFO) v3.0 - FULL AI")
    print("RL: PPO | Sim: Realistic Gym | Cameras: Ready for Real")
    print("="*60)
    
    # Ensure model trained
    ensure_trained_model()
    
    print("[SYSTEM] Booting components...")
    
    # Init
    sim = IntersectionSimulator("INT_001")
    agent = TrafficRLAgent("INT_001")
    assistant = HQAssistantLLM()
    router = CityGraphRouter()
    scoot = SCOOTController()
    genetic_optimizer = GeneticSignalOptimizer(n_intersections=1)
    
    print("[SYSTEM] AI-Enhanced system ready. Running infinite cycle...")
    
    # State tracking
    current_action = 0 # Default N-S (matching simulator 0=NS)
    cycle_start_time = time.time()
    tick_count = 0
    phase_labels = {0: "N-S", 1: "E-W", 2: "N", 3: "S", 4: "E", 5: "W"}
    inv_phase_labels = {v: k for k, v in phase_labels.items()}
    
    try:
        while True:
            tick_count += 1
            
            # 1. Read persistent state and configuration from Redis
            redis_state = redis_client.get_live_state("INT_001")
            config_duration = int(redis_state.get("config_duration", 35))
            phase_override = redis_state.get("phase_override")
            cycle_reset = redis_state.get("cycle_reset") == "True"
            is_emergency = redis_state.get("emergency_active", "False") == "True"
            
            # 2. Check for timer expiration or manual reset
            elapsed = time.time() - cycle_start_time
            if cycle_reset or elapsed >= config_duration:
                print(f"\n[CYCLE RESET] Triggered (Manual={cycle_reset}, Elapsed={elapsed:.1f}s)")
                
                # Update Sim State for decision
                raw_state = sim.queues
                metadata = simulate_edge_vision(raw_state)
                
                if phase_override and phase_override in inv_phase_labels:
                    current_action = inv_phase_labels[phase_override]
                    # Map back to simulator's 0/1 if it's a corridor
                    if current_action > 1:
                        # For single lanes, simulator defaults to E-W (1) for anything not 0.
                        # This simulator is simple 2-phase. We treat 0=NS, anything else=EW.
                        sim_action = 0 if current_action in [0, 2, 3] else 1
                    else:
                        sim_action = current_action
                    active_phase = "NS" if sim_action == 0 else "EW"
                    print(f"[BRAIN] Manual Override selected: {phase_override} (Sim Action: {sim_action})")
                else:
                    raw_action = agent.compute_action(metadata)
                    # Agent returns string like 'N-S Green'
                    sim_action = 0 if 'N-S' in str(raw_action).upper() else 1
                    current_action = sim_action
                    active_phase = "NS" if sim_action == 0 else "EW"
                    print(f"[BRAIN/RL] RL Phase: {phase_labels[current_action]}")
                
                # Pass metadata, Timescale client to SCOOT split optimizer
                config_duration = scoot.optimize_splits(active_phase, metadata, database_client=timescale_client)
                print(f"[BRAIN/SCOOT] SCOOT Optimized Split Duration for {active_phase}: {config_duration}s")
                
                cycle_start_time = time.time()
                elapsed = 0
                redis_client.update_live_state("INT_001", {"cycle_reset": "False", "phase_override": ""})
            else:
                # Use current sim_action if not resetting
                sim_action = 0 if current_action in [0, 2, 3] else 1

            # 3. Emergency Override (Maintains highest priority)
            if is_emergency:
                start_node = redis_state.get("emergency_start", "INT_005")
                end_node = redis_state.get("emergency_end", "INT_001")
                
                path, et = [], 0
                # Use the Neo4j Graph Engine via Router
                if router.client.connected:
                    try:
                        path, et = router.find_emergency_path(start_node, end_node)
                    except Exception:
                        pass
                
                if not path:
                    print("[ROUTING] Neo4j Offline/Path Not Found. Using Heuristic (Direct Path)...")
                    path = [start_node, "INT_003", end_node]
                    et = 45
                
                if "INT_001" in path:
                    sim_action = 0 # Force N-S Green
                    current_action = 0
                    print(f"[EMERGENCY] Routing {start_node}->{end_node} | OVERRIDE: Forcing N-S Green Corridor.")

            # 4. Calculate real-time countdown
            countdown = max(0, int(config_duration - elapsed))
            
            # 5. Execute Simulation Step
            raw_state = sim.queues
            metadata = simulate_edge_vision(raw_state)
            new_raw_state = sim.step(sim_action)
            new_metadata = simulate_edge_vision(new_raw_state)
            reward = agent.compute_reward(metadata, new_metadata)
            
            # Publish telemetry to DataBus
            try:
                bus.publish("traffic.raw.metadata", metadata)
            except Exception as e:
                print(f"[BUS] Publish error: {e}")
            
            print(f"[TICK {tick_count}] Phase: {phase_labels.get(current_action, 'N-S')} | Countdown: {countdown}s | Reward: {reward:.1f}")

            # 6. LLM query (every 20 ticks for performance)
            if tick_count % 20 == 0:
                q = f"Analyze tick {tick_count}: queues {raw_state}"
                try:
                    assistant.query_system(q, metadata)
                except Exception:
                    pass
                
                # Run background Genetic Signal Optimizer
                try:
                    demand = [{"queues": raw_state, "vpm": metadata["counts"]}]
                    plan_data = genetic_optimizer.optimize(demand)
                    redis_client.update_live_state("INT_001", {
                        "genetic_plan": str(plan_data.get("plan", []))
                    })
                    print(f"[BRAIN/GENETIC] Genetic Optimizer recommendation published: {plan_data}")
                except Exception as e:
                    print(f"[GENETIC] Optimization error: {e}")
            
            # 7. Sync to Redis for Dashboard display
            try:
                redis_client.update_live_state("INT_001", {
                    "queue_N": raw_state["N"], "queue_S": raw_state["S"], 
                    "queue_E": raw_state["E"], "queue_W": raw_state["W"],
                    "vpm_N": metadata["counts"]["N"], "vpm_S": metadata["counts"]["S"],
                    "vpm_E": metadata["counts"]["E"], "vpm_W": metadata["counts"]["W"],
                    "green_lights": phase_labels.get(current_action, "N-S"),
                    "reward": round(reward, 2),
                    "ai_duration": config_duration,
                    "ai_reasoning": "RLlib PPO Agent optimized phase for throughput." if not phase_override else f"Manual override: {phase_override}",
                    "cycle_countdown": countdown,
                    "pi": round(max(0, 8.5 - reward), 2)
                })
            except Exception as e:
                print(f"[REDIS] Sync error: {e}")

            # 8. Update Neo4j Graph Weights (Every 10 ticks)
            if tick_count % 10 == 0:
                try:
                    n4j = Neo4jClient()
                    if n4j.connected:
                        avg_vpm = sum(metadata["counts"].values()) / 4
                        n4j.update_edge_weight("INT_005", "INT_001", 1.0 + (avg_vpm / 20))
                        n4j.update_edge_weight("INT_001", "INT_004", 1.0 + (avg_vpm / 20))
                        print(f"[GRAPH] Sync: Updated INT_001 edge weights (Avg VPM: {avg_vpm:.1f})")
                except Exception as e:
                    print(f"[GRAPH] Sync error: {e}")

            time.sleep(1.0)


    except KeyboardInterrupt:
        print("\n[SYSTEM] Graceful shutdown.")
    
    print("\n🎉 [COMPLETE] RL-powered simulation ran successfully!")
    print("Next: Install deps, train model, run `python main.py`.")
    print("For real cams: Phase 2.")

if __name__ == "__main__":
    start_system()

