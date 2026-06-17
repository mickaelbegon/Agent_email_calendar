import argparse
import csv
from pathlib import Path

from classifier import classify_email
from config import ConfigError, load_config
from draft_generator import generate_draft
from email_parser import ParsedEmail, load_email_files
from ics_writer import write_ics
from outlook_applescript import OutlookAppleScriptError, fetch_recent_emails
from task_scheduler import TaskRecord, build_task_record


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return (cleaned[:80] or fallback).lower()


def _ensure_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    drafts_dir = output_dir / "drafts"
    calendar_dir = output_dir / "calendar_blocks"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    calendar_dir.mkdir(parents=True, exist_ok=True)
    return drafts_dir, calendar_dir


def _load_emails(source: str, input_dir: Path, limit: int) -> list[ParsedEmail]:
    if source in {"auto", "outlook"}:
        try:
            emails = fetch_recent_emails(limit=limit)
            if emails:
                return emails
            print("Outlook AppleScript n'a retourne aucun courriel.")
        except OutlookAppleScriptError as exc:
            print(f"Outlook AppleScript indisponible: {exc}")

        if source == "outlook":
            return []

    return load_email_files(input_dir=input_dir, limit=limit)


def _write_tasks_csv(path: Path, tasks: list[TaskRecord]) -> None:
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


def run(source: str) -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration invalide: {exc}")
        return 1

    config.input_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir, calendar_dir = _ensure_output_dirs(config.output_dir)

    emails = _load_emails(source=source, input_dir=config.input_dir, limit=config.max_emails)
    if not emails:
        print(
            "Aucun courriel trouve. Ajoute des fichiers .eml, .txt ou .msg dans "
            f"{config.input_dir} ou reessaie avec Outlook ouvert."
        )
        return 0

    tasks: list[TaskRecord] = []
    print(f"Analyse de {len(emails)} courriel(s). Dry-run: {config.dry_run}")
    print("Mode securite: aucun courriel ne sera envoye; seuls des fichiers locaux seront crees.")

    for email in emails:
        assessment = classify_email(
            email,
            llm_mode=config.llm_mode,
            openai_api_key=config.openai_api_key,
        )
        task = build_task_record(
            email,
            assessment,
            timezone=config.timezone,
            max_personal_block_minutes=config.personal_work_max_block_minutes,
        )
        tasks.append(task)

        base_name = _safe_filename(email.subject, email.email_id)
        draft_path = drafts_dir / f"{base_name}.txt"
        draft_path.write_text(generate_draft(email, assessment), encoding="utf-8")

        if config.create_ics and assessment.recommended_action in {"planifier", "repondre"}:
            ics_path = calendar_dir / f"{base_name}.ics"
            write_ics(
                ics_path,
                title=f"Traiter: {email.subject}",
                description=f"Bloc local suggere. Source: {email.source}",
                start_iso=task.suggested_start,
                end_iso=task.suggested_end,
            )

        print(
            f"- {email.subject} | {assessment.category} | {assessment.urgency} | "
            f"{assessment.estimated_minutes} min | {assessment.recommended_action}"
        )

    _write_tasks_csv(config.output_dir / "tasks.csv", tasks)
    print(f"\nResultats ecrits dans: {config.output_dir}")
    print(f"- Taches: {config.output_dir / 'tasks.csv'}")
    print(f"- Brouillons: {drafts_dir}")
    if config.create_ics:
        print(f"- Fichiers ICS: {calendar_dir}")
    else:
        print("- Fichiers ICS: desactives (CREATE_ICS=false)")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prototype local Outlook sans Microsoft Graph.")
    parser.add_argument(
        "--source",
        choices=["auto", "outlook", "files"],
        default="auto",
        help="auto essaie Outlook puis les fichiers locaux; files ignore Outlook.",
    )
    args = parser.parse_args()
    return run(source=args.source)


if __name__ == "__main__":
    raise SystemExit(main())
