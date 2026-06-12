import xml.etree.ElementTree as ET
import torch

def extract_graph_from_sumo(net_file_path):
    """
    Parses a SUMO .net.xml file to build a graph representation of the road network.
    Nodes: Junctions (Intersections)
    Edges: Connections (Roads between junctions)
    
    Returns:
    - edge_index: torch.Tensor of shape (2, num_edges)
    - node_mappings: dict mapping string junction IDs to integer indexes
    """
    tree = ET.parse(net_file_path)
    root = tree.getroot()
    
    # 1. Identify all valid junctions (exclude internal junctions)
    junctions = []
    for junction in root.findall('junction'):
        j_type = junction.get('type')
        if j_type != 'internal':
            junctions.append(junction.get('id'))
            
    # Node to integer mapping for PyTorch Geometric
    node_to_idx = {j_id: idx for idx, j_id in enumerate(junctions)}
    idx_to_node = {idx: j_id for idx, j_id in enumerate(junctions)}
    
    # 2. Identify connections (edges)
    edges = []
    for edge in root.findall('edge'):
        # Only consider normal edges, not internal ones
        if 'function' not in edge.attrib or edge.get('function') != 'internal':
            from_node = edge.get('from')
            to_node = edge.get('to')
            
            # Ensure both nodes are in our tracked junctions
            if from_node in node_to_idx and to_node in node_to_idx:
                edges.append((node_to_idx[from_node], node_to_idx[to_node]))
                
    # 3. Format into edge_index for PyTorch Geometric
    if not edges:
        # Fallback if no valid edges found 
        return torch.empty((2, 0), dtype=torch.long), node_to_idx
        
    # Transpose list of tuples to shape [2, num_edges]
    edge_index_data = list(zip(*edges))
    edge_index = torch.tensor(edge_index_data, dtype=torch.long)
    
    return edge_index, node_to_idx
    
if __name__ == "__main__":
    print("SUMO Utils loaded. This will parse .net.xml files to construct graphs.")
