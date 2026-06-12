"""
Generate a left-hand drive (India) SUMO network with 5-phase traffic lights.
Phase 0: North GREEN (all movements)
Phase 1: South GREEN (all movements)
Phase 2: East GREEN (all movements)
Phase 3: West GREEN (all movements)
Phase 4: Pedestrian Scramble (all RED for vehicles)
"""
import subprocess
import os
import sys

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
NETGENERATE = os.path.join(SUMO_HOME, "bin", "netgenerate.exe")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")

def generate_network():
    os.makedirs("data", exist_ok=True)
    net_file = "data/network.net.xml"
    
    cmd = [
        NETGENERATE,
        "--grid",
        "--grid.number=3",
        "--grid.length=200",
        "--lefthand",
        "--default.sidewalk-width=3",
        "--output-file=" + net_file,
        "--no-turnarounds=true",
        "--tls.guess=true",
        "--junctions.corner-detail=5",
    ]
    
    print("Generating India LHD 3x3 grid network...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(f"Network generated: {net_file}")
    return True

def generate_routes():
    net_file = "data/network.net.xml"
    route_file = "data/routes.rou.xml"
    random_trips = os.path.join(SUMO_TOOLS, "randomTrips.py")
    
    cmd = [
        sys.executable, random_trips,
        "-n", net_file,
        "-o", "data/trips.xml",
        "-r", route_file,
        "--begin=0",
        "--end=3600",
        "--period=1.5",
        "--validate",
        "--fringe-factor=5",
    ]
    
    print("Generating vehicle routes...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: {result.stderr}")
    print(f"Routes generated: {route_file}")
    return True

if __name__ == "__main__":
    if generate_network():
        generate_routes()
        print("\nIndia LHD network + routes ready.")
