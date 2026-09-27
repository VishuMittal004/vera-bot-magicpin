from typing import Dict, Any, Optional
import uuid
from app.llm.composer import compose_message

def handle_customer_trigger(category: Dict[str, Any], merchant: Dict[str, Any], trigger: Dict[str, Any], customer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    trigger_id = trigger.get("id")
    merchant_id = merchant.get("merchant_id")
    customer_id = customer.get("customer_id")
    
    # Check if we have valid customer
    if not customer:
        return None
        
    # Compose
    result = compose_message(
        category=category,
        merchant=merchant,
        trigger=trigger,
        signal=customer,
        flow_type="customer_outreach"
    )
    
    return {
        "conversation_id": f"conv_{merchant_id}_{customer_id}_{trigger_id}_{uuid.uuid4().hex[:6]}",
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "send_as": "merchant_on_behalf",
        "trigger_id": trigger_id,
        "template_name": f"vera_customer_{trigger.get('kind', 'generic')}_v1",
        "template_params": [customer.get("identity", {}).get("name", ""), merchant.get("identity", {}).get("name", "")],
        "body": result["body"],
        "cta": result["cta"],
        "suppression_key": trigger.get("suppression_key", ""),
        "rationale": result["rationale"]
    }
