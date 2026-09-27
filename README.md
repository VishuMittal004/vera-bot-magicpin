# Vera Bot: Deterministic Core + Conversational LLM Composer

This repository implements the `compose()` decision engine for magicpin's Vera AI.

## Architecture Overview
Instead of feeding raw payloads into a single black-box LLM prompt to make all decisions, this solution implements a Hybrid Deterministic Router + LLM Composer pattern. This guarantees compliance with strict challenge rules (no fake claims, single CTAs) while allowing fluid, conversational fallbacks.

## Key Design Decisions & Scenarios

### 1. Deterministic State & Idempotency
- **Strict Version Control (/v1/context)**: Context pushes are handled strictly. Re-pushing an identical version acts as a safe no-op (returning accepted: True), while stale versions are correctly rejected. 
- **Trigger Ranking**: When multiple triggers arrive simultaneously, the `SignalRanker` evaluates trigger urgency to programmatically select the single highest-value signal, preventing merchant spam.
- **Universal Trigger Engine**: The engine dynamically hydrates payloads for all 25 dataset triggers (e.g., regulation changes, performance dips, festival events) passing exact, verifiable metrics into the composer.

### 2. The Conversational State Machine (/v1/reply)
The Python-based state machine intercepts merchant replies before they reach the LLM to guarantee safety:
- **Auto-Reply Protection**: Identical messages from a merchant (e.g., WhatsApp out-of-office auto-responders) are tracked via an MD5 hashing mechanism. If the exact same string arrives 3 times, the bot immediately executes a safe `end` action to prevent looping.
- **Intent Handoff**: The deterministic engine uses regular expressions to catch explicit "STOP" or "COMMITTED" intents. If a merchant replies "Yes", the Python script immediately issues a hardcoded confirmation ("Done. I am proceeding...") to initiate human handoff without risking LLM hallucinations.
- **Double-Commit Prevention**: The system maintains an in-memory conversation history per session. If a merchant says "Yes", the bot commits. If the merchant subsequently replies "Ok thanks", the state machine checks the history. Detecting that a commit already occurred in this session, it safely downgrades the intent from COMMITTED to UNKNOWN, preventing robotic, repetitive confirmations and passing the message to the LLM for a polite sign-off.

### 3. The LLM Composer
When the deterministic engine identifies an unknown intent, or when it needs to draft an initial outbound hook, it relies on the LLM Composer.
- **Model Choice**: `nvidia/nemotron-3-ultra-550b-a55b:free` (via OpenRouter) was selected for its exceptional contextual adherence and instruction-following capabilities.
- **Structured JSON Output**: All prompts enforce strict JSON formatting. This ensures the output always perfectly matches the API schema required by the magicpin judge harness.
- **Conversational Memory**: For off-topic or informational questions (intent: ASKING_INFO or UNKNOWN), the state machine passes the complete conversation history to the LLM. The LLM is strictly prompted to address the merchant politely, avoid inventing fake pricing or timelines, and gently steer the conversation back to the primary Call-To-Action.

## Setup and Running

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

2. Set the API key environment variable (used by OpenRouter):
```bash
# Windows PowerShell:
$env:OPENROUTER_API_KEY="sk-or-v1-..."
# Mac/Linux:
# export OPENROUTER_API_KEY="sk-or-v1-..."
```

3. Run the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

4. Testing against the Judge Simulator:
With the server running, execute the magicpin `judge_simulator.py` script in a separate terminal. Ensure your LLM provider and URL are correctly configured in the simulator script.

5. Manual Chat CLI Testing:
To test the conversational flow manually, run:
```bash
python chat_cli.py
```
This script pushes mock context to the server, triggers the initial outreach, and provides an interactive terminal prompt to chat with the bot. Note that the script utilizes a 60-second timeout to allow the LLM ample time to compose responses.
