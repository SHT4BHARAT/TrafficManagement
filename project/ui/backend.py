from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, List
import time
import json
import asyncio
import random
import re
import threading
from collections import deque

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.middleware.cors import CORSMiddleware
from brain.llm_assistant import HQAssistantLLM
from core.optimization import SCOOTController
from core.utils import safe_json_parse, extract_json_from_text, detect_emergency_zone

logger = logging.getLogger(__name__)

app = FastAPI(title="DAITFO Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = HQAssistantLLM()

# Initialize SCOOT controller with error handling
scoot = None
try:
    scoot = SCOOTController()
except Exception as e:
    logger.warning(f"[BACKEND] SCOOTController initialization failed: {e}. Using fallback mode.")
    scoot = None

@app.get("/")
async def root():
    return {"status": "DAITFO Backend Online", "version": "2.3", "websocket_path": "/ws"}

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] New Client Connected. Total: {len(self.active_connections)}")
        # Send latest snapshot immediately so dashboard shows data without waiting for next tick
        with broadcast_lock:
            if last_broadcast is not None:
                try:
                    await websocket.send_json(last_broadcast.copy())
                except Exception:
                    pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Client Disconnected. Remaining: {len(self.active_connections)}")

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
# Last payload sent to WS clients; used to send immediate snapshot on new connect (dashboard expects: queues, vpm, red_times, green_lights, cycle_countdown)
last_broadcast: dict | None = None
broadcast_lock = threading.Lock()
intersection_timings = {"N": 35, "S": 35, "E": 35, "W": 35}

# FIX Bug 3: pending_duration with thread-safe access via lock
pending_duration: int | None = None
pending_duration_lock = threading.Lock()

ai_recommended_duration = 35
ai_reasoning = "Awaiting first inference..."
cycle_start_time = time.time()
emergency_mode = False
emergency_zone = None
current_phase_index = 0
current_phase_duration = 35
# FIX Bug 7: Use circular buffer to prevent unbounded growth and maintain history
event_log = deque(maxlen=1000)  # Keep last 1000 events with automatic pruning

lane_stats = {
    l: {"queue": 0.0, "red_time": 0.0, "vpm": random.randint(5, 15)}
    for l in ["N", "S", "E", "W"]
}
# Traffic controller mode: "manual" = use dashboard VPS; "auto" = random 2–40 vpm per lane
controller_mode = "manual"
manual_vps = {"N": 14, "S": 11, "E": 6, "W": 22}

# Auto mode: round-robin through all 4 single-lane phases, 15s each
AUTO_PHASE_DURATION = 15          # seconds per lane in auto mode
auto_phase_lanes = ["N", "S", "E", "W"]
auto_phase_slot = 0               # which lane is currently active in auto round-robin

# --- Background Traffic Loop ---
async def simulate_traffic_stream():
    global intersection_timings, cycle_start_time, emergency_mode, emergency_zone
    global current_phase_index, current_phase_duration, ai_recommended_duration, ai_reasoning
    global lane_stats, pending_duration, pending_duration_lock, controller_mode, manual_vps
    global auto_phase_slot

    # Phases: single (N,S,E,W) or pair (N-S, E-W)
    phases = [["N"], ["S"], ["E"], ["W"], ["N", "S"], ["E", "W"]]
    phase_order = ["N", "S", "E", "W"]
    num_phases = len(phases)

    while True:
        try:
            current_time = time.time()

            # Emergency override: force single direction
            if emergency_mode and emergency_zone:
                target_phase_idx = phase_order.index(emergency_zone) if emergency_zone in phase_order else 0
                if current_phase_index != target_phase_idx:
                    current_phase_index = target_phase_idx
                    cycle_start_time = current_time
                    event_log.append({"type": "error", "msg": f"EMERGENCY OVERRIDE: Priority Path {emergency_zone} active."})

            elapsed = current_time - cycle_start_time
            current_green_pair = phases[current_phase_index]

            # --- AUTO MODE: round-robin each single lane for AUTO_PHASE_DURATION seconds ---
            if controller_mode == "auto":
                if elapsed >= AUTO_PHASE_DURATION:
                    auto_phase_slot = (auto_phase_slot + 1) % 4
                    current_phase_index = auto_phase_slot  # indices 0-3 = N,S,E,W single lanes
                    cycle_start_time = current_time
                    elapsed = 0
                    current_green_pair = phases[current_phase_index]
                    current_phase_duration = AUTO_PHASE_DURATION
                    label = auto_phase_lanes[auto_phase_slot]
                    event_log.append({"type": "auto", "msg": f"AUTO: Lane {label} green for {AUTO_PHASE_DURATION}s."})
                    print(f"[AUTO] Round-robin → Lane {label} for {AUTO_PHASE_DURATION}s")
                else:
                    current_phase_duration = AUTO_PHASE_DURATION

            # --- MANUAL MODE: SCOOT/AI-driven phase rotation ---
            elif elapsed >= current_phase_duration and not emergency_mode:
                current_phase_index = (current_phase_index + 1) % num_phases                cycle_start_time = current_time
                elapsed = 0
                current_green_pair = phases[current_phase_index]
                new_phase_id = "NS" if set(current_green_pair) <= {"N", "S"} else "EW"

                sensor_snapshot = {
                    "queues": {l: int(lane_stats[l]["queue"]) for l in lane_stats},
                    "vpm": {l: lane_stats[l]["vpm"] for l in lane_stats}
                }
                
                # Use SCOOT if available, otherwise use default
                if scoot is not None:
                    new_opt_duration = scoot.optimize_splits(new_phase_id, sensor_snapshot)
                else:
                    new_opt_duration = 35
                
                # FIX Bug 3: Thread-safe pending_duration access
                with pending_duration_lock:
                    if pending_duration is not None:
                        current_phase_duration = max(10, min(60, pending_duration))
                        event_log.append({"type": "ai-b", "msg": f"AI queued duration applied: {current_phase_duration}s"})
                        pending_duration = None
                    else:
                        current_phase_duration = new_opt_duration
                        if scoot is not None:
                            event_log.append({"type": "ai-b", "msg": f"SCOOT optimized {new_phase_id} to {new_opt_duration}s (PI: {scoot.performance_index:.2f})"})
                        else:
                            event_log.append({"type": "ai-b", "msg": f"Using default duration {new_opt_duration}s (SCOOT unavailable)"})

                label = "+".join(current_green_pair)
                event_log.append({"type": "auto", "msg": f"Phase rotated to {label} for {current_phase_duration}s."})
                print(f"[LOGIC] Phase → {label} for {current_phase_duration}s")

            # Dynamic queue simulation per lane
            for lane in ["N", "S", "E", "W"]:
                stats = lane_stats[lane]
                is_green = lane in current_green_pair

                if controller_mode == "auto":
                    stats["vpm"] = random.randint(2, 40)
                else:
                    stats["vpm"] = max(2, min(40, manual_vps.get(lane, stats["vpm"])))
                arrival_step = stats["vpm"] / 120.0
                stats["queue"] += arrival_step

                if is_green:
                    clearing_step = random.uniform(0.8, 1.2)
                    stats["queue"] = max(0.0, stats["queue"] - clearing_step)
                    # FIX Bug 6: reset red_time when lane goes green
                    stats["red_time"] = 0.0
                else:
                    stats["red_time"] += 0.5

            intersection_timings = {
                l: int(current_phase_duration if l in current_green_pair else 10)
                for l in ["N", "S", "E", "W"]
            }

            # avg_wait: only average the RED (waiting) lanes for a meaningful signal
            # FIX Bug 2: Use max(1, len(red_lanes)) to prevent division by zero
            red_lanes = [l for l in ["N", "S", "E", "W"] if l not in current_green_pair]
            avg_wait_val = (
                sum(lane_stats[l]["red_time"] for l in red_lanes) / max(1, len(red_lanes))
            )

            mock_data = {
                "intersection": "INT_001 · MAIN ST & BROADWAY",
                "queues": {l: int(lane_stats[l]["queue"]) for l in lane_stats},
                "vpm": {l: lane_stats[l]["vpm"] for l in lane_stats},
                "red_times": {l: int(lane_stats[l]["red_time"]) for l in lane_stats},
                "timings": intersection_timings,
                "green_lights": current_green_pair,
                "cycle_countdown": max(0, int(current_phase_duration - elapsed)),
                "ai_duration": ai_recommended_duration,
                "ai_reasoning": ai_reasoning,
                "emergency": {"active": emergency_mode, "zone": emergency_zone},
                "reward": f"+{8.5 + random.uniform(0, 1):.1f}",
                "avg_wait": f"{avg_wait_val:.1f}s",
                "uptime": "99.99%",
                "pi": round(scoot.performance_index, 2) if scoot is not None else 0.0,
                "events": list(event_log),
                "timestamp": current_time
            }
            
            # Thread-safe update of last_broadcast
            global last_broadcast
            with broadcast_lock:
                last_broadcast = mock_data.copy()
            
            await manager.broadcast(mock_data)
            await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"[ERROR] Traffic simulation loop: {e}")
            # Continue the loop even if there's an error
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_traffic_stream())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


class InferenceRequest(BaseModel):
    phase: str
    vps: Dict[str, int]


@app.post("/api/controller-config")
async def controller_config(request: Dict):
    """Set traffic controller mode (manual/auto) and optional VPS for manual mode."""
    try:
        global controller_mode, manual_vps
        
        if not isinstance(request, dict):
            return {"status": "error", "message": "Request must be a JSON object"}
            
        mode = request.get("mode", controller_mode)
        if mode not in ("manual", "auto"):
            return {"status": "error", "message": "mode must be 'manual' or 'auto'"}
            
        controller_mode = mode
        vps = request.get("vps")
        
        if vps is not None:
            if not isinstance(vps, dict):
                return {"status": "error", "message": "vps must be a dictionary"}
            for k in ["N", "S", "E", "W"]:
                if k in vps:
                    if not isinstance(vps[k], (int, float)):
                        return {"status": "error", "message": f"vps[{k}] must be a number"}
                    manual_vps[k] = max(2, min(40, int(vps[k])))
                    
        return {"status": "ok", "mode": controller_mode, "vps": manual_vps}
    except Exception as e:
        return {"status": "error", "message": f"Internal server error: {str(e)}"}


@app.post("/api/select-phase")
async def select_phase(request: Dict[str, str]):
    """Select phase: N, S, E, W (single green) or NS/N-S, EW/E-W (pair green)."""
    try:
        global current_phase_index, cycle_start_time
        
        if not isinstance(request, dict):
            return {"status": "error", "message": "Request must be a JSON object"}
            
        phase = request.get("phase")
        if not phase or not isinstance(phase, str):
            return {"status": "error", "message": "phase parameter is required and must be a string"}
            
        target = phase.strip().upper().replace("-", "")
        phases = [["N"], ["S"], ["E"], ["W"], ["N", "S"], ["E", "W"]]
        
        # FIX Bug 9: Validate before assignment instead of after
        target_index = None
        if target in ("N", "S", "E", "W"):
            target_index = ["N", "S", "E", "W"].index(target)
        elif target == "NS":
            target_index = 4
        elif target == "EW":
            target_index = 5
        else:
            return {"status": "error", "message": "phase must be N, S, E, W, NS, or EW"}
        
        # Validate phase index is within bounds before assignment
        if target_index >= len(phases):
            return {"status": "error", "message": f"Invalid phase index {target_index}"}
        
        current_phase_index = target_index
            
        cycle_start_time = time.time()
        label = "+".join(phases[current_phase_index])
        print(f"[ACTION A] Manual Phase Override: {label}")
        return {"status": "Phase updated", "active_phase": label}
        
    except Exception as e:
        return {"status": "error", "message": f"Internal server error: {str(e)}"}


@app.post("/api/ai-inference")
async def ai_inference(request: InferenceRequest):
    # Integrated with SLM: pass live context so the fine-tuned model returns JSON { duration, reasoning }
    try:
        global ai_recommended_duration, ai_reasoning, pending_duration

        # Validate request data
        if not hasattr(request, 'phase') or not hasattr(request, 'vps'):
            return {
                "status": "error", 
                "message": "Missing required fields: phase and vps",
                "timestamp": time.time()
            }

        if not isinstance(request.vps, dict):
            return {
                "status": "error", 
                "message": "vps must be a dictionary",
                "timestamp": time.time()
            }

        live_state = {
            "phase": str(request.phase),
            "vps": request.vps,
            "queues": {l: int(lane_stats[l]["queue"]) for l in lane_stats},
        }
        prompt = (
            "[TRAFFIC CONTROL ACTION B] Determine optimal green duration (10-60 seconds) for the current phase and traffic. "
            "Return JSON only with keys: duration (integer 10-60), reasoning (string)."
        )

        final_duration = 35
        final_reasoning = "Static density analysis suggests standard duration."

        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(
                None, assistant.query_system, prompt, live_state
            )
            # FIX Bug 12: Use safe JSON extraction
            data = extract_json_from_text(raw_response, None)
            if isinstance(data, dict):
                duration_val = data.get("duration", 35)
                if isinstance(duration_val, (int, float)):
                    final_duration = max(10, min(60, int(duration_val)))
                final_reasoning = str(data.get("reasoning", data.get("reason", final_reasoning)))
            else:
                final_reasoning = "SLM returned unstructured data. Using fallback duration."
        except Exception as e:
            print(f"[ERROR] Inference: {e}")
            final_reasoning = f"Model busy or unreachable. Fallback: {final_reasoning}"

        ai_recommended_duration = final_duration
        ai_reasoning = final_reasoning
        # FIX Bug 3: Thread-safe pending_duration update
        with pending_duration_lock:
            pending_duration = final_duration

        return {
            "duration": final_duration,
            "reasoning": final_reasoning,
            "timestamp": time.time(),
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "timestamp": time.time()
        }


class QueryRequest(BaseModel):
    query: str


@app.get("/api/metrics")
async def get_metrics():
    return {"status": "Use WebSocket for live stream"}


def _check_ollama():
    """Sync helper: ping Ollama and check model. Used in executor."""
    import requests
    r = requests.get(f"{assistant.base_url}/api/tags", timeout=2)
    if r.status_code != 200:
        return {"ok": False, "error": f"Ollama returned HTTP {r.status_code}"}
    data = r.json()
    models = [m.get("name", "") for m in data.get("models", [])]
    model_ok = any(assistant.model_name in n for n in models)
    return {
        "ok": True,
        "ollama": "reachable",
        "model": assistant.model_name,
        "model_available": model_ok,
        "message": "SLM ready" if model_ok else f"Model '{assistant.model_name}' not found in Ollama. Pull it or use an existing model."
    }


@app.get("/api/slm-status")
async def slm_status():
    """Check if the SLM (Ollama) is reachable and the expected model is available."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _check_ollama)
        return result
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Ollama not running or unreachable. Start Ollama (e.g. ollama serve) and pull the model."
        }


@app.post("/api/ask")
async def ask_assistant(request: QueryRequest):
    # FIX Bug 1: async + run_in_executor so LLM call doesn't block the event loop
    try:
        global emergency_mode, emergency_zone

        # Validate request
        if not hasattr(request, 'query') or not request.query:
            return {
                "status": "error",
                "message": "Query is required",
                "timestamp": time.time()
            }

        if not isinstance(request.query, str):
            return {
                "status": "error",
                "message": "Query must be a string",
                "timestamp": time.time()
            }

        # Sanitize query length
        query = str(request.query).strip()
        if len(query) > 1000:
            query = query[:1000]

        mock_live_state = {
            l: int(lane_stats[l]["queue"]) for l in lane_stats
        }

        # FIX Bug 8: Use regex-based zone detection with word boundaries
        detected_zone = detect_emergency_zone(query)
        low_query = query.lower()

        if "ambulance" in low_query or "emergency" in low_query:
            emergency_mode = True
            emergency_zone = detected_zone
            print(f"[EMERGENCY] Forcing Green Corridor for Zone {emergency_zone}.")
            response = (
                f"🚨 EMERGENCY OVERRIDE ACTIVATED. Enforcing Green Corridor for Zone {emergency_zone}. "
                "All intersecting traffic is being held."
            )
        elif "clear emergency" in low_query or "reset" in low_query:
            emergency_mode = False
            emergency_zone = None
            response = "Emergency cleared. System returning to standard AI optimized cycles."
        else:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, assistant.query_system, query, mock_live_state
                )
            except Exception as e:
                print(f"[ERROR] LLM Assistant: {e}")
                response = "Assistant temporarily unavailable. Please try again later."

        # FIX Bug 6: Check LLM error status before using response
        payload = {"timestamp": time.time(), "status": "EMERGENCY_ACTIVE" if emergency_mode else "Operational"}
        try:
            parsed = safe_json_parse(response, None)
            if isinstance(parsed, dict):
                # Check if response indicates an error
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
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "timestamp": time.time()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
