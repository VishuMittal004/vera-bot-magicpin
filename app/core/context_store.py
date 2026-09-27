from typing import Dict, Any, Tuple, Optional

# In-memory store (scope, context_id) -> {"version": int, "payload": dict}
contexts: Dict[Tuple[str, str], Dict[str, Any]] = {}

def upsert_context(scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
    """
    Returns (accepted: bool, reason/ack: str, current_version: int | None)
    """
    key = (scope, context_id)
    cur = contexts.get(key)
    if cur:
        if cur["version"] > version:
            return False, "stale_version", cur["version"]
        if cur["version"] == version:
            return True, f"ack_{context_id}_v{version}", cur["version"]
    
    contexts[key] = {"version": version, "payload": payload}
    return True, f"ack_{context_id}_v{version}", None

def get_context(scope: str, context_id: str) -> Optional[Dict[str, Any]]:
    cur = contexts.get((scope, context_id))
    if cur:
        return cur["payload"]
    return None

def get_counts() -> Dict[str, int]:
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _), _ in contexts.items():
        if scope in counts:
            counts[scope] += 1
    return counts
