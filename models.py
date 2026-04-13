from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class Subscriber(Base):
    __tablename__ = "subscribers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    pref_pre_race = Column(Boolean, default=True)
    pref_qualifying = Column(Boolean, default=True)
    pref_race = Column(Boolean, default=True)
    pref_sprint = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    unsubscribe_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_emailed_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_email = Column(String, nullable=False)
    email_type = Column(String, nullable=False)  # pre_race, quali, race, welcome, verify, custom, one_time
    race_name = Column(String, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    resend_id = Column(String, nullable=True)
    status = Column(String, default="sent")
    error_message = Column(Text, nullable=True)