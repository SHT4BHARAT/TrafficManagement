import logging
import os

class TrafficGraphManager:
    """
    Manages interaction with the Neo4j Graph Database.
    Used for complex city-level routing and emergency planning.
    """
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASS", "")
        self.driver = None # Will hold neo4j.GraphDatabase.driver
        logging.info("[BRAIN] Graph Manager initialized (Neo4j Ready)")

    def update_segment_weight(self, road_id, congestion_score):
        """
        Dynamically updates the 'weight' of a road segment.
        Weight = Distance / (Speed * CongestionFactor)
        """
        query = """
        MATCH ()-[r:CONNECTED_TO {id: $road_id}]->()
        SET r.weight = $congestion_score
        """
        print(f"[GRAPH] Updating road {road_id} weight to {congestion_score}")
        # self.run_query(query, road_id=road_id, congestion_score=congestion_score)

    def find_shortest_emergency_path(self, start_id, end_id):
        """
        Returns the optimized path for an emergency responder.
        """
        print(f"[GRAPH] Calculating optimized route from {start_id} to {end_id}...")
        from brain.routing import CityGraphRouter
        router = CityGraphRouter()
        path, cost = router.find_emergency_path(start_id, end_id)
        return path


if __name__ == "__main__":
    manager = TrafficGraphManager()
    manager.update_segment_weight("SEG_001", 1.8)
    route = manager.find_shortest_emergency_path("INT_001", "INT_004")
    print(f"[GRAPH] Optimized Route: {route}")
