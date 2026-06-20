from .memory import save_log
import json

def process_decision(decision: dict, system_state: dict, status: str = "SUCCESS"):
    try:
        if not decision:
            return {"status": "failed", "error": "empty decision"}

        # Safely grab the AI's 'reason' and map it to 'reasoning' table column
        action = decision.get("action", "unknown")
        reasoning = decision.get("reason", "No reasoning provided by AI")
        
        # Turn the raw PromQL metric dictionary into a clean string for the log
        incident_summary = json.dumps(system_state)

        save_log(
            incident=incident_summary,
            reasoning=reasoning,
            action=action,
            status=status
        )

        return {"status": "executed"}

    except Exception as e:
        print(f"❌ SQLite Storage Error: {e}")
        return {"status": "failed", "error": str(e)}