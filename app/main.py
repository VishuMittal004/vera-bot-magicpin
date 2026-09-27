import time
from datetime import datetime, timezone
from fastapi import FastAPI
from app.core.schema import CtxBody, TickBody, ReplyBody, TickResponse, ReplyActionResponse
from app.core.context_store import upsert_context, get_counts, get_context

app = FastAPI(title="Vera Bot")
START = time.time()

conversations: dict[str, list] = {}

@app.get("/v1/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START),
        "contexts_loaded": get_counts()
    }

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Vipanshu Mittal",
        "team_members": ["Vipanshu"],
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "approach": "Deterministic router + LLM composer",
        "contact_email": "vipanshumittal@gmail.com",
        "version": "0.1.0",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/v1/context")
async def push_context(body: CtxBody):
    accepted, result, cur_version = upsert_context(body.scope, body.context_id, body.version, body.payload)
    if not accepted:
        return {"accepted": False, "reason": result, "current_version": cur_version}
    
    return {
        "accepted": True,
        "ack_id": result,
        "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

@app.post("/v1/tick")
async def tick(body: TickBody):
    from app.engine.signal_ranker import rank_and_select_triggers
    
    actions = []
    
    active_triggers = []
    for trg_id in body.available_triggers:
        trg = get_context("trigger", trg_id)
        if trg:
            active_triggers.append(trg)
            
    best_triggers = rank_and_select_triggers(active_triggers)
    
    for merchant_id, trg in best_triggers.items():
        merchant = get_context("merchant", merchant_id)
        if not merchant:
            continue
            
        category = get_context("category", merchant.get("category_slug"))
        if not category:
            continue
            
        action = None
        if trg.get("scope") == "customer":
            customer = get_context("customer", trg.get("customer_id"))
            if customer:
                from app.engine.customer_flow import handle_customer_trigger
                action = handle_customer_trigger(category, merchant, trg, customer)
        else:
            from app.engine.merchant_flow import handle_merchant_trigger
            action = handle_merchant_trigger(category, merchant, trg)
            
        if action:
            actions.append(action)
            
            # Save the initial message to history
            conv_id = action.get("conversation_id")
            if conv_id:
                history = conversations.setdefault(conv_id, [])
                history.append({"from": "vera", "msg": action["body"]})
                
    return {"actions": actions}

@app.post("/v1/reply")
async def reply(body: ReplyBody):
    history = conversations.setdefault(body.conversation_id, [])
    history.append({"from": body.from_role, "msg": body.message})
    
    from app.core.state_machine import detect_auto_reply, classify_intent
    
    # 1. Auto-reply detection
    if detect_auto_reply(body.message):
        return {
            "action": "end",
            "rationale": "Detected 3 identical messages, likely an auto-reply. Exiting gracefully."
        }
        
    # 2. Intent classification
    intent = classify_intent(body.message)
    
    already_committed = any("Done. I am proceeding" in turn["msg"] for turn in history if turn.get("from") == "vera")
    
    if intent == "COMMITTED" and already_committed:
        intent = "UNKNOWN" # Let the LLM handle polite sign-offs instead of re-triggering action
    
    if intent == "STOP":
        return {
            "action": "end",
            "rationale": "Merchant explicitly requested to stop or is not interested."
        }
    
    if intent == "COMMITTED":
        return {
            "action": "send",
            "body": "Done. I am proceeding to get this setup for you right away.",
            "cta": "none",
            "rationale": "Merchant committed. Moving straight to action without further qualifying."
        }
        
    # Default fallback for UNKNOWN or ASKING_INFO
    from app.llm.composer import compose_conversational_reply
    
    merchant = get_context("merchant", body.merchant_id) if body.merchant_id else {}
    category = get_context("category", merchant.get("category_slug", "")) if merchant else {}
    
    try:
        reply_data = compose_conversational_reply(merchant, category, history)
        history.append({"from": "vera", "msg": reply_data["body"]})
        return {
            "action": "send",
            "body": reply_data["body"],
            "cta": reply_data.get("cta", "none"),
            "rationale": reply_data.get("rationale", "Conversational fallback.")
        }
    except Exception as e:
        return {
            "action": "wait",
            "wait_seconds": 3600,
            "rationale": f"Uncertain intent and LLM failed. Waiting."
        }
