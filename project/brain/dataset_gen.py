import json
import random
import os

def generate_dataset(num_samples=2000, output_file="traffic_dataset.jsonl"):
    """
    Generates a synthetic dataset for fine-tuning an SLM to output strict JSON
    for traffic light actuation based on intersection state.
    """
    instructions = [
        "You are an AI traffic controller. Analyze the intersection state and call the 'set_tl_phase' function with the optimal phase.",
        "Based on the following traffic density and emergency observations, output a JSON tool call to actuate the correct traffic light phase.",
        "Evaluate the queue lengths and priority triggers below. Respond ONLY with the JSON function call to change the traffic phase."
    ]

    phases = ["N", "S", "E", "W"]
    dataset = []

    for _ in range(num_samples):
        instruction = random.choice(instructions)
        
        # Randomize queues
        queues = {p: random.randint(0, 50) for p in phases}
        
        # 10% chance of an emergency vehicle
        emergency_zone = None
        is_emergency = random.random() < 0.1
        if is_emergency:
            emergency_zone = random.choice(phases)
        
        # Determine the correct phase (Logic: Emergency overrides, otherwise max queue)
        if is_emergency:
            optimal_phase = emergency_zone
        else:
            optimal_phase = max(queues, key=queues.get)
            
        current_phase = random.choice(phases)
        
        # Construct Input
        input_text = f"Intersection: INT_001\nCurrent Phase: {current_phase}\n"
        input_text += "Queue Lengths:\n"
        for p, q in queues.items():
            input_text += f"- Lane {p}: {q} vehicles\n"
        if is_emergency:
            input_text += f"EMERGENCY VEHICLE DETECTED in Lane {emergency_zone}!\n"
        else:
            input_text += "Emergency Vehicles: None\n"

        # Construct Output (Strict JSON)
        output_data = {
            "name": "set_tl_phase",
            "arguments": {
                "intersection_id": "INT_001",
                "phase_id": optimal_phase
            }
        }
        output_json = json.dumps(output_data)

        # Alpaca standard format for Unsloth
        dataset.append({
            "instruction": instruction,
            "input": input_text,
            "output": output_json
        })

    # Save to JSONL
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    with open(output_path, 'w') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')
            
    print(f"Generated {num_samples} training examples at {output_path}")

if __name__ == "__main__":
    generate_dataset()
