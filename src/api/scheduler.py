import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from api.context_builder import ContextBuilder 
from api.mutation_lock import mutation_guard
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine
from executor.memory import init_db, save_log
from api.log_formatter import (
    console,
    log_system_state,
    log_emergency_override,
    log_safety_rejection,
    log_action_executed,
    log_routine_stable
)

context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()

def scheduled_health_check():
    console.print("\n  CRON: Running routine system health check...", style="bold white")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with mutation_guard():
        state = loop.run_until_complete(context_builder.get_system_state())

        # Yield to Alertmanager when any alert is pending or firing.
        if state.get("active_alerts", 0.0) > 0:
            log_safety_rejection(
                "Alertmanager is actively firing a trauma alert. "
                "Yielding floor to prevent race condition."
            )
            return

        log_system_state(state, title="ROUTINE STATE")
        raw_decision = loop.run_until_complete(llm_client.get_decision(state))
        safe_decision = validate_decision(raw_decision, state, source="cron")

        # Distinguish Rule 0 / emergency overrides from routine rejections
        if safe_decision is not raw_decision:
            reason = safe_decision.get("reason", "")
            if reason.startswith("SAFETY OVERRIDE:"):
                log_emergency_override(reason)
            else:
                log_safety_rejection(reason)

        if safe_decision["action"] != "no_action":
            log_action_executed(safe_decision["action"], safe_decision.get("reason", ""))
            action_engine.execute(safe_decision)
            save_log(
                incident="Routine CRON health check",
                reasoning=safe_decision.get("reason", ""),
                action=safe_decision["action"],
                status="executed",
            )
        else:
            log_routine_stable(safe_decision["reason"])
            save_log(
                incident="Routine CRON health check",
                reasoning=safe_decision.get("reason", ""),
                action="no_action",
                status="skipped",
            )

def start_scheduler() -> BackgroundScheduler:
    init_db()
    scheduler = BackgroundScheduler()
    first_run = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(scheduled_health_check, 'interval', minutes=1, next_run_time=first_run)
    scheduler.start()
    console.print(
        f"\n  Scheduler started. First CRON tick in ~10 seconds "
        f"(at {first_run.strftime('%H:%M:%S')})...",
        style="bold green",
    )
    return scheduler
