from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def write_ics(
    path: Path,
    *,
    title: str,
    description: str,
    start_iso: str,
    end_iso: str,
) -> None:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    uid = f"{uuid4()}@local-outlook-agent"

    content = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Local Outlook Agent//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_escape(title)}",
            f"DESCRIPTION:{_escape(description)}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
