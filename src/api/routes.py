from fastapi import APIRouter, Request
from pydantic import BaseModel
from api.context_builder import ContextBuilder  
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine

router = APIRouter()
context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()

# --- Pydantic Models for Rohan's Frontend Payload ---
class ChatRequest(BaseModel):
    message: str

class ExecuteRequest(BaseModel):
    action: str
    description: str = "Triggered manually via Copilot UI button"


@router.get("/")
def startup():
    return "THE CORE API SERVER RUNNING SUCCESSFULLY!"

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


    if safe_decision["action"] != "no_action":
        print(f"\n⚡ Executor: Carrying out '{safe_decision['action']}'...")
        action_engine.execute(safe_decision)
        
    print("="*50 + "\n")
    return {
        "status": "success",
        "message": "Alert processed.",
        "system_state": system_state,
        "decision": safe_decision,
    }


@router.post("/chat")
async def copilot_chat(payload: ChatRequest):
    print(f"\nCHAT INQUIRY: '{payload.message}'")
    
    # Harvest fresh Prometheus metrics & SQLite history
    system_state = await context_builder.get_system_state()
    
    # Inject the developer's chat question so prompts.py sees it
    system_state["user_chat_message"] = payload.message
    
    # Get Groq LLM diagnosis answering the developer
    raw_decision = await llm_client.get_decision(system_state)
    safe_decision = validate_decision(raw_decision, system_state)
    
    return {
        "status": "success",
        "message": "Diagnosis complete.",
        "system_state": system_state,
        "decision": safe_decision
    }



@router.post("/execute")
async def copilot_execute(payload: ExecuteRequest):
    print(f"\n⚡ COPILOT MANUAL COMMAND: '{payload.action}' ({payload.description})")
    
    # Build the decision object directly from human input (No LLM needed!)
    human_decision = {
        "action": payload.action,
        "reason": f"Manual Override from UI: {payload.description}",
        "confidence": 1.0  # 100% Human Confidence
    }
    
    # Execute immediately (action_engine.py already enforces min 1 / max 5 replicas)
    if payload.action != "no_action":
        action_engine.execute(human_decision)
        
    # Harvest fresh telemetry POST-execution so Rohan's UI updates instantly!
    fresh_state = await context_builder.get_system_state()

    return {
        "status": "success",
        "message": f"Action '{payload.action}' executed successfully.",
        "system_state": fresh_state,
        "decision": human_decision
    }