import json
import logging
import re

logger = logging.getLogger(__name__)


def safe_json_parse(raw_text: str, default_value=None):
    """
    Safely parse JSON from raw text with strict error handling.
    
    Args:
        raw_text: Raw text that may contain JSON
        default_value: Value to return if parsing fails
        
    Returns:
        Parsed JSON object or default_value if parsing fails
    """
    if not isinstance(raw_text, str):
        logger.warning(f"Expected string for JSON parsing, got {type(raw_text)}")
        return default_value
    
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e.msg} at line {e.lineno}")
        return default_value


def extract_json_from_text(raw_text: str, default_value=None):
    """
    Attempt to extract JSON object from text containing markdown code blocks or other formatting.
    
    Args:
        raw_text: Text that may contain JSON with markdown formatting
        default_value: Value to return if extraction/parsing fails
        
    Returns:
        Parsed JSON object or default_value if extraction fails
    """
    if not isinstance(raw_text, str):
        return default_value
    
    # Try direct parsing first
    result = safe_json_parse(raw_text, None)
    if result is not None:
        return result
    
    # Try extracting from markdown code blocks ```json {...} ```
    if "```" in raw_text:
        # Find first { and last }
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        
        if start >= 0 and end > start:
            json_candidate = raw_text[start:end]
            result = safe_json_parse(json_candidate, None)
            if result is not None:
                return result
    
    logger.warning(f"Could not extract valid JSON from text: {raw_text[:100]}...")
    return default_value


def detect_emergency_zone(query_text: str, default_zone: str = "E") -> str:
    """
    Detect emergency zone from query text using word boundary matching.
    
    Args:
        query_text: User query text
        default_zone: Default zone if none detected
        
    Returns:
        Zone code: "N", "S", "E", "W"
    """
    if not isinstance(query_text, str):
        return default_zone
    
    low_query = query_text.lower()
    zone_map = {"north": "N", "south": "S", "east": "E", "west": "W"}
    
    # Use word boundaries to avoid false positives
    for keyword, code in zone_map.items():
        if re.search(rf'\b{keyword}\b', low_query):
            return code
    
    return default_zone
