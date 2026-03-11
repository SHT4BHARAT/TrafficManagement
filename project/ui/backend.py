from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Set
import time
import json
import asyncio
import random

app = FastAPI(title="DAITFO Dashboard API")

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

# Background task to simulate live traffic stream
async def simulate_traffic_stream():
    while True:
        mock_data = {
            "intersection": "INT_001 (Main St & Broadway)",
            "queues": {
                "N": random.randint(0, 25),
                "S": random.randint(0, 25),
                "E": random.randint(0, 25),
                "W": random.randint(0, 25)
            },
            "reward": f"+{random.uniform(5, 20):.1f}",
            "mode": "AI Optimized",
            "uptime": "99.99%",
            "timestamp": time.time()
        }
        await manager.broadcast(mock_data)
        await asyncio.sleep(2)

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
            # Echo or process incoming commands if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class QueryRequest(BaseModel):
    query: str

@app.get("/api/metrics")
async def get_metrics():
    return {"status": "Use WebSocket for live stream"}

@app.post("/api/ask")
async def ask_assistant(request: QueryRequest):
    return {
        "answer": f"Simulated Assistant: I've processed your query '{request.query}'. System state is stable.",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
