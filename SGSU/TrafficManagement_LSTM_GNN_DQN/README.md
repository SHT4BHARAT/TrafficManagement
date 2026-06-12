# Optimized Traffic Management: LSTM + DQN + BitNet

This implementation is optimized for CPU-only local machines, integrating sequence prediction, reinforcement learning, and LLM-based emergency handling.

## Tech Stack
- **SUMO**: Traffic simulation.
- **LSTM (PyTorch CPU)**: 2-layer lightweight temporal predictor (4 inputs, 64 hidden).
- **DQN (Stable-Baselines3 CPU)**: Signal timing optimizer (20k timesteps).
- **BitNet Falcon**: High-level emergency decision agent.

## Project Structure
```
├── agents/
│   ├── dqn_agent.py      # SB3 Wrapper (Integrated in scripts)
│   └── emergency_agent.py # BitNet Falcon Bridge
├── config/
│   └── config.yaml       # CPU-optimized hyperparameters
├── env/
│   └── sumo_env.py       # Custom Gym wrapper for SUMO (4 features)
├── models/
│   └── traffic_lstm.py   # Lightweight LSTM class
├── scripts/
│   ├── collect_data.py   # Harvest 50k baseline samples
│   ├── pretrain_lstm.py  # Train predictor on CPU
│   ├── train_rl.py       # Master signal timing with DQN
│   └── evaluate.py       # Run simulation with LLM monitoring
```

## Setup
1. **Dependencies**:
```bash
pip install -r requirements.txt
```

2. **SUMO**: Ensure `SUMO_HOME` is set. Place your `.net.xml` and `.rou.xml` files in `data/` or update `config/config.yaml`.

## Pipeline Execution
1. **Collect Data** (Harvest 50k samples):
```bash
python scripts/collect_data.py
```
2. **Pre-train LSTM** (CPU convergence ~20-30 mins):
```bash
python scripts/pretrain_lstm.py
```
3. **Train RL Agent** (CPU training ~1-2 hrs):
```bash
python scripts/train_rl.py
```
4. **Run Evaluation** (With BitNet emergency triggers):
```bash
python scripts/evaluate.py
```
