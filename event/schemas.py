from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, PositiveInt

from db.models import EventInvitationStatus


class EventCreateSchema(BaseModel):
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    location: str = Field(..., min_length=5)
    start_time: datetime
    end_time: datetime


class EventUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class EventOrganizerUpdateSchema(BaseModel):
    organizer_id: Optional[PositiveInt] = None


class EventOutSchema(BaseModel):
    id: PositiveInt
    user_id: PositiveInt
    organizer_id: PositiveInt
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    location: str = Field(..., min_length=5)
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime


class EventInvitationCreateSchema(BaseModel):
    recipient_id: PositiveInt


class EventInvitationOutSchema(BaseModel):
    id: PositiveInt
    event_id: PositiveInt
    recipient_id: PositiveInt
    sender_id: PositiveInt
    status: EventInvitationStatus
    created_at: datetime
    updated_at: datetime
