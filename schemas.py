from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re

NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s'\-\.]+$")

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(None, max_length = 50)
    timezone: Optional[str] = Field("UTC", max_length=50)
    pref_pre_race: bool = True
    pref_qualifying: bool = True
    pref_race: bool = True
    pref_sprint: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not NAME_PATTERN.match(v):
            raise ValueError("Name can only contain letters, spaces, hyphens, apostrophes, and periods")
        return v

class OneTimeEmailRequest(BaseModel):
    email: EmailStr
    email_type: str  # "standings" or "schedule"

class CustomEmailRequest(BaseModel):
    subject: str
    html_body: str
    to_all: bool = True
    emails: Optional[list[str]] = None