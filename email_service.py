import resend
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from config import settings
from models import EmailLog
from sqlalchemy.ext.asyncio import AsyncSession

resend.api_key = settings.resend_api_key

jinja_env = Environment(loader = FileSystemLoader("templates/"), autoescape = True)

async def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict,
    db: AsyncSession,
    email_type: str,
    race_name: str | None = None
):
    template = jinja_env.get_template(template_name)
    html = template.render(**context)
    
    try:
        response = resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        resend_id = response.get("id")
        log = EmailLog(
            subscriber_email=to,
            email_type=email_type,
            race_name=race_name,
            resend_id=resend_id,
            status="sent"
        )
    except Exception as e:
        log = EmailLog(
            subscriber_email=to,
            email_type=email_type,
            race_name=race_name,
            status="failed",
            error_message=str(e)
        )
        raise
    finally:
        db.add(log)
        await db.commit()

async def send_verification_email(to: str, name: str, token: str, db: AsyncSession):
    verification_url = f"{settings.api_base_url}/subscribers/verify?token={token}"
    await send_email(
        to=to,
        subject="Confirm your F1 updates subscription",
        template_name="verify.html",
        context={"name": name, "verify_url": verification_url},
        db=db,
        email_type="verify"
    )

async def send_welcome_email(to: str, name: str, unsubscribe_token: str, db: AsyncSession):
    unsubscribe_url = f"{settings.api_base_url}/subscribers/unsubscribe?token={unsubscribe_token}"
    await send_email(
        to=to, subject="Welcome to F1 Updates 🏎️",
        template_name="welcome.html",
        context={"name": name, "unsubscribe_url": unsubscribe_url},
        db=db, email_type="welcome"
    )
