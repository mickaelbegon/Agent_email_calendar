from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgendaActionType(str, Enum):
    NO_ACTION = "no_action"
    MEETING_REQUEST = "meeting_request"
    DEADLINE = "deadline"
    RESCHEDULE_REQUEST = "reschedule_request"
    AVAILABILITY_REQUEST = "availability_request"
    AMBIGUOUS = "ambiguous"


class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EmailAgendaAnalysis(BaseModel):
    requires_calendar_action: bool
    action_type: AgendaActionType
    summary: str
    topic: Optional[str] = None
    participants: list[str] = Field(default_factory=list)
    requested_period: Optional[str] = None
    requested_date: Optional[str] = None
    requested_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    urgency: Urgency = Urgency.NORMAL
    ambiguities: list[str] = Field(default_factory=list)
    recommended_next_step: str
    confidence: float = Field(ge=0.0, le=1.0)


class SuggestedSlot(BaseModel):
    start: str
    end: str
    label: str


class EmailProcessingResult(BaseModel):
    email_id: str
    subject: str
    sender: str
    received_datetime: str
    analysis: EmailAgendaAnalysis
    suggested_slots: list[SuggestedSlot] = Field(default_factory=list)

