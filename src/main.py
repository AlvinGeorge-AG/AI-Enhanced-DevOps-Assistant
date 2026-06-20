# The entry point that starts the API and Cron scheduler
from fastapi import FastAPI
from api.routes import router
from apscheduler.schedulers.background import BackgroundScheduler
from api.context_builder import ContextBuilder 
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine
from executor.memory import init_db
from executor.service import process_decision
import asyncio

app = FastAPI(title="SentinelAI Core API")
app.include_router(router)

context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()

def scheduled_health_check():
    print("\n⏰ CRON: Running routine system health check...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    state = loop.run_until_complete(context_builder.get_system_state())
    
    print(f"📊 ROUTINE STATE: {state}\n")

    raw_decision = loop.run_until_complete(llm_client.get_decision(state))
    safe_decision = validate_decision(raw_decision, state)

    if safe_decision is not raw_decision:
        print(f"⚠️ CRON: Safety Engine overrode the decision: {safe_decision}")

    if safe_decision["action"] != "no_action":
        print(f"⚡ CRON: Executing '{safe_decision['action']}'...")
        try:
            action_engine.execute(safe_decision)
            # Log the successful infrastructure change!
            process_decision(safe_decision, state, status="SUCCESS")
        except Exception as e:
            # If Docker fails, record the exact error in the DB
            process_decision(safe_decision, state, status=f"FAILED: {str(e)}")
    else:
        print(f"✅ CRON: No action needed. ({safe_decision['reason']})")
        # Log routine healthy states so the Copilot Chat knows the app was stable here
        process_decision(safe_decision, state, status="ROUTINE_CHECK_STABLE")


@app.on_event("startup")
def startup_events():
    print("📦 Initializing SQLite Memory Database...")
    init_db()  # <--- Balamurali's table gets built here!
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_health_check, 'interval', minutes=3)
    scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)