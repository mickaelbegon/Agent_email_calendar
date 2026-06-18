import argparse
from pathlib import Path

from config import ConfigError, load_config
from email_parser import ParsedEmail, load_email_files
from outlook_local import OutlookLocalError, fetch_recent_emails
from processor import ensure_output_dirs, process_emails


def _load_emails(source: str, input_dir: Path, limit: int) -> list[ParsedEmail]:
    if source in {"auto", "outlook"}:
        try:
            emails = fetch_recent_emails(limit=limit)
            if emails:
                return emails
            print("Outlook local n'a retourne aucun courriel.")
        except OutlookLocalError as exc:
            print(f"Outlook local indisponible: {exc}")

        if source == "outlook":
            return []

    return load_email_files(input_dir=input_dir, limit=limit)


def run(source: str) -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration invalide: {exc}")
        return 1

    config.input_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir, calendar_dir = ensure_output_dirs(config.output_dir)

    emails = _load_emails(source=source, input_dir=config.input_dir, limit=config.max_emails)
    if not emails:
        print(
            "Aucun courriel trouve. Ajoute des fichiers .eml, .txt ou .msg dans "
            f"{config.input_dir} ou reessaie avec Outlook ouvert."
        )
        return 0

    print(f"Analyse de {len(emails)} courriel(s). Dry-run: {config.dry_run}")
    print("Mode securite: aucun courriel ne sera envoye; seuls des fichiers locaux seront crees.")

    processed = process_emails(
        emails,
        output_dir=config.output_dir,
        timezone=config.timezone,
        max_personal_block_minutes=config.personal_work_max_block_minutes,
        llm_mode=config.llm_mode,
        openai_api_key=config.openai_api_key,
        create_ics=config.create_ics,
    )
    for item in processed:
        print(
            f"- {item.email.subject} | {item.assessment.category} | {item.assessment.urgency} | "
            f"{item.assessment.estimated_minutes} min | {item.assessment.recommended_action}"
        )

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
