"""
Isolated test for the brain module (Module 3).
Mocks system_state directly so you don't need Prometheus, Docker, or the
full stack running. Just needs GROQ_API_KEY set in your environment.

Run from src/:
    python3 test_brain.py
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env from the current directory (or parent dirs) into os.environ

from brain.llm_client import LLMClient
from brain.safety_engine import validate_decision

# Try a few different fake states to see how the brain + safety engine react.
SCENARIOS = {
    "high_cpu_should_scale_up": {
        "cpu_usage_percent": 9.5,
        "memory_usage_mb": 8,
        "error_rate_percent": 6.2,
        "active_replicas": 2,
    },
    "idle_should_scale_down": {
        "cpu_usage_percent": 9.0,
        "memory_usage_mb": 120,
        "error_rate_percent": 0.0,
        "active_replicas": 3,
    },
    "healthy_should_no_action": {
        "cpu_usage_percent": 3.0,
        "memory_usage_mb": 1000,
        "error_rate_percent": 0.5,
        "active_replicas": 2,
    },
    "already_at_min_replicas": {
        "cpu_usage_percent": 95.0,
        "memory_usage_mb": 100,
        "error_rate_percent": 0.0,
        "active_replicas": 6,
    },
}


async def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY is not set in this shell. Export it first:")
        print("    export GROQ_API_KEY=your_key_here")
        return

    client = LLMClient()

    for name, state in SCENARIOS.items():
        print("\n" + "=" * 60)
        print(f"SCENARIO: {name}")
        print(f"INPUT STATE: {state}")

        raw_decision = await client.get_decision(state)
        print(f"RAW LLM DECISION: {raw_decision}")

        final_decision = validate_decision(raw_decision, state)
        if final_decision is not raw_decision:
            print(f"⚠️  SAFETY ENGINE OVERRODE: {final_decision}")
        else:
            print(f"✅ SAFETY ENGINE APPROVED: {final_decision}")


if __name__ == "__main__":
    asyncio.run(main())