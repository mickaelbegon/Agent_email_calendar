import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None


class ConfigError(RuntimeError):
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer.") from exc


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    llm_mode: str
    timezone: str
    dry_run: bool
    output_dir: Path
    input_dir: Path
    max_emails: int
    create_ics: bool
    personal_work_max_block_minutes: int


def load_config() -> AppConfig:
    load_dotenv()

    llm_mode = os.getenv("LLM_MODE", "rules").strip().lower() or "rules"
    if llm_mode not in {"rules", "openai"}:
        raise ConfigError("LLM_MODE must be either 'rules' or 'openai'.")

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if llm_mode == "openai" and not openai_api_key:
        raise ConfigError("OPENAI_API_KEY is required when LLM_MODE=openai.")

    return AppConfig(
        openai_api_key=openai_api_key,
        llm_mode=llm_mode,
        timezone=os.getenv("TIMEZONE", "America/Montreal").strip() or "America/Montreal",
        dry_run=_env_bool("DRY_RUN", True),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
        input_dir=Path(os.getenv("INPUT_DIR", "input_emails")),
        max_emails=_env_int("MAX_EMAILS", 5),
        create_ics=_env_bool("CREATE_ICS", False),
        personal_work_max_block_minutes=_env_int("PERSONAL_WORK_MAX_BLOCK_MINUTES", 120),
    )

