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
        import os
        payload = {
            "device_id": self.device_id,
            "start": start_node,
            "end": end_node,
        }
        headers = {
            "X-API-Key": os.getenv("ADMIN_API_KEY", os.getenv("DAITFO_API_KEY", "unsecured"))
        }
        print(f"[APP] {self.device_id} -> Pinging for Corridor: {start_node} to {end_node}")
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/emergency/request",
                json=payload,
                headers=headers
            )
            if response.status_code == 200:
                print(f"[APP] Request Accepted: {response.json().get('message')}")
            else:
                print(f"[APP] Server returned {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[APP] Connection Failed: {e}")


if __name__ == "__main__":
    app = EmergencyResponderApp()
    app.send_ping("INT_005", "INT_004")
