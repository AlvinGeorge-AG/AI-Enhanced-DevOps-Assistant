# This is the last line of defense before a decision reaches the executor
# and actually touches running infrastructure. Nothing here calls an LLM;
# everything is plain, deterministic Python so it's easy to reason about
# and impossible for a bad model output to talk its way around.

VALID_ACTIONS = {"scale_up", "scale_down", "restart_container", "no_action"}

# Below this confidence, we don't trust the decision enough to act on it.
CONFIDENCE_THRESHOLD = 0.6

MIN_REPLICAS = 1
MAX_REPLICAS = 5

# Metric thresholds used for the sanity check below. These are intentionally
# generous/simple; the goal isn't to replace the LLM's judgment, just to
# catch decisions that are obviously contradicted by the numbers.
HIGH_CPU_THRESHOLD = 70.0
LOW_CPU_THRESHOLD = 20.0
HIGH_ERROR_RATE_THRESHOLD = 5.0


def _safe_decision(reason: str) -> dict:
    """Helper for building a forced no_action response, always with
    confidence 0.0 so it's obvious downstream (e.g. in memory/logs) that
    this didn't come from the LLM's own judgment."""
    return {
        "action": "no_action",
        "reason": reason,
        "confidence": 0.0,
    }


def validate_decision(decision: dict, system_state: dict) -> dict:
    """Validates an LLM decision against structural rules, a confidence
    threshold, and the actual system metrics. Returns either the original
    decision (if it passes every check) or a safe "no_action" fallback.

    This function never raises. Anything malformed or out of bounds is
    treated as a failed check, not a crash.
    """

    # --- 1. Structural validation -----------------------------------
    if not isinstance(decision, dict):
        return _safe_decision("Rejected: decision was not a JSON object.")

    action = decision.get("action")
    reason = decision.get("reason")
    confidence = decision.get("confidence")

    if action not in VALID_ACTIONS:
        return _safe_decision(f"Rejected: '{action}' is not a recognized action.")

    if not isinstance(reason, str) or not reason.strip():
        return _safe_decision("Rejected: decision is missing a valid reason.")

    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return _safe_decision("Rejected: confidence score missing or out of range.")

    # --- 2. Confidence threshold --------------------------------------
    if confidence < CONFIDENCE_THRESHOLD:
        return _safe_decision(
            f"Rejected: confidence {confidence} below threshold {CONFIDENCE_THRESHOLD}. "
            f"Original reasoning was: {reason}"
        )

    # --- 3. Replica count guardrails -----------------------------------
    # action_engine.py already protects against going below 1 or above 5,
    # but we check here too so a bad decision never even reaches that code,
    # and so the rejection reason is clear in logs/memory.
    active_replicas = system_state.get("active_replicas")
    if isinstance(active_replicas, (int, float)):
        if action == "scale_down" and active_replicas <= MIN_REPLICAS:
            return _safe_decision(
                f"Rejected: cannot scale_down, already at minimum replicas ({active_replicas})."
            )
        if action == "scale_up" and active_replicas >= MAX_REPLICAS:
            return _safe_decision(
                f"Rejected: cannot scale_up, already at maximum replicas ({active_replicas})."
            )

    # --- 4. Metrics sanity check ----------------------------------------
    # Cross-check the decision against the actual numbers so the LLM can't
    # talk itself into an action the metrics don't support.
    cpu = system_state.get("cpu_usage_percent")
    error_rate = system_state.get("error_rate_percent")

    if action == "scale_up" and isinstance(cpu, (int, float)) and isinstance(error_rate, (int, float)):
        if cpu < HIGH_CPU_THRESHOLD and error_rate < HIGH_ERROR_RATE_THRESHOLD:
            return _safe_decision(
                f"Rejected: scale_up requested but metrics look healthy "
                f"(cpu={cpu}%, error_rate={error_rate}%). Overriding LLM decision."
            )

    if action == "scale_down" and isinstance(cpu, (int, float)):
        if cpu > LOW_CPU_THRESHOLD:
            return _safe_decision(
                f"Rejected: scale_down requested but CPU usage ({cpu}%) is not low enough "
                f"to justify removing a replica. Overriding LLM decision."
            )

    # Passed every check; the original decision is allowed through unchanged.
    return decision