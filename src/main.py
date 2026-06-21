from fastapi import FastAPI
from api.routes import router
from apscheduler.schedulers.background import BackgroundScheduler
from api.context_builder import ContextBuilder 
from api.mutation_lock import mutation_guard
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine
from executor.memory import init_db, save_log
import asyncio
from datetime import datetime, timedelta

app = FastAPI(title="SentinelAI Core API")
app.include_router(router)

context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()

def scheduled_health_check():
    print("\n⏰ CRON: Running routine system health check...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with mutation_guard():
        state = loop.run_until_complete(context_builder.get_system_state())

        # Yield to Alertmanager when any alert is pending or firing.
        if state.get("active_alerts", 0.0) > 0:
            print("⏳ CRON: Alertmanager is actively cooking/firing a trauma alert. Yielding floor to prevent race condition.\n")
            return

        print(f"📊 ROUTINE STATE: {state}\n")
        raw_decision = loop.run_until_complete(llm_client.get_decision(state))
        safe_decision = validate_decision(raw_decision, state, source="cron")

        if safe_decision["action"] != "no_action":
            print(f"⚡ CRON: Executing '{safe_decision['action']}'...")
            action_engine.execute(safe_decision)
            save_log(
                incident="Routine CRON health check",
                reasoning=safe_decision.get("reason", ""),
                action=safe_decision["action"],
                status="executed",
            )
        else:
            print(f"✅ CRON: No action needed. ({safe_decision['reason']})")
            save_log(
                incident="Routine CRON health check",
                reasoning=safe_decision.get("reason", ""),
                action="no_action",
                status="skipped",
            )

@app.on_event("startup")
def start_scheduler():
    init_db()
    scheduler = BackgroundScheduler()
    first_run = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(scheduled_health_check, 'interval', minutes=3, next_run_time=first_run)
    scheduler.start()
    print(f"🚀 Scheduler started. First CRON tick in ~10 seconds (at {first_run.strftime('%H:%M:%S')})...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)