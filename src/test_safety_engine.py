"""
Pure unit test for safety_engine.py — no API key, no network, no Docker.
Feeds fake LLM decisions straight into validate_decision() to check each
guardrail fires correctly.

Run from src/:
    python3 test_safety_engine.py
"""
from brain.safety_engine import validate_decision

STATE = {
    "cpu_usage_percent": 85.0,
    "memory_usage_mb": 500,
    "error_rate_percent": 1.0,
    "active_replicas": 2,
}

TESTS = [
    {
        "name": "valid scale_up passes through",
        "decision": {"action": "scale_up", "reason": "CPU is high", "confidence": 0.9},
        "state": STATE,
        "expect_action": "scale_up",
    },
    {
        "name": "low confidence gets rejected",
        "decision": {"action": "scale_up", "reason": "Maybe?", "confidence": 0.3},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "invalid action name gets rejected",
        "decision": {"action": "delete_everything", "reason": "oops", "confidence": 0.95},
        "state": STATE,
        "expect_action": "no_action",
    },
    {
        "name": "scale_down at min replicas gets rejected",
        "decision": {"action": "scale_down", "reason": "Low load", "confidence": 0.9},
        "state": {**STATE, "active_replicas": 1},
        "expect_action": "no_action",
    },
    {
        "name": "scale_up at max replicas gets rejected",
        "decision": {"action": "scale_up", "reason": "High load", "confidence": 0.9},
        "state": {**STATE, "active_replicas": 5},
        "expect_action": "no_action",
    },
    {
        "name": "scale_up rejected when metrics are actually healthy",
        "decision": {"action": "scale_up", "reason": "Just in case", "confidence": 0.9},
        "state": {**STATE, "cpu_usage_percent": 10.0, "error_rate_percent": 0.5},
        "expect_action": "no_action",
    },
    {
        "name": "scale_down rejected when CPU is still high",
        "decision": {"action": "scale_down", "reason": "Saving resources", "confidence": 0.9},
        "state": {**STATE, "cpu_usage_percent": 80.0, "active_replicas": 3},
        "expect_action": "no_action",
    },
    {
        "name": "missing confidence field gets rejected",
        "decision": {"action": "scale_up", "reason": "no confidence given"},
        "state": STATE,
        "expect_action": "no_action",
    },
]


def run():
    passed, failed = 0, 0
    for t in TESTS:
        result = validate_decision(t["decision"], t["state"])
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