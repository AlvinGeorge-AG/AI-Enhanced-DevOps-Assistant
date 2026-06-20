from .memory import save_log

def process_decision(decision):

    try:
        if not decision:
            return {"status": "failed", "error": "empty decision"}

        required = ["incident", "reasoning", "action"]
        for key in required:
            if key not in decision:
                return {"status": "failed", "error": f"missing {key}"}

        save_log(
            incident=decision["incident"],
            reasoning=decision["reasoning"],
            action=decision["action"],
            status="SUCCESS"
        )

        return {"status": "executed"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}