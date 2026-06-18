# The /webhook endpoint FastAPI/Flask code
from fastapi import APIRouter, Request
from api.context_builder import ContextBuilder  # <--- UPDATED IMPORT

router = APIRouter()
context_builder = ContextBuilder()

@router.post("/webhook")
async def receive_alert(request: Request):
    payload = await request.json()
    
    print("\n" + "="*50)
    print("🚨 ALERT RECEIVED FROM ALERTMANAGER! 🚨")
    
    print("🔍 Context Builder: Fetching current system metrics from Prometheus...")
    system_state = await context_builder.get_system_state()
    
    print("\n📊 CURRENT SYSTEM STATE:")
    for metric, value in system_state.items():
        print(f"   - {metric}: {value}")
    print("="*50 + "\n")
    
    return {"status": "success", "message": "Alert caught and context built."}