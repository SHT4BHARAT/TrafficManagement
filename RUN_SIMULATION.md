# DAITFO Automatic Simulation - Quick Start Guide

## Prerequisites

```bash
# Python 3.9+ with pip
python --version

# Required packages (install from requirements.txt)
pip install -r project/requirements.txt
```

If packages are missing:
```bash
pip install fastapi uvicorn pydantic requests pytest pytest-asyncio
```

---

## Running the Automatic Simulation

### Option 1: Start Backend with Auto-Reload (Development)
```bash
cd D:\HackaThon\IndiaInnovates2026
uvicorn project.ui.backend:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

The simulation automatically starts when the backend starts (due to `@app.on_event("startup")`).

### Option 2: Start Backend without Auto-Reload (Production)
```bash
cd D:\HackaThon\IndiaInnovates2026
uvicorn project.ui.backend:app --host 0.0.0.0 --port 8000
```

### Option 3: Run with Python Directly
```bash
cd D:\HackaThon\IndiaInnovates2026\project\ui
python -c "import backend; import uvicorn; uvicorn.run(backend.app, host='0.0.0.0', port=8000)"
```

---

## Verify Simulation is Running

### Check 1: HTTP Request
```bash
curl http://localhost:8000/
```

**Expected Response:**
```json
{
  "status": "DAITFO Backend Online",
  "version": "2.3",
  "websocket_path": "/ws"
}
```

### Check 2: WebSocket Connection (in another terminal)
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/ws
```

**Expected Output:** Real-time traffic data stream
```json
{
  "intersection": "INT_001 · MAIN ST & BROADWAY",
  "queues": {"N": 12, "S": 8, "E": 5, "W": 3},
  "vpm": {"N": 15, "S": 12, "E": 8, "W": 5},
  "green_lights": ["N", "S"],
  "cycle_countdown": 28,
  ...
}
```

### Check 3: View Dashboard
Open in browser:
```
http://localhost:3000
```

The dashboard automatically connects to WebSocket and displays:
- Intersection diagram with traffic lights
- Queue lengths per lane
- Performance metrics
- Event log
- Control buttons

---

## Control the Simulation

### 1. Change Traffic Light Phase (Manual Control)
```bash
# Green North-South
curl -X POST http://localhost:8000/api/select-phase \
  -H "Content-Type: application/json" \
  -d '{"phase": "NS"}'

# Green East-West
curl -X POST http://localhost:8000/api/select-phase \
  -H "Content-Type: application/json" \
  -d '{"phase": "EW"}'

# Single lane green (North only)
curl -X POST http://localhost:8000/api/select-phase \
  -H "Content-Type: application/json" \
  -d '{"phase": "N"}'
```

### 2. Set Vehicle Arrival Rates (Manual Mode)
```bash
# Set manual mode
curl -X POST http://localhost:8000/api/controller-config \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual"}'

# Set vehicles per minute for each lane
curl -X POST http://localhost:8000/api/controller-config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "manual",
    "vps": {
      "N": 25,
      "S": 20,
      "E": 15,
      "W": 10
    }
  }'

# Switch to auto mode (random VPS)
curl -X POST http://localhost:8000/api/controller-config \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto"}'
```

### 3. Trigger AI Inference
```bash
curl -X POST http://localhost:8000/api/ai-inference \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "NS",
    "vps": {"N": 15, "S": 12, "E": 8, "W": 5}
  }'
```

**Response:**
```json
{
  "duration": 40,
  "reasoning": "High North-South traffic detected. Increasing green duration.",
  "timestamp": 1234567890.123,
  "status": "success"
}
```

### 4. Trigger Emergency Mode
```bash
# Activate green corridor for ambulance going North
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Ambulance heading north"}'

# Clear emergency
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Clear emergency"}'
```

### 5. Get LLM Assistant Query Response
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Why is Lane S congested?"}'
```

---

## Running Tests

### Test All Components
```bash
# Install pytest if needed
pip install pytest pytest-asyncio

# Run all tests
pytest project/tests/test_simulation.py -v
```

### Test Specific Component
```bash
# Test traffic simulator
pytest project/tests/test_simulation.py::TestTrafficSimulation -v

# Test RL agent
pytest project/tests/test_simulation.py::TestRLAgent -v

# Test SCOOT optimizer
pytest project/tests/test_simulation.py::TestSCOOT -v

# Test utilities
pytest project/tests/test_simulation.py::TestUtilFunctions -v
```

### Run with Coverage Report
```bash
pytest project/tests/test_simulation.py --cov=project --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Simulation Parameters

### Default Configuration
```python
# Phase rotation (6 phases, each with configurable duration)
Phases:
  1. N only
  2. S only
  3. E only
  4. W only
  5. N-S together (pair)
  6. E-W together (pair)

# Default durations
Default phase duration: 35 seconds
Min duration: 10 seconds
Max duration: 60 seconds
SCOOT adjustment: ±3 seconds

# Vehicle dynamics
Arrival rate: 2-40 vehicles/minute per lane (configurable)
Discharge rate when green: ~1.5 vehicles/second
Queue increase per tick: arrival_rate / 120

# Broadcast
Update rate: 0.5 seconds
Event log capacity: 1000 events (circular buffer)
```

### Tuning Parameters
```python
# File: project/ui/backend.py

# Line 178: Vehicle arrival rate in auto mode
stats["vpm"] = random.randint(2, 40)
# Change range to control traffic intensity

# Line 185: Queue discharge rate
clearing_step = random.uniform(0.8, 1.2)
# Increase to discharge faster (e.g., 1.2, 1.8)

# Line 229: Broadcast rate
await asyncio.sleep(0.5)
# Decrease for faster updates (e.g., 0.25)
# Increase for lower bandwidth (e.g., 1.0)

# Line 10, 60 in core/optimization.py: SCOOT step size
self.step = 3  # ±3 second adjustments
# Change to 1, 5, or 10 for different sensitivity
```

---

## Monitoring & Debugging

### View Real-Time Logs
```bash
# Terminal 1: Start backend
uvicorn project.ui.backend:app --reload

# Terminal 2: Watch logs
tail -f backend.log  # Or watch terminal 1 output
```

### Look for These Messages
```
# Normal startup
[SYSTEM] System ready. Running closed-loop simulation...
[LOGIC] Phase → N-S Green for 35s

# With SCOOT optimization
SCOOT optimized NS to 40s (PI: 12.34)

# With AI inference
AI queued duration applied: 45s

# Emergency mode
EMERGENCY OVERRIDE: Priority Path N active
```

### Common Debugging Commands
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Mac/Linux

# Kill process on port 8000
taskkill /PID <PID> /F  # Windows
kill -9 <PID>  # Mac/Linux

# Check backend memory usage
Get-Process | Where-Object {$_.ProcessName -match "python"} | Select-Object Name, WorkingSet
```

---

## Integration with Dashboard

### Running Frontend (if available)
```bash
# In separate terminal, from UI project directory
cd path/to/frontend
npm install
npm start
```

The frontend automatically connects to `ws://localhost:8000/ws` and displays:
- Live intersection visualization
- Queue lengths
- Performance metrics
- Control panel
- Event logs

### Dashboard Updates
- **Real-time:** Every 0.5 seconds via WebSocket
- **Responsive:** Shows all phase changes immediately
- **Interactive:** Manual phase selection and VPS control
- **Monitoring:** Event log tracks all changes

---

## Stopping the Simulation

### Graceful Shutdown
```bash
# Press Ctrl+C in terminal where uvicorn is running
# OR
# Send HTTP request
curl -X POST http://localhost:8000/shutdown
```

### Force Kill
```bash
# Windows
taskkill /IM python.exe /F

# Mac/Linux
killall python
```

---

## Troubleshooting

### Issue: Port Already in Use
```bash
# Use different port
uvicorn project.ui.backend:app --port 8001
```

### Issue: Import Errors
```bash
# Add project to Python path
set PYTHONPATH=%PYTHONPATH%;D:\HackaThon\IndiaInnovates2026
# Or run from correct directory
cd D:\HackaThon\IndiaInnovates2026
uvicorn project.ui.backend:app --reload
```

### Issue: No WebSocket Data
1. Check backend is running: `curl http://localhost:8000/`
2. Check logs for startup errors
3. Verify SCOOT initialized (should see message or warning)
4. Try reconnecting WebSocket client

### Issue: Simulation Stuck
1. Check system resources (CPU, memory)
2. Verify event loop not blocked (check logs)
3. Restart backend: Kill and restart uvicorn
4. Check for exceptions in console output

---

## Next Steps

1. **Monitor Simulation:** Keep WebSocket connected to watch traffic flow
2. **Run Tests:** Execute test suite to verify all components
3. **Tune Parameters:** Adjust arrival rates and phase durations
4. **Trigger Events:** Test emergency mode and AI inference
5. **Integrate Dashboard:** Connect frontend for visualization
6. **Scale Up:** Add more intersections and optimize across city network

---

## References

- **Backend Code:** `project/ui/backend.py`
- **Simulation Loop:** Lines 111-235
- **Test Suite:** `project/tests/test_simulation.py`
- **Debug Guide:** `SIMULATION_DEBUG_GUIDE.md`
- **Fixes Applied:** `FIXES_APPLIED.md`
