import argparse
import json
import random
import os
import sys
import numpy as np

# Adjust path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def generate_v5(num_samples=5000):
    examples = []
    for _ in range(num_samples):
        q_n = random.randint(0, 30)
        q_s = random.randint(0, 30)
        q_e = random.randint(0, 30)
        q_w = random.randint(0, 30)
        q_nr = random.randint(0, min(q_n, 15))
        q_sr = random.randint(0, min(q_s, 15))
        q_er = random.randint(0, min(q_e, 15))
        q_wr = random.randint(0, min(q_w, 15))
        ped = random.randint(0, 40)
        has_emergency = random.random() < 0.1
        
        if has_emergency:
            emerg_dir = random.choice(["N", "S", "E", "W"])
            action = {"N": 0, "S": 1, "E": 2, "W": 3}[emerg_dir]
            reason = f"Emergency vehicle from {emerg_dir}"
            duration = 60
            input_text = (f"MODE: EMERGENCY | Q_N: {q_n} | Q_S: {q_s} | Q_E: {q_e} | "
                         f"Q_W: {q_w} | PED: {ped} | ALERT: Vehicle from {emerg_dir}")
        elif ped > 25:
            action = 4
            reason = "High pedestrian demand"
            duration = min(60, max(15, int(ped * 1.5)))
            input_text = (f"MODE: PEDESTRIAN | Q_N: {q_n} | Q_S: {q_s} | Q_E: {q_e} | "
                         f"Q_W: {q_w} | QR_N: {q_nr} | QR_S: {q_sr} | QR_E: {q_er} | "
                         f"QR_W: {q_wr} | PED: {ped}")
        else:
            queues = {"N": q_n, "S": q_s, "E": q_e, "W": q_w}
            best = max(queues, key=queues.get)
            action = {"N": 0, "S": 1, "E": 2, "W": 3}[best]
            reason = f"Serving highest queue: {best}={queues[best]}"
            duration = min(60, max(10, (queues[best] * 2) + 3))
            
            input_text = (f"MODE: OPTIMIZE | Q_N: {q_n} | Q_S: {q_s} | Q_E: {q_e} | "
                         f"Q_W: {q_w} | QR_N: {q_nr} | QR_S: {q_sr} | QR_E: {q_er} | "
                         f"QR_W: {q_wr} | PED: {ped}")

        output_json = json.dumps({"action": action, "duration": duration, "desc": reason})
        examples.append({"instruction": input_text, "output": output_json})
    return examples

def generate_v4(num_samples=5000):
    examples = []
    for _ in range(num_samples):
        q = {
            "N": random.randint(0, 30), "S": random.randint(0, 30),
            "E": random.randint(0, 30), "W": random.randint(0, 30),
            "NL": random.randint(0, 15), "SL": random.randint(0, 15),
            "EL": random.randint(0, 15), "WL": random.randint(0, 15)
        }
        has_emergency = random.random() < 0.1
        
        if has_emergency:
            emerg_move = random.choice(["NS_STRAIGHT", "NS_LEFT", "EW_STRAIGHT", "EW_LEFT"])
            if emerg_move == "NS_STRAIGHT":
                action = [2, 6]
                reason = "Emergency: North-South Straight cleared"
            elif emerg_move == "NS_LEFT":
                action = [1, 5]
                reason = "Emergency: North-South Protected Left turns"
            elif emerg_move == "EW_STRAIGHT":
                action = [4, 8]
                reason = "Emergency: East-West Straight cleared"
            else:
                action = [3, 7]
                reason = "Emergency: East-West Protected Left turns"
            input_text = f"MODE: EMERGENCY | Q: {q} | ALERT: {emerg_move} request"
        else:
            vertical_pairs = {
                (1, 5): q["NL"] + q["SL"],
                (1, 6): q["NL"] + q["N"],
                (2, 5): q["S"] + q["SL"],
                (2, 6): q["S"] + q["N"]
            }
            horizontal_pairs = {
                (3, 7): q["EL"] + q["WL"],
                (3, 8): q["EL"] + q["E"],
                (4, 7): q["W"] + q["WL"],
                (4, 8): q["E"] + q["W"]
            }
            v_best = max(vertical_pairs, key=vertical_pairs.get)
            h_best = max(horizontal_pairs, key=horizontal_pairs.get)
            
            if vertical_pairs[v_best] >= horizontal_pairs[h_best]:
                action = list(v_best)
                reason = "Optimize: Serving high NS demand"
            else:
                action = list(h_best)
                reason = "Optimize: Serving high EW demand"
            input_text = f"MODE: OPTIMIZE | Q: {q}"

        output_json = json.dumps({
            "phases": action,
            "logic": "8-PHASE-DUAL-RING",
            "desc": reason
        })
        examples.append({
            "instruction": input_text,
            "output": output_json
        })
    return examples

def generate_base_rllib_dqn(num_samples=5000):
    # Fallback to model-based dataset generator logic (original v1/v2/v3)
    # If imports fail or files don't exist, we fallback to a synthetic structure
    try:
        import yaml
        from stable_baselines3 import DQN
        from models.traffic_lstm import TrafficLSTM
        import torch
        
        with open("config/config.yaml", "r") as f:
            config = yaml.safe_load(f)
        params = config["training"]
        lstm = TrafficLSTM(input_size=4, hidden_size=params["hidden_size"])
        weights_path = os.path.join(params["checkpoint_dir"], "lstm_weights.pth")
        if os.path.exists(weights_path):
            lstm.load_state_dict(torch.load(weights_path, map_location="cpu"))
        lstm.eval()
        
        model_path = os.path.join(params["checkpoint_dir"], "dqn_traffic_model")
        model = DQN.load(model_path, device="cpu")
        data = np.load("data/raw/traffic_data_50k.npy")
        
        dataset = []
        seq_len = params["sequence_len"]
        for i in range(seq_len, len(data), 5):
            window = data[i-seq_len : i]
            state = data[i]
            seq_tensor = torch.FloatTensor(np.array(window)).unsqueeze(0)
            with torch.no_grad():
                lstm_pred = lstm(seq_tensor).item()
            aug_state = np.append(state, [lstm_pred])
            action, _ = model.predict(aug_state, deterministic=True)
            
            queue_count = int(state[0])
            avg_speed = round(float(state[1]), 2)
            phase = int(state[2])
            
            instruction = f"Intersection State: Queue Length {queue_count}, Average Speed {avg_speed} m/s, Current Phase {phase}."
            response = f"{{\"action\": {int(action)}, \"reason\": \"Optimized for queue reduction and flow consistency.\"}}"
            prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are an AI Traffic Controller. Based on sensor data, select the best signal phase ID to minimize traffic congestion.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{response}<|eot_id|>"
            dataset.append({"text": prompt})
            if len(dataset) >= num_samples:
                break
        return dataset
    except Exception as e:
        print(f"[WARN] LSTM/DQN model generation failed: {e}. Falling back to synthetic model format.")
        # Synthetic v1 fallback
        examples = []
        for _ in range(num_samples):
            q_len = random.randint(5, 40)
            avg_spd = random.uniform(5.0, 25.0)
            cur_ph = random.choice([0, 1])
            action = 0 if q_len > 20 else 1
            instruction = f"Intersection State: Queue Length {q_len}, Average Speed {avg_spd:.2f} m/s, Current Phase {cur_ph}."
            response = f"{{\"action\": {action}, \"reason\": \"Optimized for queue reduction.\"}}"
            examples.append({
                "text": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are an AI Traffic Controller.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{response}<|eot_id|>"
            })
        return examples

def main():
    parser = argparse.ArgumentParser(description="Unified DAITFO Dataset Generator")
    parser.add_argument("--phase-scheme", type=str, default="v5_5phase", choices=["v1", "v2", "v3", "v4_8phase", "v5_5phase"], help="Phase scheme configuration")
    parser.add_argument("--samples", type=int, default=5000, help="Number of samples to generate")
    parser.add_argument("--out", type=str, default=None, help="Output destination path")
    args = parser.parse_args()

    os.makedirs("data", exist_ok=True)
    
    if args.phase-scheme == "v5_5phase":
        examples = generate_v5(args.samples)
        output_file = args.out or "data/finetune_v5_5phase.jsonl"
    elif args.phase-scheme == "v4_8phase":
        examples = generate_v4(args.samples)
        output_file = args.out or "data/finetune_v4_8phase.jsonl"
    else:
        examples = generate_base_rllib_dqn(args.samples)
        output_file = args.out or f"data/llm_fine_tune_dataset_{args.phase_scheme}.jsonl"
        
    with open(output_file, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(examples)} samples under phase-scheme '{args.phase_scheme}' -> {output_file}")

if __name__ == "__main__":
    main()
