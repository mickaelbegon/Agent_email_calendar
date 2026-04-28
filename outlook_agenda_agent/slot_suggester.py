from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from config import (
    DEFAULT_MEETING_DURATION_MINUTES,
    MAX_SLOT_SUGGESTIONS,
    WORK_END_HOUR,
    WORK_START_HOUR,
)
from models import SuggestedSlot


def _parse_graph_datetime(value: str, timezone: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(ZoneInfo(timezone))


def _is_working_time(start: datetime, end: datetime) -> bool:
    if start.weekday() >= 5 or end.weekday() >= 5:
        return False

    work_start = start.replace(
        hour=WORK_START_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    work_end = start.replace(
        hour=WORK_END_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start >= work_start and end <= work_end and start.date() == end.date()


def _iter_free_runs(availability_view: str, required_blocks: int) -> list[int]:
    starts = []
    run_length = 0
    run_start = 0

    for index, value in enumerate(availability_view):
        if value == "0":
            if run_length == 0:
                run_start = index
            run_length += 1
            if run_length >= required_blocks:
                starts.append(index - required_blocks + 1)
        else:
            run_length = 0
            run_start = index + 1

    return starts


def suggest_slots_from_schedule(
    schedule_response: dict[str, Any],
    duration_minutes: Optional[int],
    range_start: str,
    range_end: str,
    *,
    interval_minutes: int = 30,
    timezone: str = "America/Montreal",
    max_suggestions: int = MAX_SLOT_SUGGESTIONS,
) -> list[SuggestedSlot]:
    duration = duration_minutes or DEFAULT_MEETING_DURATION_MINUTES
    required_blocks = max(1, (duration + interval_minutes - 1) // interval_minutes)
    range_start_dt = _parse_graph_datetime(range_start, timezone)
    range_end_dt = _parse_graph_datetime(range_end, timezone)

    schedules = schedule_response.get("value")
    if not isinstance(schedules, list) or not schedules:
        return []

    availability_view = schedules[0].get("availabilityView", "")
    if not isinstance(availability_view, str) or not availability_view:
        return []

    suggestions: list[SuggestedSlot] = []
    for start_index in _iter_free_runs(availability_view, required_blocks):
        slot_start = range_start_dt + timedelta(minutes=start_index * interval_minutes)
        slot_end = slot_start + timedelta(minutes=duration)

        if slot_end > range_end_dt:
            continue
        if not _is_working_time(slot_start, slot_end):
            continue

        suggestions.append(
            SuggestedSlot(
                start=slot_start.isoformat(),
                end=slot_end.isoformat(),
                label=slot_start.strftime("%A %Y-%m-%d %H:%M"),
            )
        )
        if len(suggestions) >= max_suggestions:
            break

    return suggestions

