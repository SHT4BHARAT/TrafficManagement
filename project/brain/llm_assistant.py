import time
import requests
import json
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.utils import safe_json_parse, extract_json_from_text

logger = logging.getLogger(__name__)

# Import TomTom scraper at module level with graceful fallback
TomTomDelhiScraper = None
try:
    from edge.tomtom_scraper import TomTomDelhiScraper
except ImportError:
    logger.warning("[LLM] TomTom scraper not available. Regional context will be skipped.")

class HQAssistantLLM:
    """
    Real-time Air-Gapped HQ Assistant connecting to local Ollama.
    Handles natural language queries about the traffic system state.
    Uses RAG (Retrieval-Augmented Generation) to ground the LLM in live data.
    """
    def __init__(self, model_name="TrafficAgent", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{self.base_url}/api/generate"
        print(f"[LLM] Initialized for local Ollama: {self.model_name}")

    def mock_retrieval(self, query):
        """
        Simulates searching a Vector DB for historical patterns.
        """
        knowledge_base = {
            "bottleneck": "Historical data shows a 25% increase in North-bound traffic on Mondays between 8-10 AM.",
            "emergency": "Green Corridor protocols prioritize ambulances within 500m of the intersection.",
            "failure": "Hardware watchdog triggers local sequencing if the central heartbeat is lost for 10s."
        }
        
        for key in knowledge_base:
            if key in query.lower():
                return knowledge_base[key]
        return "Standard traffic patterns apply."

    def _local_fallback_inference(self, live_state: dict) -> dict:
        """
        Compute a duration recommendation locally when Ollama is unavailable.
        Uses queue depth + VPS to estimate optimal green time (no model needed).
        """
        phase = live_state.get("phase", "N-S")
        vps = live_state.get("vps", {})
        queues = live_state.get("queues", {})

        # Determine which lanes are in this phase
        if "N" in phase or "S" in phase:
            lanes = ["N", "S"]
        else:
            lanes = ["E", "W"]

        total_queue = sum(queues.get(l, 0) for l in lanes)
        avg_vps = sum(vps.get(l, 10) for l in lanes) / max(1, len(lanes))

        # Simple heuristic: base 20s + 1s per queued vehicle, scaled by arrival rate
        duration = int(20 + total_queue * 1.0 + avg_vps * 0.3)
        duration = max(10, min(60, duration))

        return {
            "duration": duration,
            "reasoning": f"Local fallback (Ollama offline): queue={total_queue} veh, avg_vps={avg_vps:.0f} → {duration}s recommended.",
            "status": "fallback"
        }

    def query_system(self, user_query, live_state=None):
        """
        Sends a RAG-augmented prompt to the local Ollama instance.
        """
        # 1. Gather context from internal history
        history = self.mock_retrieval(user_query)
        
        # 2. Extract real-world stats if available (Phase 7 Integration)
        regional_stats = ""
        if TomTomDelhiScraper is not None:
            try:
                scraper = TomTomDelhiScraper()
                stats = scraper.fetch_live_stats()
                if stats:
                    regional_stats = f"Regional Context (New Delhi): {stats['status']} at {stats['live_speed']}. Time lost: {stats['time_lost_per_10km']}."
                else:
                    regional_stats = "Regional Context: Live Delhi data unavailable."
            except Exception as e:
                logger.warning(f"[LLM] TomTom fetch failed: {e}")
                regional_stats = "Regional Context: Live Delhi data unavailable."
        else:
            regional_stats = "Regional Context: TomTom scraper not available."

        # 3. Construct the prompt (your fine-tuned SLM returns JSON; we pass context only)
        prompt = f"""
        [SYSTEM CONTEXT]
        You are the DAITFO Smart City Traffic Assistant. 
        {regional_stats}
        Live Intersection State: {live_state or 'No live junction data available'}
        Historical Patterns: {history}

        [USER QUERY]
        {user_query}

        [INSTRUCTIONS]
        Respond with a single JSON object only (you are fine-tuned for this format).
        Reference the live state and regional context. If there is congestion, explain and recommend signal adjustments.
        """

        print(f"[LLM] Querying Ollama ({self.model_name})...")
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(self.api_url, json=payload, timeout=180)
            
            if response.status_code == 200:
                raw = response.json().get('response', "").strip()
                if not raw:
                    return json.dumps({"answer": "LLM returned an empty response.", "status": "ok"})
                # Your fine-tuned SLM returns JSON; parse with safe extraction
                obj = extract_json_from_text(raw, None)
                if isinstance(obj, dict):
                    return json.dumps(obj)
                # If JSON parsing failed, return the raw response as fallback
                return json.dumps({"answer": raw, "status": "ok"})
            else:
                return json.dumps({"answer": f"LLM Error: HTTP {response.status_code}", "status": "error"})
                
        except requests.exceptions.Timeout:
            fallback = self._local_fallback_inference(live_state or {})
            return json.dumps(fallback)
        except requests.exceptions.ConnectionError:
            fallback = self._local_fallback_inference(live_state or {})
            fallback["answer"] = "Ollama not reachable. Using local heuristic inference."
            return json.dumps(fallback)
        except Exception as e:
            fallback = self._local_fallback_inference(live_state or {})
            fallback["answer"] = f"LLM error: {e}. Using local heuristic."
            return json.dumps(fallback)

if __name__ == "__main__":
    assistant = HQAssistantLLM()
    # Simple test case
    print(f"[LLM] Local Test Response: {assistant.query_system('Why is Lane S congested?')}")
