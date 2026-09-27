import httpx
import uuid
import sys

BOT_URL = "http://localhost:8080"
MERCHANT_ID = "m_001_drmeera_dentist_delhi"
CONV_ID = f"conv_{uuid.uuid4().hex[:8]}"

def setup_context():
    print("[System] Pushing merchant and category context to the brain...")
    # Push category
    httpx.post(f"{BOT_URL}/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": {
            "slug": "dentists", 
            "voice": {"tone": "clinical, professional, helpful", "rules": ["No hype"]}, 
            "digest": [{"id": "d_1", "title": "70% of local patients are overdue for teeth cleaning."}]
        },
        "delivered_at": "2026-04-26T10:00:00Z"
    }, timeout=60.0)
    # Push merchant
    httpx.post(f"{BOT_URL}/v1/context", json={
        "scope": "merchant", "context_id": MERCHANT_ID, "version": 1,
        "payload": {
            "merchant_id": MERCHANT_ID, 
            "category_slug": "dentists", 
            "identity": {"name": "Dr. Meera's Clinic"},
            "performance": {"weekly_footfall": "down 15%"},
            "signals": []
        },
        "delivered_at": "2026-04-26T10:00:00Z"
    }, timeout=60.0)
    # Push trigger
    httpx.post(f"{BOT_URL}/v1/context", json={
        "scope": "trigger", "context_id": "trg_1", "version": 1,
        "payload": {"id": "trg_1", "merchant_id": MERCHANT_ID, "kind": "research_digest", "payload": {"top_item_id": "d_1"}},
        "delivered_at": "2026-04-26T10:00:00Z"
    }, timeout=60.0)

def start_chat():
    try:
        setup_context()
    except Exception as e:
        print(f"[Error] Couldn't connect to {BOT_URL}. Is Uvicorn running?")
        sys.exit(1)
        
    print("[System] Triggering the AI to initiate conversation...\n")
    resp = httpx.post(f"{BOT_URL}/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_1"]}, timeout=60.0)
    actions = resp.json().get("actions", [])
    
    if not actions:
        print("[System] Bot didn't take any action.")
        return
        
    first_action = actions[0]
    print(f"[Vera]: {first_action.get('body')}\n")
    
    turn = 1
    while True:
        try:
            user_msg = input("[You / Dr. Meera]: ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if user_msg.strip().lower() in ["quit", "exit"]:
            break
            
        turn += 1
        resp = httpx.post(f"{BOT_URL}/v1/reply", json={
            "conversation_id": CONV_ID,
            "merchant_id": MERCHANT_ID,
            "from_role": "merchant",
            "message": user_msg,
            "received_at": "2026-04-26T10:00:00Z",
            "turn_number": turn
        }, timeout=60.0)
        
        reply_data = resp.json()
        action = reply_data.get("action")
        
        if action == "send":
            print(f"\n[Vera]: {reply_data.get('body')}\n")
        elif action == "wait":
            print(f"\n[System]: Vera is WAITING ({reply_data.get('wait_seconds')}s)\n")
        elif action == "end":
            print(f"\n[System]: Vera ENDED the conversation.\n")
            break

if __name__ == "__main__":
    start_chat()
