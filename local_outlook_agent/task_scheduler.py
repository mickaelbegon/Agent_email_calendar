from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from classifier import EmailAssessment
from email_parser import ParsedEmail


@dataclass(frozen=True)
class TaskRecord:
    email_id: str
    subject: str
    sender: str
    category: str
    urgency: str
    importance: str
    estimated_minutes: int
    recommended_action: str
    rationale: str
    source: str
    suggested_start: str
    suggested_end: str


def _next_work_start(now: datetime) -> datetime:
    candidate = now.replace(second=0, microsecond=0)
    work_start = candidate.replace(hour=8, minute=30)
    work_end = candidate.replace(hour=17, minute=30)

    if candidate.weekday() >= 5 or candidate >= work_end:
        candidate = (candidate + timedelta(days=1)).replace(hour=8, minute=30)
    elif candidate < work_start:
        candidate = work_start

    while candidate.weekday() >= 5:
        candidate = (candidate + timedelta(days=1)).replace(hour=8, minute=30)

    return candidate


def build_task_record(
    email: ParsedEmail,
    assessment: EmailAssessment,
    timezone: str,
    max_personal_block_minutes: int,
) -> TaskRecord:
    now = datetime.now(ZoneInfo(timezone))
    start = _next_work_start(now)
    block_minutes = min(assessment.estimated_minutes, max_personal_block_minutes)
    end = start + timedelta(minutes=block_minutes)

    work_end = datetime.combine(start.date(), time(17, 30), tzinfo=start.tzinfo)
    if end > work_end:
        end = work_end

    return TaskRecord(
        email_id=email.email_id,
        subject=email.subject,
        sender=email.sender,
        category=assessment.category,
        urgency=assessment.urgency,
        importance=assessment.importance,
        estimated_minutes=assessment.estimated_minutes,
        recommended_action=assessment.recommended_action,
        rationale=assessment.rationale,
        source=email.source,
        suggested_start=start.isoformat(),
        suggested_end=end.isoformat(),
    )

