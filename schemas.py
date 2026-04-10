from pydantic import BaseModel, EmailStr
from typing import Optional
from models import EmailPreference

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    timezone: Optional[str] = "UTC"
    country: Optional[str] = None
    email_preference: EmailPreference = EmailPreference.all
    custom_prefs: Optional[dict] = None

class OneTimeEmailRequest(BaseModel):
    email: EmailStr
    email_type: str  # "standings" or "schedule"

class CustomEmailRequest(BaseModel):
    subject: str
    html_body: str
    to_all: bool = True
    emails: Optional[list[str]] = None