import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "contexts_loaded" in data
    assert data["contexts_loaded"]["category"] == 0

def test_metadata():
    response = client.get("/v1/metadata")
    assert response.status_code == 200
    assert "team_name" in response.json()

def test_context_push_idempotency():
    # Push initial context
    payload_v1 = {
        "scope": "merchant",
        "context_id": "m_test",
        "version": 1,
        "payload": {"name": "Test Merchant"},
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    r1 = client.post("/v1/context", json=payload_v1)
    assert r1.status_code == 200
    assert r1.json()["accepted"] is True

    # Push same version again (idempotent no-op)
    r2 = client.post("/v1/context", json=payload_v1)
    assert r2.status_code == 200
    assert r2.json()["accepted"] is True
    assert "ack" in r2.json()["ack_id"]

    # Push newer version (accepted)
    payload_v2 = payload_v1.copy()
    payload_v2["version"] = 2
    r3 = client.post("/v1/context", json=payload_v2)
    assert r3.status_code == 200
    assert r3.json()["accepted"] is True

    # Healthz should show 1 merchant loaded
    r_health = client.get("/v1/healthz")
    assert r_health.json()["contexts_loaded"]["merchant"] == 1

def test_tick_research_digest():
    # Push category
    client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": {"slug": "dentists", "digest": [{"id": "d_2026W17_jida", "title": "Test Title"}]},
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    # Push merchant
    client.post("/v1/context", json={
        "scope": "merchant", "context_id": "m_test_2", "version": 1,
        "payload": {"merchant_id": "m_test_2", "category_slug": "dentists", "identity": {"name": "Test Clinic"}},
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    # Push trigger
    client.post("/v1/context", json={
        "scope": "trigger", "context_id": "trg_1", "version": 1,
        "payload": {"id": "trg_1", "merchant_id": "m_test_2", "kind": "research_digest", "payload": {"top_item_id": "d_2026W17_jida"}},
        "delivered_at": "2026-04-26T10:00:00Z"
    })

    # Trigger tick
    resp = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_1"]})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["merchant_id"] == "m_test_2"
    assert "Test Clinic" in action["body"]
    assert "Test Title" in action["body"]

def test_reply_auto_reply_hell():
    base_reply = {
        "conversation_id": "conv_auto",
        "merchant_id": "m_test",
        "from_role": "merchant",
        "message": "Thank you for contacting us. We will get back to you.",
        "received_at": "2026-04-26T10:00:00Z",
        "turn_number": 1
    }
    
    # 1st reply -> wait
    r1 = client.post("/v1/reply", json=base_reply)
    assert r1.json()["action"] == "wait"
    
    # 2nd reply -> wait
    base_reply["turn_number"] = 2
    r2 = client.post("/v1/reply", json=base_reply)
    assert r2.json()["action"] == "wait"
    
    # 3rd identical reply -> end
    base_reply["turn_number"] = 3
    r3 = client.post("/v1/reply", json=base_reply)
    assert r3.json()["action"] == "end"
    assert "auto-reply" in r3.json()["rationale"]

def test_reply_intent_committed():
    r = client.post("/v1/reply", json={
        "conversation_id": "conv_intent",
        "merchant_id": "m_test",
        "from_role": "merchant",
        "message": "ok let's do it",
        "received_at": "2026-04-26T10:00:00Z",
        "turn_number": 1
    })
    assert r.json()["action"] == "send"
    assert r.json()["cta"] == "none"

def test_reply_intent_hostile():
    r = client.post("/v1/reply", json={
        "conversation_id": "conv_hostile",
        "merchant_id": "m_test",
        "from_role": "merchant",
        "message": "stop messaging me",
        "received_at": "2026-04-26T10:00:00Z",
        "turn_number": 1
    })
    assert r.json()["action"] == "end"
