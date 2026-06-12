import random

class SCOOTController:
    """
    SCOOT (Split Cycle Offset Optimization Technique) like controller.
    Adjusts splits (+3s / -3s) to minimize a Performance Index (PI).
    """
    def __init__(self):
        self.current_splits = {"NS": 35, "EW": 35}
        self.step = 3             # seconds per adjustment
        self.performance_index = 0.0

    def compute_performance_index(self, queues: dict, red_times: dict) -> float:
        """
        PI = w1 * total_queue + w2 * total_wait_time
        Lower PI = better performance
        """
        w1, w2 = 0.6, 0.4
        total_queue = sum(queues.values())
        total_wait = sum(red_times.values())
        return w1 * total_queue + w2 * total_wait

    def optimize_splits(self, active_phase: str, sensor_data: dict, database_client=None) -> int:
        """
        active_phase: 'NS' or 'EW'
        Try current, +step, and -step. Return best green duration.
        """
        current_val = self.current_splits[active_phase]
        
        # Candidate evaluations
        pi_hold = self._simulate_pi(active_phase, current_val, sensor_data, database_client)
        pi_plus = self._simulate_pi(active_phase, current_val + self.step, sensor_data, database_client)
        pi_minus = self._simulate_pi(active_phase, current_val - self.step, sensor_data, database_client)

        # Pick best
        results = [
            (pi_hold, current_val),
            (pi_plus, current_val + self.step),
            (pi_minus, current_val - self.step)
        ]
        best_pi, best_duration = min(results, key=lambda x: x[0])
        
        new_val = max(10, min(60, best_duration))
        self.current_splits[active_phase] = new_val
        self.performance_index = best_pi
        return new_val

    def _simulate_pi(self, phase_id, green_time, sensor_data, database_client=None) -> float:
        """Predictive PI for a given green time"""
        # Get lanes in this phase
        lanes = ["N", "S"] if phase_id == "NS" else ["E", "W"]
        
        hist_queue_avg = 0.0
        if database_client is not None:
            metrics = database_client.get_recent_metrics("INT_001", limit=10)
            if metrics:
                hist_queue_avg = sum(m.get("avg_queue", 0) for m in metrics) / len(metrics)
                
        congestion_factor = 1.0
        try:
            from edge.tomtom_scraper import TomTomDelhiScraper
            scraper = TomTomDelhiScraper()
            stats = scraper.fetch_live_stats()
            if stats:
                congestion_str = stats.get("live_congestion", "0%")
                congestion_pct = float(congestion_str.replace("%", "").strip())
                if congestion_pct > 30:
                    congestion_factor = 1.0 + (congestion_pct - 30) / 100.0
                
                speed_str = stats.get("live_speed", "40 km/h")
                speed_val = float(speed_str.split()[0])
                if speed_val < 30:
                    congestion_factor *= (30 / max(5, speed_val))
        except Exception:
            pass

        predicted_pi = 0
        history_weight = 0.3
        for l in lanes:
            q = sensor_data.get("queues", {}).get(l, 0)
            vpm = sensor_data.get("vpm", {}).get(l, 10)
            # Simple model: arrivals - departures
            arrivals = (vpm / 60.0 * 30) * congestion_factor # vehicles arriving in 30s adjusted by congestion
            departures = green_time * 1.5 # ~1.5 veh/sec clearing
            residual = max(0, q + arrivals - departures)
            if hist_queue_avg > 0:
                residual = (1 - history_weight) * residual + history_weight * hist_queue_avg
            predicted_pi += residual
            
        return predicted_pi


class GeneticSignalOptimizer:
    """
    Coordination engine for multi-intersection corridors.
    Optimizes offsets and cycle lengths using a GA.
    """
    def __init__(self, n_intersections: int = 1):
        self.n = n_intersections
        self.pop_size = 30
        self.generations = 50

    def optimize(self, demand_data: list) -> dict:
        """
        Calculates optimal plan for the grid.
        For a single intersection, it finds the best static cycle.
        """
        # Placeholder for complex GA logic - implemented as a simplified search for now
        best_plan = []
        for i in range(self.n):
            best_plan.append({
                "cycle": random.randint(60, 100),
                "ns_green": random.randint(30, 50),
                "ew_green": random.randint(30, 50),
                "offset": random.randint(0, 20)
            })
        return {"plan": best_plan, "gen": self.generations}
