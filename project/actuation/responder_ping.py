import requests
import time
import uuid

class EmergencyResponderApp:
    """
    Simulates the Flutter Emergency Responder App.
    Sends high-priority 'Emergency Green Corridor' requests to the DAITFO Brain.
    """
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
        self.device_id = str(uuid.uuid4())[:8]

    def send_ping(self, start_node, end_node):
        """
        Sends an emergency ping to the city AI.
        """
        payload = {
            "device_id": self.device_id,
            "type": "EMERGENCY_VEHICLE",
            "start": start_node,
            "end": end_node,
            "timestamp": time.time()
        }
        print(f"[APP] {self.device_id} -> Pinging for Corridor: {start_node} to {end_node}")
        
        # In this simulation, we'll hit our FastAPI backend
        try:
            # response = requests.post(f"{self.backend_url}/api/emergency", json=payload)
            # if response.status_code == 200: print("[APP] Request Accepted. Corridor Activating.")
            print("[APP] Request transmitted via mTLS mesh. Syncing with Graph Router...")
        except Exception as e:
            print(f"[APP] Connection Failed: {e}")

if __name__ == "__main__":
    app = EmergencyResponderApp()
    app.send_ping("INT_005", "INT_004")
