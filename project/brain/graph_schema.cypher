// DAITFO Neo4j Graph Schema Concept
// Model: Intersections as Nodes, Roads as Relationships

// 1. CLEAR EXISTING DATA (Optional)
MATCH (n) DETACH DELETE n;

// 2. CREATE NODES (Intersections)
CREATE (i1:Intersection {id: "INT_001", name: "Main St & Broadway", zones: ["ZONE_A"]})
CREATE (i2:Intersection {id: "INT_002", name: "Broadway & 2nd Ave", zones: ["ZONE_A"]})
CREATE (i3:Intersection {id: "INT_003", name: "Main St & 3rd Ave", zones: ["ZONE_B"]})
CREATE (i4:Intersection {id: "INT_004", name: "Park Ave & 5th St", zones: ["ZONE_C"]});

// 3. CREATE RELATIONSHIPS (Roads/Segments)
CREATE (i1)-[:CONNECTED_TO {distance: 500, lanes: 3, speed_limit: 40, weight: 1.0}]->(i2)
CREATE (i2)-[:CONNECTED_TO {distance: 500, lanes: 3, speed_limit: 40, weight: 1.0}]->(i1)
CREATE (i1)-[:CONNECTED_TO {distance: 800, lanes: 2, speed_limit: 30, weight: 1.0}]->(i3)
CREATE (i3)-[:CONNECTED_TO {distance: 800, lanes: 2, speed_limit: 30, weight: 1.0}]->(i1)
CREATE (i2)-[:CONNECTED_TO {distance: 1200, lanes: 4, speed_limit: 50, weight: 1.0}]->(i4)
CREATE (i4)-[:CONNECTED_TO {distance: 1200, lanes: 4, speed_limit: 50, weight: 1.0}]->(i2);

// 4. EMERGENCY ROUTING QUERY (Example)
// MATCH (start:Intersection {id: "INT_001"}), (end:Intersection {id: "INT_004"})
// CALL gds.shortestPath.dijkstra.stream({nodeProjection: 'Intersection', relationshipProjection: 'CONNECTED_TO', startNode: start, endNode: end, relationshipWeightProperty: 'weight'})
// YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
// RETURN path, totalCost;
