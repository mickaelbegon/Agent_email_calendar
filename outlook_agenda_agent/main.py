from datetime import datetime, time, timedelta
from html import unescape
from zoneinfo import ZoneInfo

from config import ConfigError, load_config


def _extract_sender(message: dict) -> str:
    email_address = message.get("from", {}).get("emailAddress", {})
    name = email_address.get("name", "")
    address = email_address.get("address", "")
    if name and address:
        return f"{name} <{address}>"
    return name or address or "Expediteur inconnu"


def _extract_sender_address(message: dict) -> str:
    return message.get("from", {}).get("emailAddress", {}).get("address", "")


def _extract_body_text(message: dict) -> str:
    body = message.get("body") or {}
    content = body.get("content") or ""
    # Graph peut retourner du HTML. Pour un prototype console, on garde une conversion simple.
    return unescape(content).strip()


def _next_ten_business_day_range(timezone: str) -> tuple[str, str]:
    now = datetime.now(ZoneInfo(timezone))
    start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = start
    business_days = 0
    while business_days < 10:
        if cursor.weekday() < 5:
            business_days += 1
        cursor += timedelta(days=1)
    end = cursor
    return start.isoformat(), end.isoformat()


def _local_time_equivalent(analysis, local_timezone: str) -> str | None:
    if not analysis.requested_timezone or not analysis.requested_date or not analysis.requested_time:
        return analysis.local_time_equivalent

    try:
        requested_time = time.fromisoformat(analysis.requested_time)
        requested_datetime = datetime.fromisoformat(analysis.requested_date).replace(
            hour=requested_time.hour,
            minute=requested_time.minute,
            second=requested_time.second,
            microsecond=0,
            tzinfo=ZoneInfo(analysis.requested_timezone),
        )
    except (ValueError, TypeError):
        return analysis.local_time_equivalent

    local_datetime = requested_datetime.astimezone(ZoneInfo(local_timezone))
    return local_datetime.strftime("%Y-%m-%d %H:%M %Z")


def _print_result(
    *,
    subject: str,
    sender: str,
    analysis,
    suggested_slots,
    local_timezone: str,
) -> None:
    print("\n" + "=" * 80)
    print(f"Sujet       : {subject or '(sans sujet)'}")
    print(f"Expediteur  : {sender}")
    print(f"Resume      : {analysis.summary}")
    print(f"Action      : {analysis.action_type.value}")
    duration_label = f"{analysis.duration_minutes} min" if analysis.duration_minutes else "non precisee"
    print(f"Duree       : {duration_label}")
    if analysis.estimated_effort_minutes:
        print(f"Effort      : {analysis.estimated_effort_minutes} min")
    if analysis.requested_timezone:
        print(f"Fuseau source: {analysis.requested_timezone}")
    local_time = _local_time_equivalent(analysis, local_timezone)
    if local_time:
        print(f"Heure locale: {local_time}")
    print(f"Confiance   : {analysis.confidence:.2f}")
    print(f"Ambiguites  : {', '.join(analysis.ambiguities) if analysis.ambiguities else 'aucune'}")
    print(f"Validation  : {analysis.recommended_next_step}")

    if suggested_slots:
        print("Creneaux proposes:")
        for slot in suggested_slots:
            print(f"  - {slot.label}: {slot.start} -> {slot.end}")
    else:
        print("Creneaux proposes: aucun")


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration incomplete: {exc}")
        return 1

    from graph_client import GraphClient, GraphClientError
    from openai_analyzer import EmailAgendaAnalyzer, EmailAgendaAnalyzerError
    from slot_suggester import suggest_slots_from_schedule

    graph = GraphClient(
        tenant_id=config.tenant_id,
        client_id=config.client_id,
        scopes=config.graph_scopes,
        timezone=config.timezone,
    )
    analyzer = EmailAgendaAnalyzer(api_key=config.openai_api_key)

    try:
        messages = graph.get_recent_emails(top=10)
    except GraphClientError as exc:
        print(f"Erreur Graph pendant la lecture des courriels: {exc}")
        return 1

    if not messages:
        print("Aucun courriel recent trouve dans la boite de reception.")
        return 0

    for message in messages:
        subject = message.get("subject") or ""
        sender = _extract_sender(message)
        body_preview = message.get("bodyPreview") or ""
        body_text = _extract_body_text(message)

        try:
            analysis = analyzer.analyze(
                subject=subject,
                sender=sender,
                body_preview=body_preview,
                body_text=body_text,
            )
        except EmailAgendaAnalyzerError as exc:
            print(f"\nCourriel ignore ({subject or 'sans sujet'}): {exc}")
            continue

        suggested_slots = []
        if analysis.requires_calendar_action and analysis.confidence >= 0.75:
            range_start, range_end = _next_ten_business_day_range(config.timezone)
            try:
                schedule = graph.get_schedule(
                    start_datetime=range_start,
                    end_datetime=range_end,
                    interval_minutes=30,
                )
                suggested_slots = suggest_slots_from_schedule(
                    schedule,
                    analysis.duration_minutes or analysis.estimated_effort_minutes,
                    range_start,
                    range_end,
                    interval_minutes=30,
                    timezone=config.timezone,
                    max_suggestions=config.max_slot_suggestions,
                    is_personal_work=analysis.is_personal_work,
                    max_personal_block_minutes=config.personal_work_max_block_minutes,
                )
            except GraphClientError as exc:
                print(f"Erreur Graph pendant la lecture du calendrier: {exc}")

        _print_result(
            subject=subject,
            sender=sender,
            analysis=analysis,
            suggested_slots=suggested_slots,
            local_timezone=config.timezone,
        )

        if config.enable_draft_creation and suggested_slots:
            to_address = _extract_sender_address(message)
            draft_body = (
                "Bonjour,\n\n"
                "Voici des creneaux possibles a valider manuellement:\n"
                + "\n".join(f"- {slot.label}" for slot in suggested_slots)
                + "\n\nAucun envoi automatique n'a ete effectue."
            )
            try:
                graph.create_draft_reply(
                    to_email=to_address,
                    subject=f"Re: {subject}",
                    body_text=draft_body,
                )
                print("Brouillon Outlook cree. Aucun courriel n'a ete envoye.")
            except GraphClientError as exc:
                print(f"Creation du brouillon impossible: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
