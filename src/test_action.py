from executor.action_engine import ActionEngine

print("\n--- Starting Action Engine Isolated Test ---")

engine = ActionEngine()

# The AI no longer needs to guess the target replicas. 
# It just passes the general intent!
fake_ai_decision = {
    "action": "scale_up",
    "reason": "Simulated CPU spike",
    "confidence": 0.99
}

engine.execute(fake_ai_decision)

print("--- Test Complete ---\n")