import time
import json
import asyncio
import random
import threading
import os
from collections import deque
from typing import Dict, List, Optional, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import verify_api_key, verify_admin_key, API_KEY_NAME
from core.logging_config import setup_logging
from brain.llm_assistant import HQAssistantLLM
from brain.slm_node import SLMBridgeNode
from core.optimization import SCOOTController
from core.utils import safe_json_parse, extract_json_from_text, detect_emergency_zone
from core.db_client import RedisClient

logger = setup_logging()

# --- Rate Limiter ---
from slowapi import Limiter as _Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = _Limiter(key_func=get_remote_address)

# --- Pydantic Models ---

class ControllerConfigRequest(BaseModel):
    mode: Optional[Literal["manual", "auto", "rr"]] = None
    vps: Optional[Dict[Literal["N", "S", "E", "W"], int]] = None
    duration: Optional[int] = Field(default=None, ge=5, le=120)

class PhaseSelectRequest(BaseModel):
    phase: Literal["N", "S", "E", "W", "NS", "N-S", "EW", "E-W"]

class EmergencyRequest(BaseModel):
    device_id: str = Field(default="UNK_RES", max_length=64)
    start: str = Field(default="INT_005", max_length=64)
    end: str = Field(default="INT_001", max_length=64)

class InferenceRequest(BaseModel):
    phase: str = Field(..., max_length=16)
    vps: Dict[Literal["N", "S", "E", "W"], int]

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=1000)

# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(stream_redis_state())
    yield

app = FastAPI(title="DAITFO Dashboard API", version="3.0.0", lifespan=lifespan)
app.state.limiter = limiter


def _rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": {"code": "RATE_LIMITED", "detail": "Too many requests. Please slow down.", "status": 429}},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=[API_KEY_NAME, "Content-Type"],
)

app.add_middleware(SlowAPIMiddleware)

# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_ERROR", "detail": "An internal error occurred", "status": 500}},
    )

# --- Init Components ---

assistant = HQAssistantLLM()
scoot = None
try:
    scoot = SCOOTController()
except Exception as e:
    logger.warning(f"SCOOTController initialization failed: {e}")
    scoot = None

slm_bridge = SLMBridgeNode()
redis_client = RedisClient()

# --- Connection Manager (WebSocket) ---

MAX_WS_CONNECTIONS = 100
WS_MAX_MESSAGE_SIZE = 1024
ALLOWED_WS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            await websocket.close(code=1013, reason="Too many connections")
            return False
        origin = websocket.headers.get("origin", "")
        if origin and origin not in ALLOWED_WS_ORIGINS:
            await websocket.close(code=1008, reason="Origin not allowed")
            return False
        api_key = websocket.headers.get(API_KEY_NAME, "") or websocket.query_params.get("api_key", "")
        if not api_key:
            await websocket.close(code=1008, reason="Missing authentication")
            return False
        try:
            verify_api_key(api_key)
        except HTTPException:
            await websocket.close(code=1008, reason="Invalid API key")
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS client connected. Total: {len(self.active_connections)}")
        with broadcast_lock:
            if last_broadcast is not None:
                try:
                    await websocket.send_json(last_broadcast.copy())
                except Exception:
                    pass
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WS client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.remove(d)

manager = ConnectionManager()

# --- Global State ---

last_broadcast: dict | None = None
broadcast_lock = threading.Lock()
intersection_timings = {"N": 35, "S": 35, "E": 35, "W": 35}
pending_duration: int | None = None
pending_duration_lock = threading.Lock()
ai_recommended_duration = 35
ai_reasoning = "Awaiting first inference..."
cycle_start_time = time.time()
emergency_mode = False
emergency_zone = None
current_phase_index = 0
current_phase_duration = 35
event_log = deque(maxlen=1000)

lane_stats = {
    l: {"queue": 0.0, "red_time": 0.0, "vpm": random.randint(5, 15)}
    for l in ["N", "S", "E", "W"]
}
controller_mode = "manual"
manual_vps = {"N": 14, "S": 11, "E": 6, "W": 22}
AUTO_PHASE_DURATION = 15
auto_phase_lanes = ["N", "S", "E", "W"]
auto_phase_slot = 0

# --- Live Data Bridge ---

async def stream_redis_state():
    global last_broadcast
    loop = asyncio.get_event_loop()
    while True:
        try:
            state = await loop.run_in_executor(None, redis_client.get_live_state, "INT_001")
            if state:
                mock_data = {
                    "intersection": "INT_001 \u00b7 MAIN ST & BROADWAY",
                    "queues":      {l: int(state.get(f"queue_{l}", 0)) for l in ["N", "S", "E", "W"]},
                    "vpm":         {l: int(state.get(f"vpm_{l}", 0))   for l in ["N", "S", "E", "W"]},
                    "red_times":   {l: int(state.get(f"red_{l}", 0))   for l in ["N", "S", "E", "W"]},
                    "timings":     {l: int(state.get(f"timing_{l}", 35)) for l in ["N", "S", "E", "W"]},
                    "green_lights": state.get("green_lights", "NS").split("-"),
                    "cycle_countdown": int(state.get("cycle_countdown", 0)),
                    "ai_duration": int(state.get("ai_duration", 35)),
                    "ai_reasoning": state.get("ai_reasoning", "Optimizing via RLlib..."),
                    "emergency": {
                        "active": state.get("emergency_active", "False") == "True",
                        "zone":   state.get("emergency_zone", None)
                    },
                    "reward":    f"+{state.get('reward', '0.0')}",
                    "avg_wait":  f"{state.get('avg_wait', '0.0')}s",
                    "uptime":    "99.99%",
                    "pi":        float(state.get("pi", 0.0)),
                    "events":    list(event_log),
                    "timestamp": time.time()
                }
                with broadcast_lock:
                    last_broadcast = mock_data.copy()
                await manager.broadcast(mock_data)
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"Redis streamer error: {e}")
            await asyncio.sleep(2)

# --- Routes ---

@app.get("/")
async def root():
    return {"status": "DAITFO Backend Online", "version": "3.0.0", "websocket_path": "/ws"}

@app.get("/health")
async def health():
    statuses = {"api": "ok"}
    try:
        redis_client.client.ping()
        statuses["redis"] = "ok"
    except Exception:
        statuses["redis"] = "degraded"
    try:
        r = __import__("requests").get(f"{assistant.base_url}/api/tags", timeout=2)
        statuses["ollama"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        statuses["ollama"] = "degraded"
    all_ok = all(v == "ok" for v in statuses.values())
    return JSONResponse(
        content={"status": "ok" if all_ok else "degraded", "checks": statuses},
        status_code=200 if all_ok else 503,
    )

@app.get("/city-3d")
async def serve_city_3d():
    html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daitfo_city_3d.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="daitfo_city_3d.html not found")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    accepted = await manager.connect(websocket)
    if not accepted:
        return
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) > WS_MAX_MESSAGE_SIZE:
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/controller-config")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "30/minute"))
async def controller_config(request: Request, config: ControllerConfigRequest, api_key: str = Depends(verify_admin_key)):

    global controller_mode, manual_vps, current_phase_duration
    if config.mode is not None:
        controller_mode = config.mode
    if config.vps is not None:
        for k in ["N", "S", "E", "W"]:
            if k in config.vps:
                manual_vps[k] = max(2, min(40, config.vps[k]))
    if config.duration is not None:
        current_phase_duration = config.duration
        redis_client.update_live_state("INT_001", {"config_duration": current_phase_duration})
    return {"status": "ok", "mode": controller_mode, "vps": manual_vps, "duration": current_phase_duration}


@app.post("/api/select-phase")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "30/minute"))
async def select_phase(request: Request, body: PhaseSelectRequest, api_key: str = Depends(verify_admin_key)):

    global current_phase_index, cycle_start_time
    target = body.phase.strip().upper().replace("-", "")

    phases = [["N"], ["S"], ["E"], ["W"], ["N", "S"], ["E", "W"]]
    if target in ("N", "S", "E", "W"):
        target_index = ["N", "S", "E", "W"].index(target)
    elif target == "NS":
        target_index = 4
    elif target == "EW":
        target_index = 5
    else:
        raise HTTPException(status_code=400, detail="phase must be N, S, E, W, NS, or EW")
    current_phase_index = target_index
    cycle_start_time = time.time()
    label = "-".join(phases[current_phase_index])
    redis_client.update_live_state("INT_001", {"phase_override": label, "cycle_reset": "True"})
    logger.info(f"Manual phase override: {label}")
    return {"status": "Phase updated", "active_phase": label}

@app.post("/api/emergency/request")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "5/minute"))
async def emergency_request(request: Request, body: EmergencyRequest, api_key: str = Depends(verify_admin_key)):

    global emergency_mode, emergency_zone
    redis_client.update_live_state("INT_001", {
        "emergency_active": "True", "emergency_start": body.start,
        "emergency_end": body.end, "emergency_device": body.device_id
    })
    emergency_mode = True
    emergency_zone = body.start
    logger.info(f"Emergency request from {body.device_id}: {body.start} -> {body.end}")
    return {"status": "success", "message": "Green Corridor Activated", "corridor": f"{body.start} to {body.end}"}


@app.post("/api/emergency/clear")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "10/minute"))
async def emergency_clear(request: Request, api_key: str = Depends(verify_admin_key)):
    global emergency_mode, emergency_zone
    redis_client.update_live_state("INT_001", {"emergency_active": "False"})
    emergency_mode = False
    emergency_zone = None
    return {"status": "success", "message": "Emergency cleared"}

@app.post("/api/ai-inference")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "10/minute"))
async def ai_inference(request: Request, body: InferenceRequest, api_key: str = Depends(verify_api_key)):

    global ai_recommended_duration, ai_reasoning, pending_duration
    live_state = {
        "phase": body.phase,
        "vps": body.vps,
        "queues": {l: int(lane_stats[l]["queue"]) for l in lane_stats},
    }

    prompt = ("[TRAFFIC CONTROL ACTION B] Determine optimal green duration (10-60 seconds)"
              " for the current phase and traffic. Return JSON only with keys: duration (integer 10-60), reasoning (string).")
    final_duration = 35
    final_reasoning = "Static density analysis suggests standard duration."
    try:
        loop = asyncio.get_event_loop()
        raw_response = await loop.run_in_executor(None, assistant.query_system, prompt, live_state)
        data = extract_json_from_text(raw_response, None)
        if isinstance(data, dict):
            duration_val = data.get("duration", 35)
            if isinstance(duration_val, (int, float)):
                final_duration = max(10, min(60, int(duration_val)))
            final_reasoning = str(data.get("reasoning", data.get("reason", final_reasoning)))
        else:
            final_reasoning = "SLM returned unstructured data. Using fallback duration."
    except Exception as e:
        logger.error(f"Inference error: {e}")
        final_reasoning = f"Model busy or unreachable. Fallback: {final_reasoning}"
    ai_recommended_duration = final_duration
    ai_reasoning = final_reasoning
    with pending_duration_lock:
        pending_duration = final_duration
    return {"duration": final_duration, "reasoning": final_reasoning, "timestamp": time.time(), "status": "success"}

@app.get("/api/metrics")
async def get_metrics():
    return {"status": "Use WebSocket for live stream"}

def _check_ollama():
    import requests
    r = requests.get(f"{assistant.base_url}/api/tags", timeout=2)
    if r.status_code != 200:
        return {"ok": False, "error": f"Ollama returned HTTP {r.status_code}"}
    data = r.json()
    models = [m.get("name", "") for m in data.get("models", [])]
    model_ok = any(assistant.model_name in n for n in models)
    return {
        "ok": True, "ollama": "reachable", "model": assistant.model_name,
        "model_available": model_ok,
        "message": "SLM ready" if model_ok else f"Model '{assistant.model_name}' not found in Ollama."
    }

@app.get("/api/slm-analyze")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "20/minute"))
async def slm_analyze(request: Request, zone: str = Query(default="INT_001", max_length=64), api_key: str = Depends(verify_api_key)):
    try:
        state = {"queues": manual_vps, "emergency": {"active": emergency_mode, "zone": emergency_zone}}
        loop = asyncio.get_event_loop()
        reasoning = await loop.run_in_executor(None, slm_bridge.get_reasoning, zone, state)
        return {"status": "success", "data": reasoning}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/slm-status")
async def slm_status(api_key: str = Depends(verify_api_key)):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _check_ollama)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e), "message": "Ollama not running or unreachable."}

@app.post("/api/ask")
@limiter.limit(os.getenv("SLOWAPI_RATE_LIMIT", "5/minute"))
async def ask_assistant(request: Request, body: QueryRequest, api_key: str = Depends(verify_api_key)):

    global emergency_mode, emergency_zone
    query = body.query.strip()

    mock_live_state = {l: int(lane_stats[l]["queue"]) for l in lane_stats}
    detected_zone = detect_emergency_zone(query)
    low_query = query.lower()
    if "ambulance" in low_query or "emergency" in low_query:
        emergency_mode = True
        emergency_zone = detected_zone
        logger.info(f"Emergency forced for zone {emergency_zone}")
        response = (f"\U0001f6a8 EMERGENCY OVERRIDE ACTIVATED. Enforcing Green Corridor for Zone {emergency_zone}. "
                     "All intersecting traffic is being held.")
    elif "clear emergency" in low_query or "reset" in low_query:
        emergency_mode = False
        emergency_zone = None
        response = "Emergency cleared. System returning to standard AI optimized cycles."
    else:
        try:
            rl_state = assistant.query_rl_state("INT_001")
            live_context = rl_state if rl_state else mock_live_state
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, assistant.query_system, query, live_context)
        except Exception as e:
            logger.error(f"LLM assistant error: {e}")
            response = "Assistant temporarily unavailable. Please try again later."

    payload = {"timestamp": time.time(), "status": "EMERGENCY_ACTIVE" if emergency_mode else "Operational"}
    try:
        parsed = safe_json_parse(response, None)
        if isinstance(parsed, dict):
            if parsed.get("status") == "error":
                payload["answer"] = f"Assistant error: {parsed.get('answer', 'Unknown error')}"
                payload["status"] = "error"
            else:
                payload = {**parsed, **payload}
        else:
            payload["answer"] = str(response)
    except (json.JSONDecodeError, TypeError):
        payload["answer"] = str(response)
    return payload

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
