import os
import json
import httpx
from typing import Dict, Any

def compose_message(category: Dict[str, Any], merchant: Dict[str, Any], trigger: Dict[str, Any], signal: Any, flow_type: str) -> Dict[str, str]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    
    # If no API key is provided, return a mock response so tests don't crash
    if not api_key:
        merchant_name = merchant.get("identity", {}).get("name", "Merchant")
        signal_title = signal.get("title", "interesting info") if isinstance(signal, dict) else str(signal)
        return {
            "body": f"Hi {merchant_name}, this is Vera. I found this research: {signal_title}. Want me to draft a WhatsApp message for your patients?",
            "cta": "open_ended",
            "rationale": "Mocked LLM generation due to missing API key."
        }
        
    prompt = f"""
Write a WhatsApp message from Vera to the merchant.

Category: {category.get('slug')}
Voice Profile: {json.dumps(category.get('voice', {}))}

Merchant Name: {merchant.get('identity', {}).get('name')}
Performance: {json.dumps(merchant.get('performance', {}))}
Signals: {json.dumps(merchant.get('signals', []))}

Trigger: {trigger.get('kind')}
Key Signal: {json.dumps(signal)}

Rules:
1. Be specific, use verifiable numbers from the signal.
2. Do NOT use promotional 'hype' words if category voice forbids it.
3. Match the language preference (usually Hindi-English mix).
4. Provide ONE clear call to action.
5. KEEP IT EXTREMELY BRIEF. Under 3 sentences. Be punchy and concise for WhatsApp.

RESPOND ONLY WITH VALID JSON using this exact schema:
{{
  "body": "The WhatsApp message body. Concise, verifiable, engaging.",
  "cta": "The primary call to action (e.g. 'open_ended', 'YES_NO', 'none')",
  "rationale": "Why this specific message was drafted and what compulsion levers it uses."
}}
"""
    
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        },
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8080"
        },
        timeout=30.0
    )
    
    if response.status_code != 200:
        return {
            "body": f"Hi {merchant.get('identity', {}).get('name')}, we found a new signal for you. Please check your dashboard.",
            "cta": "none",
            "rationale": f"LLM failed with status {response.status_code}: {response.text}"
        }
        
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    
    # Strip markdown if present
    content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "body": f"Hi {merchant.get('identity', {}).get('name')}, we found a new signal for you. Please check your dashboard.",
            "cta": "none",
            "rationale": "LLM returned invalid JSON."
        }

def compose_conversational_reply(merchant: Dict[str, Any], category: Dict[str, Any], history: list) -> Dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    
    sys_prompt = (
        "You are Vera, an AI assistant for magicpin. "
        "The merchant has asked a question or given an off-topic response to your previous message.\n"
        "Your goal is to:\n"
        "1. Briefly and politely address their response. If you don't know the exact answer, be transparent.\n"
        "2. Do NOT invent fake pricing, fake features, or fake facts. No fake claims.\n"
        "3. Gently steer the conversation back to your original Call to Action (e.g. asking them to reply YES to proceed).\n"
        "4. KEEP IT EXTREMELY BRIEF. This is a WhatsApp chat. Your reply must be under 3 sentences.\n"
        "5. NEVER ask for more than one piece of information at a time. Do NOT provide lists of options.\n\n"
        "Respond in JSON format with strictly two keys: 'body' (the message to send) and 'rationale' (brief explanation of your handling)."
    )
    
    messages = [{"role": "system", "content": sys_prompt}]
    
    merchant_name = merchant.get("identity", {}).get("name", "Merchant")
    messages.append({"role": "system", "content": f"You are talking to {merchant_name}. Maintain a professional and helpful tone fitting the {category.get('slug', '')} category."})
    
    for turn in history:
        role = "assistant" if turn.get("from") == "vera" else "user"
        messages.append({"role": role, "content": turn.get("msg", "")})
        
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "messages": messages,
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8080"
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        content = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"LLM Error in fallback: {e}")
        return {
            "body": "I'll have a campaign specialist reach out to explain the exact details. In the meantime, would you like me to tentatively queue this up? Reply YES or NO.",
            "rationale": "Fallback response due to LLM error."
        }
