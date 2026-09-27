from typing import Dict, Any, Optional
import uuid
from app.llm.composer import compose_message

def handle_merchant_trigger(category: Dict[str, Any], merchant: Dict[str, Any], trigger: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # 1. Hydrate the signal based on the trigger kind
    trigger_kind = trigger.get("kind", "")
    payload = trigger.get("payload", {})
    
    signal = payload
    
    # Specific hydration logic for complex triggers
    if trigger_kind == "research_digest":
        top_item_id = payload.get("top_item_id")
        digest_items = category.get("digest", [])
        signal = next((item for item in digest_items if isinstance(item, dict) and item.get("id") == top_item_id), payload)
    elif trigger_kind in ["regulation_change", "supply_alert", "cde_opportunity"]:
        # Some triggers rely on external items, if they exist in category digest or similar, we extract them here.
        pass
        
    # 2. Extract merchant specifics
    merchant_name = merchant.get("identity", {}).get("name", "Merchant")
    merchant_id = merchant.get("merchant_id")
    trigger_id = trigger.get("id")
    
    # 3. Call LLM to compose the message
    result = compose_message(
        category=category,
        merchant=merchant,
        trigger=trigger,
        signal=signal,
        flow_type="merchant_outreach"
    )
    
    # 4. Return action
    return {
        "conversation_id": f"conv_{merchant_id}_{trigger_id}_{uuid.uuid4().hex[:6]}",
        "merchant_id": merchant_id,
        "customer_id": None,
        "send_as": "vera",
        "trigger_id": trigger_id,
        "template_name": f"vera_{trigger_kind}_v1",
        "template_params": [merchant_name],
        "body": result["body"],
        "cta": result["cta"],
        "suppression_key": trigger.get("suppression_key", ""),
        "rationale": result["rationale"]
    }
