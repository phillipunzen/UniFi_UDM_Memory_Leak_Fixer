from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    return int(value)


def _as_float(value: str | None, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    return float(value)


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "UDM Memory Controller")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _as_int(os.getenv("PORT"), 8080) or 8080
    timezone: str = os.getenv("TIMEZONE", "Europe/Berlin")
    state_file: Path = Path(os.getenv("STATE_FILE", "/data/state.json"))
    poll_interval_seconds: int = _as_int(os.getenv("POLL_INTERVAL_SECONDS"), 300) or 300
    restart_cooldown_seconds: int = _as_int(os.getenv("RESTART_COOLDOWN_SECONDS"), 3600) or 3600
    ssh_host: str = os.getenv("SSH_HOST", "")
    ssh_port: int = _as_int(os.getenv("SSH_PORT"), 22) or 22
    ssh_username: str = os.getenv("SSH_USERNAME", "root")
    ssh_password: str | None = os.getenv("SSH_PASSWORD")
    ssh_private_key_path: str | None = os.getenv("SSH_PRIVATE_KEY_PATH")
    ssh_private_key_passphrase: str | None = os.getenv("SSH_PRIVATE_KEY_PASSPHRASE")
    ssh_timeout_seconds: int = _as_int(os.getenv("SSH_TIMEOUT_SECONDS"), 15) or 15
    verify_host_key: bool = _as_bool(os.getenv("VERIFY_HOST_KEY"), False)
    memory_min_available_mb: int | None = _as_int(os.getenv("MEMORY_MIN_AVAILABLE_MB"))
    memory_min_available_percent: float | None = _as_float(os.getenv("MEMORY_MIN_AVAILABLE_PERCENT"))
    memory_check_command: str = os.getenv("MEMORY_CHECK_COMMAND", "cat /proc/meminfo")
    device_name_command: str = os.getenv("DEVICE_NAME_COMMAND", "hostname")
    service_restart_command: str = os.getenv("SERVICE_RESTART_COMMAND", "unifi-os restart")
    dry_run_restart: bool = _as_bool(os.getenv("DRY_RUN_RESTART"), False)
    ui_username: str | None = os.getenv("UI_USERNAME")
    ui_password: str | None = os.getenv("UI_PASSWORD")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    gotify_url: str | None = os.getenv("GOTIFY_URL")
    gotify_token: str | None = os.getenv("GOTIFY_TOKEN")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = _as_int(os.getenv("SMTP_PORT"), 587) or 587
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from: str | None = os.getenv("SMTP_FROM")
    smtp_to: str | None = os.getenv("SMTP_TO")
    smtp_use_tls: bool = _as_bool(os.getenv("SMTP_USE_TLS"), True)

    def validate(self) -> None:
        if not self.ssh_host:
            raise ValueError("SSH_HOST must be configured.")
        if self.memory_min_available_mb is None and self.memory_min_available_percent is None:
            raise ValueError(
                "Configure MEMORY_MIN_AVAILABLE_MB and/or MEMORY_MIN_AVAILABLE_PERCENT."
            )


settings = Settings()
