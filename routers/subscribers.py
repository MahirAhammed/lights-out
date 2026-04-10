from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
from database import get_db
from models import Subscriber
from schemas import SubscribeRequest, OneTimeEmailRequest
from email_service import send_verification_email, send_welcome_email, send_one_time_email

router = APIRouter()

@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.email == request.email))
    existing = result.scalar_one_or_none()
    if existing:
        if existing.verified:
            raise HTTPException(400, "Already subscribed")
        # Resend verification
        background_tasks.add_task(send_verification_email, existing.email, existing.name or "F1 Fan", existing.verification_token, db)
        return {"message": "Verification email resent"}

    verification_token = secrets.token_urlsafe(32)
    unsubscribe_token = secrets.token_urlsafe(32)
    subscriber = Subscriber(
        email=request.email,
        name=request.name,
        timezone=request.timezone or "UTC",
        country=request.country,
        email_preference=request.email_preference,
        custom_prefs=request.custom_prefs or {},
        verification_token=verification_token,
        unsubscribe_token=unsubscribe_token,
    )
    db.add(subscriber)
    await db.commit()
    background_tasks.add_task(send_verification_email, request.email, request.name or "F1 Fan", verification_token, db)
    return {"message": "Please check your email to verify your subscription"}

@router.get("/verify")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.verification_token == token))
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(400, "Invalid or expired token")
    subscriber.verified = True
    subscriber.verification_token = None
    await db.commit()
    # Send welcome email
    await send_welcome_email(subscriber.email, subscriber.name or "F1 Fan", subscriber.unsubscribe_token, db)
    return {"message": "Email verified! Welcome to F1 Updates"}

@router.get("/unsubscribe")
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).where(Subscriber.unsubscribe_token == token))
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(400, "Invalid token")
    subscriber.is_active = False
    await db.commit()
    return {"message": "You've been unsubscribed. Sorry to see you go!"}