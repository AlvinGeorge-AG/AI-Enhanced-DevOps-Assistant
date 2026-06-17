# The entry point that starts the API and Cron scheduler
from fastapi import FastAPI
from api.routes import router
from apscheduler.schedulers.background import BackgroundScheduler
from api.context_builder import ContextBuilder  # <--- UPDATED IMPORT
import asyncio

app = FastAPI(title="SentinelAI Core API")
app.include_router(router)

context_builder = ContextBuilder()

def scheduled_health_check():
    print("\n⏰ CRON: Running routine system health check...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    state = loop.run_until_complete(context_builder.get_system_state())
    
    print(f"📊 ROUTINE STATE: {state}\n")

@app.on_event("startup")
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_health_check, 'interval', minutes=1)
    scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)