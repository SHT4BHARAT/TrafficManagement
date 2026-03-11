import time
import sys
import os

# Add the project root to sys.path for proper module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project.edge.vision_node import simulate_edge_vision
from project.brain.optimizer import TrafficRLAgent
from project.brain.llm_assistant import HQAssistantLLM
from project.brain.routing import CityGraphRouter
from project.simulation.traffic_sim import IntersectionSimulator

def start_system():
    """
    Initializes the Dynamic AI Traffic Flow Optimizer system.
    """
    print("\n--- Dynamic AI Traffic Flow Optimizer (DAITFO) v2.0 ---")
    print("[SYSTEM] Booting Core Orchestrator...")
    
    # Initialize components
    sim = IntersectionSimulator("INT_001")
    agent = TrafficRLAgent("INT_001")
    assistant = HQAssistantLLM()
    router = CityGraphRouter()
    
    print("[SYSTEM] System ready. Running closed-loop simulation...")
    
    try:
        for i in range(10):
            print(f"\n[Cycle {i+1}]")
            
            # 1. Simulator generates internal state
            raw_state = sim.queues
            
            # 2. Edge Vision processes state into metadata
            metadata = simulate_edge_vision(raw_state)
            print(f"[EDGE] Processed metadata: {metadata['counts']}")
            
            # 3. Brain computes optimal action (RL)
            action = agent.compute_action(metadata)
            print(f"[BRAIN] Optimal Phase: {action}")
            
            # 4. Simulator applies action for next step
            new_raw_state = sim.step(action)
            new_metadata = simulate_edge_vision(new_raw_state)
            
            # 5. Calculate Reward (Evaluation)
            reward = agent.compute_reward(metadata, new_metadata)
            print(f"[BRAIN] Reward for this move: {reward} (Total: {agent.total_reward})")
            
            # 6. Emergency Routing Trigger (Simulation)
            if i == 5:
                print("\n[ALERT] Emergency Responder Ping Detected!")
                start_node, end_node = "INT_005", "INT_004"
                path, time_val = router.find_emergency_path(start_node, end_node)
                print(f"[ROUTING] Fastest Route: {path} ({time_val}s)")
                router.trigger_green_corridor(path)
            
            # 7. Opportunity for LLM Query (Simulation)
            if i % 8 == 0:
                q = f"Describe the current bottleneck and security protocols."
                print(f"[OPERATOR] '{q}'")
                print(f"{assistant.query_system(q, str(metadata))}")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("[SYSTEM] Shutting down...")
    
    print("\n[SYSTEM] Simulation complete.")

if __name__ == "__main__":
    start_system()
