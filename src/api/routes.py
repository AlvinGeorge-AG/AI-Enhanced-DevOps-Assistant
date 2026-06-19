# The /webhook endpoint FastAPI/Flask code
from fastapi import APIRouter, Request
from api.context_builder import ContextBuilder  # <--- UPDATED IMPORT
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine

router = APIRouter()
context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()

@router.post("/webhook")
async def receive_alert(request: Request):
    payload = await request.json()
    
    print("\n" + "="*50)
    print("🚨 ALERT RECEIVED FROM ALERTMANAGER! 🚨")
    
    print("🔍 Context Builder: Fetching current system metrics from Prometheus...")
    system_state = await context_builder.get_system_state()
    
    print("\n📊 CURRENT SYSTEM STATE:")
    for metric, value in system_state.items():
        print(f"   - {metric}: {value}")

    print("\n🧠 Brain: Asking Groq for a decision...")
    raw_decision = await llm_client.get_decision(system_state)
    print(f"   - Raw LLM decision: {raw_decision}")

    safe_decision = validate_decision(raw_decision, system_state)
    if safe_decision is not raw_decision:
        print(f"   - ⚠️ Safety Engine overrode the decision: {safe_decision}")
    else:
        print(f"   - ✅ Safety Engine approved the decision.")

    print(f"\n⚡ Executor: Carrying out '{safe_decision['action']}'...")
    action_engine.execute(safe_decision)
    print("="*50 + "\n")
    
    return {
        "status": "success",
        "message": "Alert processed.",
        "system_state": system_state,
        "decision": safe_decision,
    }