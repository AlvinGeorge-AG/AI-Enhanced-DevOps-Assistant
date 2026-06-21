# The hardcoded if/else rules to validate AI output.
#
# This is the last line of defense before a decision reaches the executor
# and actually touches running infrastructure. Nothing here calls an LLM;
# everything is plain, deterministic Python so it's easy to reason about
# and impossible for a bad model output to talk its way around.

import time
from api.log_formatter import log_emergency_override

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
HIGH_MEMORY_THRESHOLD = 150.0

# Mirror alert_rules.yml `for:` durations so CRON cannot beat Alertmanager
# by reacting to a single high snapshot before the alert window completes.
BREACH_DURATIONS_SECONDS = {
    "cpu": 15,
    "memory": 60,
    "error_rate": 60,
}

# CPU alert threshold in alert_rules.yml (75%) — used for sustained tracking.
CPU_ALERT_THRESHOLD = 75.0

# --- Cooldown -----------------------------------------------------------
COOLDOWN_SECONDS = 120
_last_action_time = 0.0

# Actions that change infrastructure and therefore need to respect the
# cooldown. "no_action" and rejected/no-op decisions never need to wait.
ACTIONS_REQUIRING_COOLDOWN = {"scale_up", "scale_down", "restart_container"}

# --- Sustained-breach & extinction tracking -----------------------------
_breach_started_at: dict[str, float] = {}
_extinction_since: float | None = None
EXTINCTION_CONFIRM_SECONDS = 15


def _safe_decision(reason: str) -> dict:
    """Helper for building a forced no_action response, always with
    confidence 0.0 so it's obvious downstream (e.g. in memory/logs) that
    this didn't come from the LLM's own judgment."""
    return {
        "action": "no_action",
        "reason": reason,
        "confidence": 0.0,
    }


def _update_breach_timers(system_state: dict) -> None:
    """Track when each metric first crossed its alert threshold."""
    now = time.time()
    checks = {
        "cpu": (
            system_state.get("cpu_usage_percent"),
            CPU_ALERT_THRESHOLD,
        ),
        "memory": (
            system_state.get("memory_usage_mb"),
            HIGH_MEMORY_THRESHOLD,
        ),
        "error_rate": (
            system_state.get("error_rate_percent"),
            HIGH_ERROR_RATE_THRESHOLD,
        ),
    }

    for metric, (value, threshold) in checks.items():
        if isinstance(value, (int, float)) and value > threshold:
            _breach_started_at.setdefault(metric, now)
        else:
            _breach_started_at.pop(metric, None)


def _breach_sustained(metric: str) -> bool:
    started = _breach_started_at.get(metric)
    if started is None:
        return False
    return (time.time() - started) >= BREACH_DURATIONS_SECONDS[metric]


def _breach_elapsed(metric: str) -> float:
    started = _breach_started_at.get(metric)
    if started is None:
        return 0.0
    return time.time() - started


def validate_decision(decision: dict, system_state: dict, *, source: str = "cron") -> dict:
    """Validates an LLM decision against structural rules, a confidence
    threshold, and the actual system metrics. Returns either the original
    decision (if it passes every check) or a safe "no_action" fallback.

    source:
      - "cron"    — background poll; enforce sustained-breach so CRON cannot
                    beat Alertmanager's `for:` window on a single snapshot.
      - "webhook" — Alertmanager already waited `for:`; skip sustained-breach.
      - "chat"    — interactive UI; skip sustained-breach.

    This function never raises. Anything malformed or out of bounds is
    treated as a failed check, not a crash.
    """

    global _last_action_time

    _update_breach_timers(system_state)

    cpu = system_state.get("cpu_usage_percent")
    memory = system_state.get("memory_usage_mb")
    error_rate = system_state.get("error_rate_percent")
    replicas = system_state.get("active_replicas")

    # =========================================================================
    # RULE 0: THE DEFIBRILLATOR (TOTAL EXTINCTION OVERRIDE)
    # =========================================================================
    global _extinction_since
    if replicas is None:
        _extinction_since = None
    elif isinstance(replicas, (int, float)) and replicas < 1.0:
        now = time.time()
        if _extinction_since is None:
            _extinction_since = now
        if now - _extinction_since >= EXTINCTION_CONFIRM_SECONDS:
            log_emergency_override(
                "TOTAL FLEET EXTINCTION DETECTED!\n"
                "Active container count dropped to 0.\n"
                "Bypassing LLM logic. Forcing immediate emergency cold-boot."
            )
            _extinction_since = None
            return {
                "action": "scale_up",
                "reason": "SAFETY OVERRIDE: Active container count dropped to 0. Executing emergency fleet resurrection.",
                "confidence": 1.0,
            }
        return _safe_decision(
            f"Rejected: active_replicas reads {replicas} — awaiting "
            f"{EXTINCTION_CONFIRM_SECONDS}s confirmation before emergency scale_up "
            f"({now - _extinction_since:.0f}s elapsed, may be a Prometheus SD gap)."
        )
    else:
        _extinction_since = None

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
    if (
        action == "scale_up"
        and isinstance(memory, (int, float))
        and isinstance(cpu, (int, float))
        and isinstance(error_rate, (int, float))
        and memory > HIGH_MEMORY_THRESHOLD
        and cpu < HIGH_CPU_THRESHOLD
        and error_rate < HIGH_ERROR_RATE_THRESHOLD
    ):
        return _safe_decision(
            f"Rejected: scale_up requested but only memory is elevated ({memory}MB). "
            f"Scaling adds replicas that will also leak — use restart_container instead."
        )

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

    # --- 4b. MEMORY LEAK HARD OVERRIDE (LAST LINE OF DEFENSE) -----------
    # If the LLM says "no_action" or "scale_up" but memory is dangerously
    # high with low CPU and low errors, this is a textbook memory leak.
    # The safety engine FORCES restart_container deterministically —
    # just like the extinction detector forces scale_up at 0 replicas.
    if (
        action in ("no_action", "scale_up")
        and isinstance(memory, (int, float))
        and isinstance(cpu, (int, float))
        and isinstance(error_rate, (int, float))
        and memory > HIGH_MEMORY_THRESHOLD
        and cpu < LOW_CPU_THRESHOLD
        and error_rate < HIGH_ERROR_RATE_THRESHOLD
    ):
        log_emergency_override(
            f"MEMORY LEAK DETECTED!\n"
            f"Memory: {memory:.2f}MB (>{HIGH_MEMORY_THRESHOLD}MB threshold)\n"
            f"CPU: {cpu:.2f}% (low -- not genuine load)\n"
            f"Errors: {error_rate:.2f}% (low -- not state corruption)\n"
            f"LLM said '{action}' but this is WRONG for a memory leak.\n"
            f"Overriding to restart_container to reclaim leaked memory."
        )

        # This is a forced action, so we need to check cooldown before forcing
        now = time.time()
        seconds_since_last = now - _last_action_time
        if seconds_since_last < COOLDOWN_SECONDS:
            return _safe_decision(
                f"Memory leak detected (mem={memory}MB, cpu={cpu}%) but cooldown active. "
                f"Last infrastructure change was {seconds_since_last:.0f}s ago; "
                f"must wait {COOLDOWN_SECONDS}s between actions."
            )

        # For cron source, require the memory breach to be sustained
        if source == "cron" and not _breach_sustained("memory"):
            elapsed = _breach_elapsed("memory")
            needed = BREACH_DURATIONS_SECONDS["memory"]
            return _safe_decision(
                f"Memory leak detected (mem={memory}MB) but breach not sustained for {needed}s yet "
                f"({elapsed:.0f}s elapsed). Waiting for confirmation before forced restart."
            )

        _last_action_time = now
        return {
            "action": "restart_container",
            "reason": (
                f"SAFETY OVERRIDE: Memory leak detected — memory at {memory}MB with only "
                f"{cpu}% CPU and {error_rate}% errors. The process is hoarding RAM without "
                f"doing useful work. Forcing restart_container to reclaim leaked memory."
            ),
            "confidence": 1.0,
        }

    # --- 5. Sustained-breach gate (CRON only — mirrors alert_rules.yml) --
    # Webhook path: Alertmanager already enforced `for:` before calling us.
    if source == "cron":
        if action == "scale_up" and isinstance(cpu, (int, float)) and cpu >= CPU_ALERT_THRESHOLD:
            if not _breach_sustained("cpu"):
                elapsed = _breach_elapsed("cpu")
                needed = BREACH_DURATIONS_SECONDS["cpu"]
                return _safe_decision(
                    f"Rejected: CPU at {cpu}% but breach not sustained for {needed}s yet "
                    f"({elapsed:.0f}s elapsed — CRON must not beat Alertmanager's window)."
                )

        if action == "restart_container" and isinstance(error_rate, (int, float)) and error_rate >= HIGH_ERROR_RATE_THRESHOLD:
            if not _breach_sustained("error_rate"):
                elapsed = _breach_elapsed("error_rate")
                needed = BREACH_DURATIONS_SECONDS["error_rate"]
                return _safe_decision(
                    f"Rejected: error_rate at {error_rate}% but breach not sustained for {needed}s yet "
                    f"({elapsed:.0f}s elapsed)."
                )

    # --- 6. Cooldown -----------------------------------------------------
    if action in ACTIONS_REQUIRING_COOLDOWN:
        now = time.time()
        seconds_since_last = now - _last_action_time
        if seconds_since_last < COOLDOWN_SECONDS:
            return _safe_decision(
                f"Rejected: cooldown active. Last infrastructure change was "
                f"{seconds_since_last:.0f}s ago; must wait {COOLDOWN_SECONDS}s between actions. "
                f"Original reasoning was: {reason}"
            )
        _last_action_time = now

    return decision
