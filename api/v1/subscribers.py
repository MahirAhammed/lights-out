from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
from config.database import get_db
from models import Subscriber
from schemas import SubscribeRequest, OneTimeEmailRequest
from services.email_service import send_verification_email, send_welcome_email, send_one_time_email
from config.config import settings
from datetime import datetime, timezone, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
VERIFICATION_EXPIRATION = 24

@router.post("/subscribe")
@limiter.limit("3/hour")
async def subscribe(request: Request, request_type: SubscribeRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.email == request_type.email))
    existing = result.scalar_one_or_none()
    if existing:
        if existing.verified:
            raise HTTPException(400, "Already subscribed")
        # Resend verification
        existing.verification_token = secrets.token_urlsafe(32)
        existing.created_at = datetime.now(timezone.utc)   # reset expiry clock
        await db.commit()
        background_tasks.add_task(
            send_verification_email,
            existing.email,
            existing.name or "F1 Fan",
            existing.verification_token,
            db
        )
        return {"message": "Verification email sent. Please check your inbox."}

    verification_token = secrets.token_urlsafe(32)
    unsubscribe_token = secrets.token_urlsafe(32)
    subscriber = Subscriber(
        email=request_type.email,
        name=request_type.name,
        timezone=request_type.timezone or "UTC",
        pref_pre_race = request_type.pref_pre_race,
        pref_qualifying = request_type.pref_qualifying,
        pref_race = request_type.pref_race,
        pref_sprint = request_type.pref_sprint,
        verification_token = verification_token,
        unsubscribe_token = unsubscribe_token,
    )
    db.add(subscriber)
    await db.commit()
    background_tasks.add_task(send_verification_email, request_type.email, request_type.name or "F1 Fan", verification_token, db)
    return {"message": "Please check your email to verify your subscription"}

@router.get("/verify")
@limiter.limit("5/minute")
async def verify(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.verification_token == token))
    subscriber = result.scalar_one_or_none()
    if not subscriber:
         return RedirectResponse(url=f"{settings.frontend_url}/verify.html?status=error",status_code=302)

    token_age = datetime.now(timezone.utc) - subscriber.created_at
    if token_age > timedelta(hours=VERIFICATION_EXPIRATION):
        await db.delete(subscriber)
        await db.commit()
        return RedirectResponse(
            url=f"{settings.frontend_url}/verify.html?status=error",
            status_code=302
        )
    
    subscriber.verified = True
    subscriber.verification_token = None
    await db.commit()
    try:
        await send_welcome_email(subscriber.email, subscriber.name or "F1 Fan", subscriber.unsubscribe_token, db)
    except Exception as e:
        print(f"Welcome email failed: {e}")

    return RedirectResponse(url=f"{settings.frontend_url}/verify.html?status=success", status_code=302)


@router.get("/unsubscribe")
@limiter.limit("5/minute")
async def unsubscribe(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.unsubscribe_token == token))
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(400, "Invalid unsubscribe link")
    
    if not subscriber.is_active:
        return {"message": "Already unsubscribed."}

    subscriber.is_active = False
    await db.commit()
    return {"message": "You've been unsubscribed successfully. Sorry to see you go!"}


@router.post("/onetime")
@limiter.limit("5/hour")
async def one_time_email(request: Request, request_type: OneTimeEmailRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if request_type.email_type not in ("standings", "schedule"):
        raise HTTPException(400, "Invalid email type")
    background_tasks.add_task(send_one_time_email, request_type.email, request_type.email_type, db)
    return {"message": f"Sending {request_type.email_type} email to {request_type.email}"}