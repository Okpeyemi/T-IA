import osmnx as ox
import networkx as nx
import heapq
import sys
import os

# --- 1. Graph Data Loading ---

def load_graph(place_name="France métropolitaine", filename="france_graph.graphml"):
    """
    Loads the graph from a local file if it exists.
    Otherwise, downloads it from OpenStreetMap and saves it.
    """
    # Configure generic settings
    ox.settings.use_cache = True
    ox.settings.log_console = True
    ox.settings.requests_timeout = 600

    if os.path.exists(filename):
        print(f"Loading graph from local file: {filename}...")
        try:
            # Load from GraphML
            graph = ox.load_graphml(filename)
            
            # Ensure edge weights (length) and travel times are present/converted correctly
            # GraphML loads everything as string, but osmnx handles typing usually.
            # If not, we might need to cast 'length' to float. 
            # OSMnx load_graphml should handle standard attributes.
            
            print(f"Graph loaded with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
            return graph
        except Exception as e:
            print(f"Error loading graph from file: {e}")
            print("Falling back to download...")
    
    # If not found or error, download
    print(f"Downloading road graph for: {place_name}...")
    print("This may take 5-10 minutes. Please wait...")
    
    try:
        # "drive" network type gets drivable public streets
        graph = ox.graph_from_place(place_name, network_type='drive')
        
        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)
        
        print(f"Graph downloaded. Saving to {filename}...")
        ox.save_graphml(graph, filename)
        
        print(f"Graph loaded with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
        return graph
    except Exception as e:
        print(f"Error loading graph: {e}")
        return None

# --- 2. Bidirectional Dijkstra ---

def bidirectional_dijkstra(graph, start_node, end_node):
    """
    Performs Bidirectional Dijkstra on a NetworkX graph.
    Optimized for road networks (weights = 'length' in meters).
    """
    if start_node not in graph or end_node not in graph:
        return None, float('inf')
    
    if start_node == end_node:
        return [start_node], 0.0

    # Queues: (distance, node)
    q_f = [(0, start_node)]
    q_b = [(0, end_node)]
    
    # Distances
    dist_f = {start_node: 0}
    dist_b = {end_node: 0}
    
    # Parents
    parent_f = {start_node: None}
    parent_b = {end_node: None}
    
    # Visited
    visited_f = set()
    visited_b = set()
    
    mu = float('inf')
    meeting_node = None
    
    # For NetworkX, neighbors access:
    # G[u] returns a dict of neighbors.
    # edge data is in G[u][v]. Since it's MultiDiGraph, it might have key 0.
    # We want the shortest edge if multiple exist.
    
    while q_f and q_b:
        if q_f[0][0] + q_b[0][0] >= mu:
            break
            
        # --- Forward Step ---
        if q_f:
            d_u, u = heapq.heappop(q_f)
            
            if u not in visited_f:
                visited_f.add(u)
                
                # Iterate neighbors
                for v in graph.neighbors(u):
                    # Get edge weight (length in meters)
                    # Handle MultiDiGraph: get minimum length edge
                    edges = graph.get_edge_data(u, v)
                    # edges is a dict keyed by edge key (0, 1...) with attributes
                    weight = min(d.get('length', float('inf')) for d in edges.values())
                    
                    new_dist = d_u + weight
                    if new_dist < dist_f.get(v, float('inf')):
                        dist_f[v] = new_dist
                        parent_f[v] = u
                        heapq.heappush(q_f, (new_dist, v))
                        
                        if v in dist_b:
                            total_dist = new_dist + dist_b[v]
                            if total_dist < mu:
                                mu = total_dist
                                meeting_node = v

        # --- Backward Step ---
        if q_b:
            d_v, v = heapq.heappop(q_b)
            
            if v not in visited_b:
                visited_b.add(v)
                
                # Backwards search needs INCOMING edges (predecessors)
                # NetworkX DiGraph predecessors()
                for u in graph.predecessors(v):
                    # We are going u -> v in real life, so we look up edge u->v
                    edges = graph.get_edge_data(u, v)
                    weight = min(d.get('length', float('inf')) for d in edges.values())
                    
                    new_dist = d_v + weight
                    if new_dist < dist_b.get(u, float('inf')):
                        dist_b[u] = new_dist
                        parent_b[u] = v
                        heapq.heappush(q_b, (new_dist, u))
                        
                        if u in dist_f:
                            total_dist = dist_f[u] + new_dist
                            if total_dist < mu:
                                mu = total_dist
                                meeting_node = u

    return reconstruct_path(parent_f, parent_b, meeting_node, mu)

def reconstruct_path(parent_f, parent_b, meeting_node, total_dist):
    if meeting_node is None:
        return None, float('inf')
        
    # Forward path
    path_f = []
    curr = meeting_node
    while curr is not None:
        path_f.append(curr)
        curr = parent_f[curr]
    path_f.reverse()
    
    # Backward path
    path_b = []
    curr = parent_b[meeting_node]
    while curr is not None:
        path_b.append(curr)
        curr = parent_b[curr]
    
    full_path = path_f + path_b
    return full_path, total_dist

# --- 3. Main ---

if __name__ == "__main__":
    # Settings
    START_CITY = "Basilique Notre-Dame de Fourvière, France"
    END_CITY = "Vaux-sur-Vienne, France"
    
    # 1. Load Graph (Persistent)
    G = load_graph()
    if not G:
        sys.exit(1)
        
    print("Graph loaded successfully.")
    
    # 2. Geocode start/end to find nearest graph nodes
    print(f"Locating nearest nodes for {START_CITY} and {END_CITY}...")
    try:
        # get coordinates
        start_point = ox.geocode(START_CITY)
        end_point = ox.geocode(END_CITY)
        
        # nearest nodes (osmnx < 2.0 uses get_nearest_node, >= 2.0 uses distance.nearest_nodes)
        # Checking osmnx version behavior. recent versions use:
        start_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
        end_node = ox.distance.nearest_nodes(G, X=end_point[1], Y=end_point[0])
        
        print(f"Start Node: {start_node} (near {START_CITY})")
        print(f"End Node: {end_node} (near {END_CITY})")
        
    except Exception as e:
        print(f"Error geocoding or finding nodes: {e}")
        sys.exit(1)

    # 3. Run Algorithm
    print(f"\n--- Finding path from {START_CITY} to {END_CITY} ---")
    path_nodes, distance_meters = bidirectional_dijkstra(G, start_node, end_node)
    
    if path_nodes:
        print(f"\n🏆 Shortest Path Found!")
        print(f"Total Distance: {distance_meters/1000:.2f} km")
        print(f"Number of nodes in path: {len(path_nodes)}")
        
        # Optional: Print street names for first few and last few segments
        # to verify it makes sense
        print("Path details (Full turn-by-turn):")
        
        # Consolidate street names
        path_segments = []
        last_name = None
        
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i+1]
            data = G.get_edge_data(u, v)
            
            # Helper to get name from edge data
            # Edge data might have multiple keys (0, 1) for parallel edges
            # We take the one with min length usually, or just the first one if we didn't track the specific key
            # In our Dijkstra we used min length. Let's try to get the name associated with that.
            
            # Simple approach: get name from first key (sufficient for most cases)
            first_key = list(data.keys())[0]
            edge_attr = data[first_key]
            
            name = edge_attr.get('name', 'Unnamed Road')
            if isinstance(name, list):
                name = name[0] # Take first name if multiple
                
            length = edge_attr.get('length', 0)
            
            # If same name as last, add to length
            if name == last_name:
                path_segments[-1]['length'] += length
            else:
                path_segments.append({'name': name, 'length': length})
                last_name = name
                
        # Print Consolidated segments
        for idx, seg in enumerate(path_segments, 1):
            print(f"{idx}. {seg['name']} ({seg['length']:.0f} m)")
        
    else:
        print("No path found.")
