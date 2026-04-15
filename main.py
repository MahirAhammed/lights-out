from api.v1 import subscribers
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.database import engine
from models import Base
from services.scheduler import start_scheduler
from config.config import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    yield

app = FastAPI(title="LightsOut", lifespan=lifespan)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except RateLimitExceeded:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Please wait a moment before trying again."}
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-type", "Random-token"],
)

app.include_router(subscribers.router, prefix="/api/v1/subscribers", tags=["subscribers"])

@app.head("/health")
@limiter.limit("6/hour")
async def health(request: Request):
    return {"status": "ok"}