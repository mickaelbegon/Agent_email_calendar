import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None


class ConfigError(RuntimeError):
    pass


WORK_START_HOUR = 9
WORK_END_HOUR = 17
DEFAULT_MEETING_DURATION_MINUTES = 30
MAX_SLOT_SUGGESTIONS = 3


READ_ONLY_GRAPH_SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "MailboxSettings.Read",
]


@dataclass(frozen=True)
class AppConfig:
    tenant_id: str
    client_id: str
    openai_api_key: str
    timezone: str
    enable_draft_creation: bool
    graph_scopes: list[str]
    work_start_hour: int = WORK_START_HOUR
    work_end_hour: int = WORK_END_HOUR
    default_meeting_duration_minutes: int = DEFAULT_MEETING_DURATION_MINUTES
    max_slot_suggestions: int = MAX_SLOT_SUGGESTIONS


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config() -> AppConfig:
    load_dotenv()

    tenant_id = os.getenv("TENANT_ID", "").strip()
    client_id = os.getenv("CLIENT_ID", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    timezone = os.getenv("TIMEZONE", "America/Montreal").strip() or "America/Montreal"
    enable_draft_creation = _env_bool("ENABLE_DRAFT_CREATION", False)

    missing = []
    if not tenant_id:
        missing.append("TENANT_ID")
    if not client_id:
        missing.append("CLIENT_ID")
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")

    if missing:
        raise ConfigError(
            "Variables d'environnement manquantes: "
            + ", ".join(missing)
            + ". Copiez .env.example vers .env puis renseignez les valeurs."
        )

    scopes = list(READ_ONLY_GRAPH_SCOPES)
    if enable_draft_creation:
        scopes.append("Mail.ReadWrite")

    return AppConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        openai_api_key=openai_api_key,
        timezone=timezone,
        enable_draft_creation=enable_draft_creation,
        graph_scopes=scopes,
    )
