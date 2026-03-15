# DAITFO Automatic Simulation - Monitoring & Debug Guide

## Overview

The DAITFO system runs an automatic traffic simulation loop that:
1. Simulates vehicle arrivals and departures at a 4-way intersection
2. Uses SCOOT optimization to calculate optimal signal timings
3. Allows AI inference to override signal timings
4. Broadcasts real-time data via WebSocket to the dashboard
5. Maintains event logs for audit trail

---

## System Architecture

### Startup Flow
```
FastAPI Server Starts
    ↓
@app.on_event("startup") triggers
    ↓
asyncio.create_task(simulate_traffic_stream()) started
    ↓
Background async loop begins running every 0.5 seconds
    ↓
WebSocket broadcasts data to connected clients
```

### Simulation Loop Components

**File:** `project/ui/backend.py` - `simulate_traffic_stream()` function (lines 111-235)

```python
# Runs every 0.5 seconds
while True:
    # 1. Check emergency mode
    # 2. Rotate phases if duration expired
    # 3. Optimize new phase duration (SCOOT or AI)
    # 4. Simulate queue dynamics per lane
    # 5. Calculate performance metrics
    # 6. Broadcast to WebSocket clients
    # 7. Sleep 0.5s
```

---

## Key Variables to Monitor

### Global State Variables
```python
# Traffic Control State
current_phase_index        # 0-5: which phase is active
current_phase_duration     # 10-60: seconds for current phase
cycle_start_time          # timestamp when phase started

# AI Inference State
ai_recommended_duration   # 10-60: duration from LLM
ai_reasoning              # explanation from LLM
pending_duration          # next duration queued by AI
pending_duration_lock     # threading.Lock for race condition prevention

# Emergency State
emergency_mode            # True/False: green corridor active
emergency_zone           # "N"/"S"/"E"/"W": which lane has priority

# Traffic State
lane_stats               # {lane: {queue, vpm, red_time}}
event_log                # deque(maxlen=1000): audit trail
controller_mode          # "manual" or "auto"
```

---

## Monitoring Checklist

### 1. Startup Verification
```bash
# Check if backend is running
curl http://localhost:8000/

# Expected response:
# {"status": "DAITFO Backend Online", "version": "2.3", "websocket_path": "/ws"}
```

### 2. WebSocket Connection
```bash
# Connect to WebSocket
wscat -c ws://localhost:8000/ws

# Should receive data every ~0.5 seconds with structure:
{
  "intersection": "INT_001 · MAIN ST & BROADWAY",
  "queues": {"N": X, "S": X, "E": X, "W": X},
  "vpm": {"N": X, "S": X, "E": X, "W": X},
  "red_times": {"N": X, "S": X, "E": X, "W": X},
  "timings": {"N": X, "S": X, "E": X, "W": X},
  "green_lights": ["N", "S"],  // Currently green lanes
  "cycle_countdown": X,         // Seconds remaining in current phase
  "ai_duration": X,
  "ai_reasoning": "string",
  "emergency": {"active": false, "zone": null},
  "pi": X.XX,                   // Performance Index
  "events": [{...}, {...}],     // Event log
  "timestamp": X.XXX
}
```

### 3. Phase Rotation
```bash
# Watch phase rotation in logs
[LOGIC] Phase → N-S Green for 35s
[LOGIC] Phase → E-W Green for 35s
[LOGIC] Phase → N Green for 35s
...
```

### 4. Queue Dynamics
- Queue length should increase as vehicles arrive (`vpm / 120.0`)
- Queue should decrease when lane is green (`0.8-1.2 vehicles`)
- Red time should increase for non-green lanes (`+0.5 per tick`)

### 5. SCOOT Optimization
```bash
# Look for SCOOT optimization messages in events
{
  "type": "ai-b",
  "msg": "SCOOT optimized NS to 40s (PI: 12.34)"
}
```

### 6. AI Inference
```bash
# Trigger AI inference via API
curl -X POST http://localhost:8000/api/ai-inference \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "NS",
    "vps": {"N": 15, "S": 12, "E": 8, "W": 5}
  }'

# Should see in events:
{
  "type": "ai-b",
  "msg": "AI queued duration applied: 45s"
}
```

---

## Common Issues & Solutions

### Issue 1: Simulation Not Broadcasting Data
**Symptoms:** No WebSocket messages received, or empty arrays

**Root Causes:**
1. Backend not started
2. WebSocket not properly connected
3. Simulation loop crashed (check console logs)

**Debug Steps:**
```python
# Check if simulation loop is running
# Add temporary debug print in simulate_traffic_stream() at line 123:
print(f"[DEBUG] Tick at {time.time()}, elapsed={elapsed}, duration={current_phase_duration}")

# Check last broadcast timestamp
# If not updating, simulation loop may be stuck
```

**Solutions:**
- Restart FastAPI server: `uvicorn ui/backend.py --reload`
- Check for exceptions in event loop (lines 231-234)
- Verify SCOOT controller initialized (check logs for warnings)

---

### Issue 2: Queue Never Clears
**Symptoms:** Queue lengths keep growing, never decrease

**Root Causes:**
1. Phase not rotating (timer stuck)
2. Green lane discharge logic broken
3. Queue arrival rate too high

**Debug Steps:**
```python
# Check phase rotation
# Look for "Phase rotated" messages in events
# If missing, check:
#   - elapsed >= current_phase_duration (line 137)
#   - emergency_mode = False (line 137)

# Check if discharge is happening
# In traffic_sim.py, add debug:
print(f"[SIM] Before: {self.queues}, Action: {action}")
# ... discharge logic ...
print(f"[SIM] After: {self.queues}")
```

**Solutions:**
- Check `cycle_start_time` is being reset (line 139)
- Verify `current_phase_duration` > 0 (should be 10-60)
- Increase clearing_step in line 185 if arrival rate is high

---

### Issue 3: AI Inference Not Applied
**Symptoms:** `pending_duration` always None, AI messages don't appear

**Root Causes:**
1. AI inference endpoint not being called
2. Race condition on `pending_duration_lock`
3. AI response format incorrect

**Debug Steps:**
```python
# Check if pending_duration is being set
# Add debug at line 395 in ai_inference:
print(f"[DEBUG] Setting pending_duration={final_duration}")

# Check if it's being consumed
# Add debug at line 157 in simulate_traffic_stream:
print(f"[DEBUG] Checking pending_duration={pending_duration}")
```

**Solutions:**
- Call `/api/ai-inference` endpoint (see example above)
- Verify response format: `{"duration": 35, "reasoning": "..."}`
- Check Ollama is running if using real LLM
- Increase AI response timeout (line 74 in llm_assistant.py)

---

### Issue 4: Emergency Mode Stuck
**Symptoms:** Emergency always active, green corridor won't clear

**Root Causes:**
1. `emergency_mode = True` but query doesn't contain "clear emergency"
2. `emergency_zone` not properly reset

**Debug Steps:**
```python
# Check emergency state
print(f"[DEBUG] emergency_mode={emergency_mode}, zone={emergency_zone}")

# Verify "clear" command is registered
# In ask_assistant at line 484:
elif "clear emergency" in low_query or "reset" in low_query:
```

**Solutions:**
- Send query: "Clear emergency" or "Reset emergency"
- Check dashboard shows emergency status
- Manually reset via API if needed

---

### Issue 5: High Memory Usage
**Symptoms:** Memory gradually increases, eventual OOM

**Root Causes:**
1. Event log still using list instead of deque (pre-fix)
2. Last broadcast not being cleaned properly
3. WebSocket client list growing unbounded

**Debug Steps:**
```python
# Check event_log type
print(f"[DEBUG] event_log type: {type(event_log)}")
# Should be: <class 'collections.deque'>

# Check event_log size
print(f"[DEBUG] event_log size: {len(event_log)}")
# Should never exceed 1000 (maxlen=1000)

# Check WebSocket connections
print(f"[DEBUG] Active connections: {len(manager.active_connections)}")
```

**Solutions:**
- Verify `event_log = deque(maxlen=1000)` at line 100
- Check dead connections are properly removed (lines 64-65)
- Monitor memory with: `watch -n 1 'ps aux | grep backend'`

---

## Performance Tuning

### Phase Duration
- **Current:** 35 seconds per phase
- **Too short:** Queues build up, long wait times
- **Too long:** Inefficient use of other lanes
- **Tuning:** SCOOT optimizes this with ±3s adjustments

### Simulation Tick Rate
- **Current:** 0.5 seconds broadcast rate
- **Higher:** More responsive but higher CPU
- **Lower:** Less responsive but lower bandwidth
- **Adjust:** Line 229 in backend.py

### Vehicle Arrival Rate
- **Current:** 2-40 vehicles per minute (vpm) per lane
- **Formula:** `arrival_step = vpm / 120.0`
- **Adjust:** Manual VPS settings via `/api/controller-config`

### Queue Discharge Rate
- **Current:** 0.8-1.2 vehicles per lane per tick
- **Calculated as:** ~1.5 vehicles/second when green
- **Adjust:** Line 185 in backend.py

---

## Testing the Simulation

### Unit Tests
```bash
# Run all tests
pytest project/tests/test_simulation.py -v

# Run specific test class
pytest project/tests/test_simulation.py::TestTrafficSimulation -v

# Run with coverage
pytest project/tests/test_simulation.py --cov=project
```

### Manual Testing
```bash
# Test 1: Basic connectivity
curl http://localhost:8000/

# Test 2: WebSocket streaming
wscat -c ws://localhost:8000/ws

# Test 3: Manual phase control
curl -X POST http://localhost:8000/api/select-phase \
  -H "Content-Type: application/json" \
  -d '{"phase": "EW"}'

# Test 4: Auto/manual mode toggle
curl -X POST http://localhost:8000/api/controller-config \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto"}'

# Test 5: Manual VPS setting
curl -X POST http://localhost:8000/api/controller-config \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual", "vps": {"N": 20, "S": 15, "E": 10, "W": 12}}'

# Test 6: Emergency query
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Ambulance heading north"}'
```

---

## Log Interpretation

### Normal Operation Log
```
[LOGIC] Phase → N-S Green for 35s
[LOGIC] Phase → E-W Green for 35s
[LOGIC] Phase → N Green for 35s
[LOGIC] Phase → S Green for 35s
[LOGIC] Phase → E Green for 35s
[LOGIC] Phase → W Green for 35s
```

### With SCOOT Optimization
```
SCOOT optimized NS to 40s (PI: 12.34)
SCOOT optimized EW to 30s (PI: 10.22)
```

### With AI Inference
```
AI queued duration applied: 45s
AI queued duration applied: 32s
```

### Emergency Mode
```
EMERGENCY OVERRIDE: Priority Path N active
Phase → N Green for 60s  [held until cleared]
```

### Error Conditions
```
[ERROR] Traffic simulation loop: [exception details]
[WARN] SCOOTController initialization failed: [reason]
[WARN] TomTom fetch failed: [reason]
```

---

## Production Monitoring

### Key Metrics
1. **Cycle Time:** Time for one complete phase rotation
2. **Avg Queue Length:** Should trend downward with optimization
3. **Avg Wait Time:** Red light duration experienced by vehicles
4. **Performance Index:** Composite metric from SCOOT (lower is better)
5. **Uptime:** Should maintain 99%+ availability

### Alert Thresholds
- **Queue > 50 vehicles:** High congestion, check optimization
- **PI > 30:** Poor performance, consider manual override
- **Broadcast latency > 1s:** Network issue or computation bottleneck
- **Memory > 500MB:** Check for leaks

### Logging Integration
```python
# Add structured logging for monitoring
import logging

logger = logging.getLogger("DAITFO")
logger.info(f"phase_rotation", extra={
    "phase": current_green_pair,
    "duration": current_phase_duration,
    "pi": scoot.performance_index,
    "avg_queue": sum(lane_stats[l]["queue"] for l in lane_stats) / 4
})
```

---

## References

- Main simulation: `project/ui/backend.py` - `simulate_traffic_stream()` (lines 111-235)
- Test suite: `project/tests/test_simulation.py`
- Components tested:
  - Traffic simulator: `project/simulation/traffic_sim.py`
  - RL optimizer: `project/brain/optimizer.py`
  - Routing: `project/brain/routing.py`
  - SCOOT: `project/core/optimization.py`
  - Utils: `project/core/utils.py`
