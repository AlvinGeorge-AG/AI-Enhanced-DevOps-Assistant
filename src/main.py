from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import router
from api.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    scheduler = start_scheduler()
    yield
    # Shutdown logic
    scheduler.shutdown()

app = FastAPI(title="SentinelAI Core API", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)