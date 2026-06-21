# Code to call the Groq API and get back a structured decision.
import os
import json
from groq import AsyncGroq

from brain.prompts import SYSTEM_PROMPT, build_incident_prompt
from api.log_formatter import console

# Centralizing the model name here (instead of inline in the call) makes it
# a one-line change if we ever want to swap models.
MODEL_NAME = "llama-3.3-70b-versatile"

# A safe fallback decision used whenever the LLM call fails outright (bad
# API key, network issue, rate limit, malformed response, etc). We always
# want to fail toward doing nothing rather than crash the whole pipeline.
FALLBACK_DECISION = {
    "action": "no_action",
    "reason": "LLM call failed or returned unparseable output; defaulting to no_action for safety.",
    "confidence": 0.0,
}


class LLMClient:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            # We don't raise here because we still want the rest of the app
            # (and local dev without a key yet) to import and start up.
            # The actual API call below will fail loudly instead.
            console.print("  LLMClient: GROQ_API_KEY is not set. Calls will fail.", style="bold red")
        self.client = AsyncGroq(api_key=api_key)

    async def get_decision(self, system_state: dict) -> dict:
        """Sends the current system state to Groq and returns a decision
        dict shaped like {"action": ..., "reason": ..., "confidence": ...}.

        Never raises: on any failure this returns FALLBACK_DECISION so a
        flaky LLM call can't take down the API route or the cron job.
        """
        user_prompt = build_incident_prompt(system_state)

        try:
            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # low temperature: we want consistent, repeatable ops decisions
                max_completion_tokens=300,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content
            decision = json.loads(raw_content)
            return decision

        except json.JSONDecodeError as e:
            console.print(f"  LLMClient: Could not parse LLM response as JSON: {e}", style="bold yellow")
            return FALLBACK_DECISION
        except Exception as e:
            # Catches Groq SDK errors (auth, rate limit, connection, etc.)
            # as well as anything unexpected. We'd rather log and fall back
            # than let an incident response pipeline crash.
            console.print(f"  LLMClient: Groq API call failed: {e}", style="bold yellow")
            return FALLBACK_DECISION