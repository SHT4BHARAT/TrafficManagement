from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Set
import time
import json
import asyncio
import random

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.middleware.cors import CORSMiddleware
from brain.llm_assistant import HQAssistantLLM

app = FastAPI(title="DAITFO Dashboard API")

# Add CORS Middleware to allow dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = HQAssistantLLM()

@app.get("/")
async def root():
    return {"status": "DAITFO Backend Online", "version": "2.2", "websocket_path": "/ws"}

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] New Client Connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"[WS] Client Disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Global state for signal timings
intersection_timings = {"N": 15, "S": 15, "E": 15, "W": 15}
pending_timings = None
cycle_start_time = time.time()
emergency_mode = False
emergency_zone = None
current_phase_index = 0
current_phase_duration = 15

# Background task to simulate live traffic stream
async def simulate_traffic_stream():
    global intersection_timings, pending_timings, cycle_start_time, emergency_mode, emergency_zone
    global current_phase_index, current_phase_duration
    
    lanes = ["N", "S", "E", "W"]
    
    while True:
        current_time = time.time()
        elapsed = current_time - cycle_start_time
        
        # 1. Generate fresh mock data for density (Simulating Edge detection)
        mock_queues = {
            "N": random.randint(0, 5) if (emergency_mode and emergency_zone == "N") else random.randint(2, 25),
            "S": random.randint(0, 5) if (emergency_mode and emergency_zone == "S") else random.randint(2, 25),
            "E": random.randint(0, 5) if (emergency_mode and emergency_zone == "E") else random.randint(2, 25),
            "W": random.randint(0, 5) if (emergency_mode and emergency_zone == "W") else random.randint(2, 25)
        }

        # 2. EMERGENCY OVERRIDE (Green Corridor)
        if emergency_mode and emergency_zone:
            current_lane = emergency_zone
            current_phase_duration = 99
            # Stay in this phase as long as emergency is active
        else:
            # 3. SEQUENTIAL ROTATION LOGIC
            current_lane = lanes[current_phase_index]
            
            # Calculate dynamic duration for current lane based on density
            # Base 10s + 2s per vehicle (capped at 60s max, 10s min)
            density = mock_queues[current_lane]
            current_phase_duration = max(10, min(60, 10 + (density * 1.5)))
            
            if elapsed >= current_phase_duration:
                # Rotate to next lane
                current_phase_index = (current_phase_index + 1) % 4
                cycle_start_time = current_time
                elapsed = 0
                current_lane = lanes[current_phase_index]
                print(f"[LOGIC] Phase Rotation: Moving to ZONE {current_lane}")

        # Update timings for dashboard display
        intersection_timings = {l: (99 if (emergency_mode and l == emergency_zone) else int(current_phase_duration if l == current_lane else 10)) for l in lanes}
        
        green_lanes = [current_lane]

        mock_data = {
            "intersection": "INT_001 (Main St & Broadway)",
            "queues": mock_queues,
            "timings": intersection_timings,
            "green_lights": green_lanes,
            "pending_timings": pending_timings,
            "cycle_countdown": max(0, int(current_phase_duration - elapsed)),
            "emergency": {"active": emergency_mode, "zone": emergency_zone},
            "reward": "EMERGENCY_MODE" if emergency_mode else f"+{random.uniform(5, 20):.1f}",
            "mode": "GREEN CORRIDOR ACTIVE" if emergency_mode else "DYNAMIC_SEQUENTIAL",
            "uptime": "99.99%",
            "timestamp": current_time
        }
        await manager.broadcast(mock_data)
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_traffic_stream())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class QueryRequest(BaseModel):
    query: str

@app.get("/api/metrics")
async def get_metrics():
    return {"status": "Use WebSocket for live stream"}

@app.post("/api/ask")
def ask_assistant(request: QueryRequest):
    # Simulated live state from the "Hot Store"
    mock_live_state = {"N": 12, "S": 8, "E": 24, "W": 15}
    
    # This is a blocking call (requests + scraper), so we run it in a thread
    response = assistant.query_system(request.query, live_state=mock_live_state)
    
    global pending_timings, emergency_mode, emergency_zone
    
    # EMERGENCY TRIGGER: 
    # If the user mentions ambulance or emergency, we force a Green Corridor
    low_query = request.query.lower()
    if "ambulance" in low_query or "emergency" in low_query:
        emergency_mode = True
        emergency_zone = "E" # Simulate ambulance coming from East
        print("[EMERGENCY] Emergency signal detected. Forcing Green Corridor ON.")
        response = "🚨 EMERGENCY OVERRIDE ACTIVATED. Enforcing Green Corridor for Zone E. All intersecting traffic is being held. Pathfinding prioritized for life-saving transit."
    
    elif "clear emergency" in low_query or "reset" in low_query:
        emergency_mode = False
        emergency_zone = None
        print("[EMERGENCY] Emergency cleared. Returning to standard AI optimization.")
        response = "Emergency cleared. System is returning to standard AI optimized cycles."

    # CLOSED-LOOP ACTUATION: 
    # Store recommended timings as "Pending" until current 60s cycle ends (only if NOT in emergency)
    elif "recommend" in response.lower() or "optimize" in response.lower():
        pending_timings = {
            "E": 60, "W": 60,
            "N": 30, "S": 30
        }
        print("[QUEUED] AI Optimized timings queued for next cycle.")

    return {
        "answer": response,
        "timestamp": time.time(),
        "applied_actuation": True,
        "status": "EMERGENCY_ACTIVE" if emergency_mode else ("Queued" if pending_timings else "Operational")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
