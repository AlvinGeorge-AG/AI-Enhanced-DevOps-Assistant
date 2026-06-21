"""
Pure unit test for safety_engine.py — no API key, no network, no Docker.
Feeds fake LLM decisions straight into validate_decision() to check each
guardrail fires correctly.

Run from src/:
    python3 -m pytest ../tests/test_safety_engine.py -v
    # or:
    cd src && python3 ../tests/test_safety_engine.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import brain.safety_engine as safety_engine
from brain.safety_engine import validate_decision

STATE = {
    "cpu_usage_percent": 85.0,
    "memory_usage_mb": 500,
    "error_rate_percent": 1.0,
    "active_replicas": 2,
}


def _seed_cpu_breach(seconds_ago: float = 20.0):
    safety_engine._breach_started_at["cpu"] = time.time() - seconds_ago


def _seed_error_breach(seconds_ago: float = 70.0):
    safety_engine._breach_started_at["error_rate"] = time.time() - seconds_ago


def _reset_engine_state():
    safety_engine._breach_started_at.clear()
    safety_engine._extinction_since = None
    safety_engine._last_action_time = 0.0


TESTS = [
    {
        "name": "valid scale_up passes through after sustained CPU breach (cron)",
        "setup": _seed_cpu_breach,
        "decision": {"action": "scale_up", "reason": "CPU is high", "confidence": 0.9},
        "state": STATE,
        "expect_action": "scale_up",
    },
    {
        "name": "webhook scale_up passes immediately without local breach timer",
        "setup": _reset_engine_state,
        "source": "webhook",
        "decision": {"action": "scale_up", "reason": "Alertmanager fired HighCPUUsage", "confidence": 0.95},
        "state": STATE,
        "expect_action": "scale_up",
    },
    {
        "name": "scale_up rejected before CPU breach is sustained",
        "setup": lambda: safety_engine._breach_started_at.update({"cpu": time.time()}),
        "decision": {"action": "scale_up", "reason": "CPU is high", "confidence": 0.9},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "low confidence gets rejected",
        "setup": _seed_cpu_breach,
        "decision": {"action": "scale_up", "reason": "Maybe?", "confidence": 0.3},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "invalid action name gets rejected",
        "setup": _seed_cpu_breach,
        "decision": {"action": "delete_everything", "reason": "oops", "confidence": 0.95},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "scale_down at min replicas gets rejected",
        "setup": _reset_engine_state,
        "decision": {"action": "scale_down", "reason": "Low load", "confidence": 0.9},
        "state": {**STATE, "active_replicas": 1},
        "expect_action": "no_action",
    },
    {
        "name": "scale_up at max replicas gets rejected",
        "setup": _seed_cpu_breach,
        "decision": {"action": "scale_up", "reason": "High load", "confidence": 0.9},
        "state": {**STATE, "active_replicas": 5},
        "expect_action": "no_action",
    },
    {
        "name": "scale_up rejected when metrics are actually healthy",
        "setup": _reset_engine_state,
        "decision": {"action": "scale_up", "reason": "Just in case", "confidence": 0.9},
        "state": {**STATE, "cpu_usage_percent": 10.0, "error_rate_percent": 0.5},
        "expect_action": "no_action",
    },
    {
        "name": "scale_up rejected when only memory is elevated (leak, not load)",
        "setup": _reset_engine_state,
        "decision": {"action": "scale_up", "reason": "Memory high", "confidence": 0.9},
        "state": {**STATE, "cpu_usage_percent": 10.0, "memory_usage_mb": 200.0, "error_rate_percent": 0.5},
        "expect_action": "no_action",
    },
    {
        "name": "scale_down rejected when CPU is still high",
        "setup": _reset_engine_state,
        "decision": {"action": "scale_down", "reason": "Saving resources", "confidence": 0.9},
        "state": {**STATE, "cpu_usage_percent": 80.0, "active_replicas": 3},
        "expect_action": "no_action",
    },
    {
        "name": "missing confidence field gets rejected",
        "setup": _seed_cpu_breach,
        "decision": {"action": "scale_up", "reason": "no confidence given"},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "transient active_replicas=0 does not immediately defibrillate",
        "setup": _reset_engine_state,
        "decision": {"action": "no_action", "reason": "monitoring", "confidence": 0.9},
        "state": {**STATE, "active_replicas": 0.0},
        "expect_action": "no_action",
    },
    {
        "name": "restart_container rejected before error breach is sustained",
        "setup": lambda: safety_engine._breach_started_at.update({"error_rate": time.time()}),
        "decision": {"action": "restart_container", "reason": "Errors high", "confidence": 0.9},
        "state": {**STATE, "error_rate_percent": 10.0},
        "expect_action": "no_action",
    },
    {
        "name": "restart_container passes after sustained error breach",
        "setup": _seed_error_breach,
        "decision": {"action": "restart_container", "reason": "Errors high", "confidence": 0.9},
        "state": {**STATE, "error_rate_percent": 10.0},
        "expect_action": "restart_container",
    },
]


def run():
    passed, failed = 0, 0
    for t in TESTS:
        _reset_engine_state()
        setup = t.get("setup")
        if setup:
            setup()

        source = t.get("source", "cron")
        result = validate_decision(t["decision"], t["state"], source=source)
        ok = result["action"] == t["expect_action"]
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} — {t['name']}")
        print(f"         got: {result}")
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"         expected action: {t['expect_action']}")

    print(f"\n{passed} passed, {failed} failed out of {len(TESTS)}")


if __name__ == "__main__":
    run()
