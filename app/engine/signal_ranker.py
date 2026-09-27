from typing import List, Dict, Any

def rank_and_select_triggers(triggers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict mapping merchant_id to the single best trigger to send.
    """
    merchant_triggers = {}
    
    for trg in triggers:
        # Group by merchant
        m_id = trg.get("merchant_id")
        if not m_id:
            continue
            
        merchant_triggers.setdefault(m_id, []).append(trg)
        
    best_per_merchant = {}
    for m_id, trgs in merchant_triggers.items():
        # Sort by urgency (descending), then source (internal first)
        trgs.sort(key=lambda t: (
            t.get("urgency", 1), 
            1 if t.get("source") == "internal" else 0
        ), reverse=True)
        best_per_merchant[m_id] = trgs[0]
        
    return best_per_merchant
