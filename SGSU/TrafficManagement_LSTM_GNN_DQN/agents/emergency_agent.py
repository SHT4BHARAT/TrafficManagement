import subprocess
import json
import os

def query_traffic_agent(intersection_state, bitnet_cwd="D:\\BitNet\\BitNet"):
    """
    BitNet Falcon integration for emergency handling and edge cases.
    """
    prompt = f"""You are a traffic signal controller.
State: {json.dumps(intersection_state)}
Respond only in JSON: {{"action": "phase_id", "reason": "brief"}}"""

    # Ensure we run from the BitNet directory
    try:
        result = subprocess.run(
            ["python", "run_inference.py", "--prompt", prompt],
            capture_output=True, 
            text=True,
            cwd=bitnet_cwd,
            timeout=30 # Safety timeout for inference
        )
        # Parse the JSON from stdout
        # Note: Model might output extra text, so we might need a parser to extract JSON block
        output = result.stdout.strip()
        # Find the first { and last }
        start = output.find('{')
        end = output.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = output[start:end]
            return json.loads(json_str)
        else:
            return {"action": "default", "reason": "Failed to parse JSON from BitNet output"}
            
    except Exception as e:
        return {"action": "default", "reason": f"BitNet query failed: {str(e)}"}

if __name__ == "__main__":
    # Example usage
    state = {
        "intersection": "J1",
        "queue": 14,
        "speed_kmh": 8,
        "phase": "NS-Green",
        "emergency_vehicle": False
    }
    print(f"Querying BitNet for state: {state}")
    # action = query_traffic_agent(state)
    # print(action)
    print("BitNet Integration module ready.")
