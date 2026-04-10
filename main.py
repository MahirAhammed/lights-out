from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine
from models import Base
from scheduler import start_scheduler
from routers import subscribers, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    yield

app = FastAPI(title="LightsOut", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subscribers.router, prefix="/api/v1/subscribers", tags=["subscribers"])

@app.get("/health")
async def health():
    return {"status": "ok"}