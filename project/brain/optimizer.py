class TrafficRLAgent:
    """
    Skeleton for the MADDPG Traffic Optimizer Agent.
    Interfaces with the state space (density) to determine optimal signal phases.
    """
    def __init__(self, intersection_id):
        self.intersection_id = intersection_id
        self.last_state = None
        self.total_reward = 0
        print(f"[BRAIN] Initializing RL Agent for {self.intersection_id}")

    def _normalize_state(self, state):
        """
        Normalizes state to always return queue counts dict {"N": x, "S": y, "E": z, "W": w}.
        Handles both metadata format (with 'counts' key) and direct queue dict.
        """
        if isinstance(state, dict):
            # If state contains 'counts' key (from edge vision), extract it
            if "counts" in state:
                return state["counts"]
            # Otherwise assume it's already a queue dict
            return state
        # Fallback for non-dict states
        return {"N": 0, "S": 0, "E": 0, "W": 0}
    def compute_reward(self, prev_state, current_state):
        """
        Calculates the reward based on the reduction of queue lengths.
        Positive reward for queue reduction (better performance).
        """
        # Normalize both states to standard queue dict format
        prev_queue = sum(self._normalize_state(prev_state).values())
        curr_queue = sum(self._normalize_state(current_state).values())
        
        # Reward is the reduction in queue length (positive = good)
        reward = prev_queue - curr_queue
        self.total_reward += reward
        return reward

    def compute_action(self, state):
        """
        Takes the current intersection state and returns the optimal signal phase.
        Decision logic: Priority to lanes with the longest queues.
        """
        # Normalize state to standard queue dict format
        counts = self._normalize_state(state)
        
        ns_count = counts.get("N", 0) + counts.get("S", 0)
        ew_count = counts.get("E", 0) + counts.get("W", 0)

        # Basic action selection
        if ns_count >= ew_count:
            action = "N-S Green"
        else:
            action = "E-W Green"
        
        self.last_state = state
        return action

if __name__ == "__main__":
    import random
    agent = TrafficRLAgent("INT_001")
    dummy_state = {"queue_length": 15}
    print(f"[BRAIN] Suggested Action: {agent.compute_action(dummy_state)}")
