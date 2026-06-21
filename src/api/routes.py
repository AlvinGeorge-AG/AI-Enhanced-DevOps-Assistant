from fastapi import APIRouter, Request
from pydantic import BaseModel
from api.context_builder import ContextBuilder  
from api.mutation_lock import mutation_guard
from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision
from executor.action_engine import ActionEngine
from executor.memory import save_log
from api.log_formatter import (
    console,
    log_system_state,
    log_decision,
    log_action_executed,
    log_safety_rejection,
    log_emergency_override,
    log_alert_received,
    log_info,
)

router = APIRouter()
context_builder = ContextBuilder()
llm_client = LLMClient()
action_engine = ActionEngine()


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

    # ── Extract alert context from the Alertmanager payload ──────────
    # Alertmanager sends an array of alerts, each with:
    #   status: "firing" | "resolved"
    #   labels: {alertname, severity, ...}
    #   annotations: {summary, ...}
    alerts = payload.get("alerts", [])
    firing_alerts = [a for a in alerts if a.get("status") == "firing"]

    # If every alert in this batch is "resolved", there's nothing to act on.
    # The problem fixed itself before or during Alertmanager's group_wait.
    if not firing_alerts:
        log_info("Alertmanager sent a 'resolved' notification. No action needed.", style="dim")
        return {
            "status": "success",
            "message": "Alert resolved — no action taken.",
            "system_state": {},
            "decision": {"action": "no_action", "reason": "Alert already resolved.", "confidence": 1.0},
        }

    # Build a human-readable summary of what's firing
    alert_names = [a.get("labels", {}).get("alertname", "unknown") for a in firing_alerts]
    alert_summaries = [a.get("annotations", {}).get("summary", "") for a in firing_alerts]
    alert_context = "; ".join(
        f"{name}: {summary}" for name, summary in zip(alert_names, alert_summaries) if summary
    ) or ", ".join(alert_names)

    log_alert_received("ALERTMANAGER")
    console.print(f"  Firing alerts: [bold yellow]{', '.join(alert_names)}[/bold yellow]")

    with mutation_guard():
        log_info("Fetching current system metrics from Prometheus...", style="dim italic")
        system_state = await context_builder.get_system_state()

        # ── Inject alert context so the LLM knows WHY this webhook fired ──
        # Even if metrics have recovered by now, the LLM needs to know that
        # Alertmanager already confirmed a sustained breach (it waited the
        # full `for:` duration before firing). Without this, the LLM sees
        # healthy metrics and says "no_action" — defeating the alert.
        system_state["alert_context"] = (
            f"ALERTMANAGER CONFIRMED FIRING: {alert_context}. "
            f"These alerts passed Alertmanager's sustained-breach window before reaching you. "
            f"Even if current metrics look normal now, the breach was real and recent."
        )

        log_system_state(system_state, title="CURRENT SYSTEM STATE")

        log_info("Requesting LLM decision from Groq...", style="dim italic")

        raw_decision = await llm_client.get_decision(system_state)

        log_decision(raw_decision, source="WEBHOOK")

        safe_decision = validate_decision(raw_decision, system_state, source="webhook")
        
        # Distinguish Rule 0 / emergency overrides from routine rejections
        if safe_decision is not raw_decision:
            reason = safe_decision.get("reason", "")
            if reason.startswith("SAFETY OVERRIDE:"):
                log_emergency_override(reason)
            else:
                log_safety_rejection(reason)
        else:
            console.print("  Safety Engine: [bold green]APPROVED[/bold green]")

        if safe_decision["action"] != "no_action":
            log_action_executed(safe_decision["action"], safe_decision.get("reason", ""))
            action_engine.execute(safe_decision)
            save_log(
                incident=f"Alertmanager webhook: {', '.join(alert_names)}",
                reasoning=safe_decision.get("reason", ""),
                action=safe_decision["action"],
                status="executed",
            )
        else:
            save_log(
                incident=f"Alertmanager webhook: {', '.join(alert_names)}",
                reasoning=safe_decision.get("reason", ""),
                action="no_action",
                status="skipped",
            )

        return {
            "status": "success",
            "message": "Alert processed.",
            "system_state": system_state,
            "decision": safe_decision,
        }


@router.post("/chat")
async def copilot_chat(payload: ChatRequest):
    console.print(f"\n  CHAT INQUIRY: '{payload.message}'", style="bold magenta")
    
    # Harvest fresh Prometheus metrics & SQLite history
    system_state = await context_builder.get_system_state()
    
    # Inject the developer's chat question so prompts.py sees it
    system_state["user_chat_message"] = payload.message
    
    # Get Groq LLM diagnosis answering the developer
    raw_decision = await llm_client.get_decision(system_state)
    safe_decision = validate_decision(raw_decision, system_state, source="chat")

    # Log chat-driven decisions too so history stays complete
    save_log(
        incident=f"Chat inquiry: {payload.message[:120]}",
        reasoning=safe_decision.get("reason", ""),
        action=safe_decision["action"],
        status="executed" if safe_decision["action"] != "no_action" else "skipped",
    )

    return {
        "status": "success",
        "message": "Diagnosis complete.",
        "system_state": system_state,
        "decision": safe_decision
    }



@router.post("/execute")
async def copilot_execute(payload: ExecuteRequest):
    console.print(
        f"\n  COPILOT MANUAL COMMAND: '{payload.action}' ({payload.description})",
        style="bold cyan",
    )
    
    # Build the decision object directly from human input (No LLM needed!)
    human_decision = {
        "action": payload.action,
        "reason": f"Manual Override from UI: {payload.description}",
        "confidence": 1.0  # 100% Human Confidence
    }
    
    # Execute immediately (action_engine.py already enforces min 1 / max 5 replicas)
    if payload.action != "no_action":
        action_engine.execute(human_decision)

    save_log(
        incident="Manual override from Copilot UI",
        reasoning=human_decision.get("reason", ""),
        action=human_decision["action"],
        status="executed" if payload.action != "no_action" else "skipped",
    )

    # Harvest fresh telemetry POST-execution so Rohan's UI updates instantly!
    fresh_state = await context_builder.get_system_state()

    return {
        "status": "success",
        "message": f"Action '{payload.action}' executed successfully.",
        "system_state": fresh_state,
        "decision": human_decision
    }