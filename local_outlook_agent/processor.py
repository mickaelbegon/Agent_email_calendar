import csv
from dataclasses import dataclass
from pathlib import Path

from classifier import EmailAssessment, classify_email
from draft_generator import generate_draft
from email_parser import ParsedEmail
from ics_writer import write_ics
from task_scheduler import TaskRecord, build_task_record


@dataclass(frozen=True)
class ProcessedEmail:
    email: ParsedEmail
    assessment: EmailAssessment
    task: TaskRecord
    draft_text: str
    draft_path: Path
    ics_path: Path | None


def safe_filename(value: str, fallback: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return (cleaned[:80] or fallback).lower()


def ensure_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    drafts_dir = output_dir / "drafts"
    calendar_dir = output_dir / "calendar_blocks"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    calendar_dir.mkdir(parents=True, exist_ok=True)
    return drafts_dir, calendar_dir


def write_tasks_csv(path: Path, tasks: list[TaskRecord]) -> None:
    fieldnames = [
        "email_id",
        "subject",
        "sender",
        "category",
        "urgency",
        "importance",
        "estimated_minutes",
        "recommended_action",
        "rationale",
        "source",
        "suggested_start",
        "suggested_end",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            writer.writerow(task.__dict__)


def process_emails(
    emails: list[ParsedEmail],
    *,
    output_dir: Path,
    timezone: str,
    max_personal_block_minutes: int,
    llm_mode: str,
    openai_api_key: str,
    create_ics: bool,
) -> list[ProcessedEmail]:
    drafts_dir, calendar_dir = ensure_output_dirs(output_dir)
    processed: list[ProcessedEmail] = []

    for email in emails:
        assessment = classify_email(
            email,
            llm_mode=llm_mode,
            openai_api_key=openai_api_key,
        )
        task = build_task_record(
            email,
            assessment,
            timezone=timezone,
            max_personal_block_minutes=max_personal_block_minutes,
        )

        base_name = safe_filename(email.subject, email.email_id)
        draft_text = generate_draft(email, assessment)
        draft_path = drafts_dir / f"{base_name}.txt"
        draft_path.write_text(draft_text, encoding="utf-8")

        ics_path = None
        if create_ics and assessment.recommended_action in {"planifier", "repondre"}:
            ics_path = calendar_dir / f"{base_name}.ics"
            write_ics(
                ics_path,
                title=f"Traiter: {email.subject}",
                description=f"Bloc local suggere. Source: {email.source}",
                start_iso=task.suggested_start,
                end_iso=task.suggested_end,
            )

        processed.append(
            ProcessedEmail(
                email=email,
                assessment=assessment,
                task=task,
                draft_text=draft_text,
                draft_path=draft_path,
                ics_path=ics_path,
            )
        )

    write_tasks_csv(output_dir / "tasks.csv", [item.task for item in processed])
    return processed

