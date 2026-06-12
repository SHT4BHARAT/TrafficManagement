import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db_client import Neo4jClient

class CityGraphRouter:
    """
    Uses Neo4j Graph Routing engine for creating dynamic 'Green Corridors'.
    """
    def __init__(self):
        self.client = Neo4jClient()
        print("[ROUTING] Connected to Neo4j Graph Engine.")

    def _local_bfs_shortest_path(self, start, end):
        """Local BFS pathfinder fallback over the 20-node grid layout."""
        try:
            # Reconstruct grid connections
            adj = {}
            for r in range(4):
                for c in range(5):
                    idx = r * 5 + c + 1
                    u = f"INT_{idx:03d}"
                    adj[u] = set()
            # Add grid connections
            for r in range(4):
                for c in range(5):
                    idx = r * 5 + c + 1
                    u = f"INT_{idx:03d}"
                    if c < 4:
                        v = f"INT_{idx+1:03d}"
                        adj[u].add(v)
                        adj[v].add(u)
                    if r < 3:
                        v = f"INT_{idx+5:03d}"
                        adj[u].add(v)
                        adj[v].add(u)
            # Add diagonals
            diagonals = [("INT_001", "INT_007"), ("INT_005", "INT_009"), ("INT_011", "INT_017")]
            for u, v in diagonals:
                if u in adj and v in adj:
                    adj[u].add(v)
                    adj[v].add(u)
            
            # BFS
            if start not in adj or end not in adj:
                return None, float('inf')
            
            queue = [[start]]
            visited = {start}
            while queue:
                path = queue.pop(0)
                node = path[-1]
                if node == end:
                    return path, float(len(path) - 1)
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(path + [neighbor])
        except Exception as e:
            print(f"[ROUTING] Local BFS error: {e}")
        return None, float('inf')

    def find_emergency_path(self, start_node, end_node):
        """
        Computes the fastest path for an emergency vehicle using Neo4j shortestPath.
        If Neo4j is offline, falls back to a local BFS heuristic.
        """
        if self.client.connected:
            try:
                result = self.client.find_shortest_path(start_node, end_node)
                if result:
                    return result['path'], result['totalCost']
            except Exception as e:
                print(f"[ROUTING] Neo4j Pathfinding Error: {e}. Falling back to Heuristic.")
        else:
            print("[ROUTING] Neo4j Offline. Falling back to Heuristic.")
            
        return self._local_bfs_shortest_path(start_node, end_node)

    def trigger_green_corridor(self, path):
        """
        Simulates the 'Force Green' signal override across the computed path.
        Actuates all intersections along the path by updating their live state in Redis.
        """
        if not path: return
        
        print(f"[CORRIDOR] 🚑 Activating Green Wave: {' -> '.join(path)}")
        # Mark the corridor in Redis for the dashboard for all intersections in the route
        from core.db_client import RedisClient
        r = RedisClient()
        for node in path:
            r.update_live_state(node, {
                "emergency_active": "True",
                "emergency_path": ",".join(path),
                "emergency_start": path[0],
                "emergency_end": path[-1]
            })

if __name__ == "__main__":
    router = CityGraphRouter()
    # Test with seeded nodes
    start, end = "INT_005", "INT_004"
    path, cost = router.find_emergency_path(start, end)
    
    if path:
        print(f"[ROUTING] Optimal Emergency Route: {path} (Cost: {cost})")
        router.trigger_green_corridor(path)
    else:
        print("[ROUTING] No valid path found.")
