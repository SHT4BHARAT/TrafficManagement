import heapq

class CityGraphRouter:
    """
    Simulates Neo4j Graph Routing logic using a priority-based Dijkstra algorithm.
    Used for creating dynamic 'Green Corridors' for emergency vehicles.
    """
    def __init__(self):
        # Graph represented as an adjacency list: {node: {neighbor: weight}}
        # Nodes are intersections, weights are travel times based on distance/congestion.
        self.graph = {
            "INT_001": {"INT_002": 5, "INT_005": 10},
            "INT_002": {"INT_001": 5, "INT_003": 3, "INT_006": 8},
            "INT_003": {"INT_002": 3, "INT_004": 2},
            "INT_004": {"INT_003": 2, "INT_007": 6},
            "INT_005": {"INT_001": 10, "INT_006": 4},
            "INT_006": {"INT_005": 4, "INT_002": 8, "INT_007": 7},
            "INT_007": {"INT_006": 7, "INT_004": 6}
        }
        print("[ROUTING] City Graph initialized (7 Intersections).")

    def find_emergency_path(self, start_node, end_node):
        """
        Computes the fastest path for an emergency vehicle.
        Uses Dijkstra's algorithm to simulate Neo4j's shortestPath.
        """
        queue = [(0, start_node, [])]
        seen = set()
        
        while queue:
            (cost, node, path) = heapq.heappop(queue)
            if node not in seen:
                path = path + [node]
                seen.add(node)
                
                if node == end_node:
                    return path, cost
                
                for next_node, weight in self.graph.get(node, {}).items():
                    heapq.heappush(queue, (cost + weight, next_node, path))
        
        return None, float('inf')

    def trigger_green_corridor(self, path):
        """
        Simulates the 'Force Green' signal override across the computed path.
        """
        print(f"[CORRIDOR] Activating Green Wave for path: {' -> '.join(path)}")
        for node in path:
            print(f"[ACTUATION] Node {node}: Signal forced to EMERGENCY_GREEN.")

if __name__ == "__main__":
    router = CityGraphRouter()
    start = "INT_005"
    end = "INT_004"
    path, time = router.find_emergency_path(start, end)
    
    if path:
        print(f"[ROUTING] Optimal Emergency Route: {path} (Estimated Time: {time}s)")
        router.trigger_green_corridor(path)
    else:
        print("[ROUTING] No valid path found for emergency responder.")
