# Dynamic AI Traffic Flow Optimizer (DAITFO) 🚦

DAITFO is a modern, ultra-low-latency traffic management system designed to alleviate urban congestion through Deep Reinforcement Learning, Computer Vision edge-processing, and real-time Graph Routing. The platform continuously monitors intersections to optimize traffic phases, while providing an instantaneous overriding "Green Corridor" priority path for emergency vehicles (ambulances, fire trucks, etc.) across a metropolitan grid.

---

## 🏗 System Architecture

DAITFO relies on a highly scalable, decoupled microservices architecture designed to handle high-throughput telemetry streams:

### 1. 📷 Edge Vision & Telemetry (Layer 1)
Using models like **YOLOv8** running on Edge Devices (e.g., NVIDIA Jetson or Raspberry Pi Edge), the intersections process live RTSP video feeds locally. No video leaves the edge - only lightweight metadata (vehicle counts, lane densities, and emergency vehicle detections) is sent upstream.

### 2. ⚡ Data Orchestration (Layer 2)
The "Nerve Center" utilizes **Apache Kafka / Redpanda** to handle high-volume ingress streams from thousands of potential edge nodes without bottlenecking.

### 3. 🧠 AI Core / The Brain (Layer 3)
- **RL Traffic Optimizer:** Uses **Ray RLlib (PPO/MADDPG)** to dictate phase changes based on current traffic queues rather than outdated Time-of-Day systems.
- **SLM Tactical Intelligence:** A Small Language Model (Ollama) that acts as an "AI Pilot Advisory", generating human-readable reasoning and recommendations based on current intersection metrics.
- **Emergency Router:** Uses **Neo4j** (Graph Database) to calculate the absolute fastest route for an emergency vehicle. Edge weights are dynamically penalized based on live traffic congestion (VPM), forcing emergency vehicles away from heavily jammed corridors automatically.

### 4. 🗄️ Persistence Layer (Layer 4)
- **Redis (Hot Store):** Handles the volatile 1Hz real-time state, UI caching, and fast emergency active overrides.
- **TimescaleDB:** Dedicated time-series database analyzing historical trends to train the RL Models.
- **Neo4j:** Graph engine mapping out intersections as nodes and roads as edges.

### 5. 💻 App & Dashboard Layer (Layer 5)
- **City Operator Dashboard:** A powerful **Next.js** frontend with vivid visualizers showing current intersection queues, live VPM (Vehicles Per Minute) flows, real-time AI reasoning, and direct phase override commands.
- **FastAPI / WebSockets Backend:** Secure backend linking python AI pipelines with the operator UI instantly.

---

## 🚀 Setting Up the Project

### Prerequisites
- Docker & Docker Compose
- Node.js (v18+)
- Python (3.10+)
- Environment: Local Ollama (if using the AI SLM reasoning)

### 1. Launch the Analytics & Persistence Engines
Launch Kafka, Redis, Neo4j, and TimescaleDB via Docker:
```bash
docker-compose up -d redis timescaledb neo4j kafka
```

### 2. Run the Main Backend Pipeline
Install the core AI / Backend Python dependencies:
```bash
cd project
pip install -r requirements.txt
```
Start the primary FastAPI and WebSocket Backend Gateway:
```bash
python -m uvicorn ui.backend:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the Operator Dashboard Frontend
```bash
cd project/ui/dashboard
npm install
npm run dev
```

### 4. Spin up the Core AI Loop
Finally, boot up `main.py` which actively coordinates the intersection simulation, queries the LLM/SLM, runs the Neo4j routing updates, and processes RL inferences:
```bash
python project/main.py
```
*(If Ray/RLlib is missing, the system gracefully falls back to a highly-tuned Python Heuristic algorithm).*

---

## 🚨 Features

- **Real-Time Traffic Dashboard:** Operator overrides, dark/light aesthetics, visual phase representations.
- **Dynamic Active Tracking:** Visual dots mapping to exact VPM per corridor directly on the dashboard.
- **SLM Advisory:** A natural language system explaining *why* the system is changing the lights.
- **Emergency Override Failsafe:** Single button manual preemption resolving directly inside the RL loops.
- **City Graph Scaling:** Expanding from single-intersection routing to city-block scale logic.
