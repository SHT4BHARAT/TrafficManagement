import sys
import os
from neo4j import GraphDatabase

# Project root for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import DBConfig

def seed_graph():
    uri = DBConfig.NEO4J_URI
    user = DBConfig.NEO4J_USER
    password = DBConfig.NEO4J_PASS

    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        print("[SEED] Clearing existing graph data...")
        session.run("MATCH (n) DETACH DELETE n")

        print("[SEED] Creating 20 Intersections (Mini-City Grid)...")
        # 5x4 Grid Layout
        nodes = []
        for row in range(4):
            for col in range(5):
                idx = row * 5 + col + 1
                node_id = f"INT_{idx:03d}"
                x = 100 + col * 200
                y = 100 + row * 200
                nodes.append({"id": node_id, "x": x, "y": y})
                session.run(
                    "CREATE (n:Intersection {id: $id, name: $name, x: $x, y: $y})",
                    id=node_id, name=f"Intersection {node_id}", x=x, y=y
                )

        print("[SEED] Creating Road Segments (Grid Edges)...")
        # Horizontal Connections
        for row in range(4):
            for col in range(4):
                u = f"INT_{(row * 5 + col + 1):03d}"
                v = f"INT_{(row * 5 + col + 2):03d}"
                session.run(
                    "MATCH (a:Intersection {id: $u}), (b:Intersection {id: $v}) "
                    "CREATE (a)-[:CONNECTS {distance: 200, weight: 1.0, current_vpm: 0}]->(b), "
                    "       (b)-[:CONNECTS {distance: 200, weight: 1.0, current_vpm: 0}]->(a)",
                    u=u, v=v
                )
        
        # Vertical Connections
        for row in range(3):
            for col in range(5):
                u = f"INT_{(row * 5 + col + 1):03d}"
                v = f"INT_{((row + 1) * 5 + col + 1):03d}"
                session.run(
                    "MATCH (a:Intersection {id: $u}), (b:Intersection {id: $v}) "
                    "CREATE (a)-[:CONNECTS {distance: 200, weight: 1.0, current_vpm: 0}]->(b), "
                    "       (b)-[:CONNECTS {distance: 200, weight: 1.0, current_vpm: 0}]->(a)",
                    u=u, v=v
                )
        
        # Add a few Diagonal "Expressways" for mini-city feel
        diagonals = [("INT_001", "INT_007"), ("INT_005", "INT_009"), ("INT_011", "INT_017")]
        for u, v in diagonals:
             session.run(
                "MATCH (a:Intersection {id: $u}), (b:Intersection {id: $v}) "
                "CREATE (a)-[:CONNECTS {distance: 280, weight: 0.8, current_vpm: 0}]->(b), "
                "       (b)-[:CONNECTS {distance: 280, weight: 0.8, current_vpm: 0}]->(a)",
                u=u, v=v
            )

    driver.close()
    print("✅ [SEED] Mini-City Graph (20 Nodes) Seeded successfully.")

if __name__ == "__main__":
    seed_graph()
