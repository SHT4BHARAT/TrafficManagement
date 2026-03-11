import time
import random

class IntersectionSimulator:
    """
    A simple Python-based traffic simulator for a 4-way intersection.
    Generates queue lengths and vehicle types for training the RL agent.
    """
    def __init__(self, intersection_id):
        self.intersection_id = intersection_id
        # State: [North, South, East, West] queue counts
        self.queues = {"N": 0, "S": 0, "E": 0, "W": 0}
        self.current_phase = "N-S Green"
        print(f"[SIM] Simulator started for {self.intersection_id}")

    def step(self, action=None):
        """
        Advances the simulation by one time step (e.g., 5 seconds).
        Action: The signal phase decided by the RL agent.
        """
        # 1. Spawn new vehicles (Random inflow)
        for lane in self.queues:
            self.queues[lane] += random.randint(0, 5)

        # 2. Apply Signal Action (Discharge vehicles)
        if action:
            self.current_phase = action
        
        print(f"[SIM] Phase: {self.current_phase} | Queues: {self.queues}")
        
        # Simple discharge logic: Green lanes lose 8 vehicles, Red lanes lose 0.
        if "N-S Green" in self.current_phase:
            self.queues["N"] = max(0, self.queues["N"] - 8)
            self.queues["S"] = max(0, self.queues["S"] - 8)
        elif "E-W Green" in self.current_phase:
            self.queues["E"] = max(0, self.queues["E"] - 8)
            self.queues["W"] = max(0, self.queues["W"] - 8)

        return self.queues

    def run_loop(self, steps=10):
        for i in range(steps):
            print(f"--- Step {i+1} ---")
            self.step()
            time.sleep(1)

if __name__ == "__main__":
    sim = IntersectionSimulator("INT_001")
    sim.run_loop()
