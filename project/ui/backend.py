from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import time

app = FastAPI(title="DAITFO Dashboard API")

# In-memory storage for demonstration
# In production, this would be Redis/TimescaleDB
live_metrics = {
    "INT_001": {
        "status": "Active",
        "current_phase": "N-S Green",
        "queues": {"N": 0, "S": 0, "E": 0, "W": 0},
        "efficiency_reward": 0,
        "uptime": "99.9%"
    }
}

class QueryRequest(BaseModel):
    query: str

@app.get("/api/metrics")
async def get_metrics():
    """Returns live metrics for all intersections."""
    return live_metrics

@app.post("/api/ask")
async def ask_assistant(request: QueryRequest):
    """Endpoint for the HQ Assistant LLM chat."""
    # This would link to project.brain.llm_assistant
    return {
        "answer": f"Backend received: {request.query}. The system is optimizing INT_001.",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
