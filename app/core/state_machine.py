import hashlib
from typing import List, Dict, Any

# Global tracker for message hashes
message_hashes: Dict[str, int] = {}

def detect_auto_reply(conv_id: str, message: str) -> bool:
    """Returns True if this exact message has been seen 3 or more times in this conversation."""
    key = f"{conv_id}_{hashlib.md5(message.encode('utf-8')).hexdigest()}"
    message_hashes[key] = message_hashes.get(key, 0) + 1
    return message_hashes[key] >= 3

def classify_intent(message: str) -> str:
    import re
    """Very basic deterministic intent classifier."""
    msg = message.lower()
    
    stop_words = [r"\bstop\b", r"\bunsubscribe\b", r"not interested", r"\bspam\b", r"\bno\b", r"don't"]
    if any(re.search(w, msg) for w in stop_words):
        return "STOP"
        
    commit_words = [
        r"\byes\b", r"\bok\b", r"let's do it", r"go ahead", r"\bsure\b", r"\bdone\b", r"what's next",
        r"\bha\b", r"\bhaan\b", r"\bhan\b", r"krte h", r"\bchalo\b", r"thik", r"theek", r"karo", r"kar lo"
    ]
    if any(re.search(w, msg) for w in commit_words):
        return "COMMITTED"
        
    if "?" in msg or any(w in msg for w in ["what", "how", "when", "why", "who", "can you"]):
        return "ASKING_INFO"
        
    return "UNKNOWN"
