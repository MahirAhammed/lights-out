from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(None, max_length = 50, pattern=r"^[A-Za-zÀ-ÖØ-öø-ÿ\s'\-\.]+$")
    timezone: Optional[str] = Field("UTC", max_length=30)
    pref_pre_race: bool = True
    pref_qualifying: bool = True
    pref_race: bool = True
    pref_sprint: bool = True

class OneTimeEmailRequest(BaseModel):
    email: EmailStr
    email_type: str  # "standings" or "schedule"

class CustomEmailRequest(BaseModel):
    subject: str
    html_body: str
    to_all: bool = True
    emails: Optional[list[str]] = None