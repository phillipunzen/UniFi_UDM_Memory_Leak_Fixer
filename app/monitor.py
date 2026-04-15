from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from .config import Settings
from .models import MonitorSnapshot
from .notifications import NotificationManager
from .ssh_client import SSHRunner
from .state import StateStore


def parse_meminfo(raw: str) -> tuple[float, float]:
    values: dict[str, float] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts:
            continue
        values[key] = float(parts[0])
    if "MemTotal" not in values or "MemAvailable" not in values:
        raise ValueError("MemTotal or MemAvailable missing in meminfo output.")
    total_mb = values["MemTotal"] / 1024
    available_mb = values["MemAvailable"] / 1024
    return total_mb, available_mb


class MonitorService:
    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store
        self.snapshot = store.load()
        self.ssh = SSHRunner(settings)
        self.notifications = NotificationManager(settings)
        self._lock = asyncio.Lock()
        self._background_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.settings.validate()
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._background_task is not None:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

    async def trigger_check(self) -> MonitorSnapshot:
        async with self._lock:
            await self._check_once()
            return self.snapshot

    async def _run_loop(self) -> None:
        while True:
            try:
                await self.trigger_check()
            except Exception as exc:
                self.snapshot.last_status = "error"
                self.snapshot.last_error = str(exc)
                self.snapshot.add_event("error", "Scheduled check failed", error=str(exc))
                self.store.save(self.snapshot)
            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def _check_once(self) -> None:
        now = datetime.now(timezone.utc)
        total_mb, available_mb = await asyncio.to_thread(self._read_memory)
        available_percent = (available_mb / total_mb) * 100
        breached, reason = self._threshold_breached(available_mb, available_percent)

        self.snapshot.last_check_at = now.isoformat(timespec="seconds")
        self.snapshot.last_status = "ok"
        self.snapshot.last_error = None
        self.snapshot.total_mb = round(total_mb, 2)
        self.snapshot.available_mb = round(available_mb, 2)
        self.snapshot.available_percent = round(available_percent, 2)
        self.snapshot.threshold_breached = breached
        self.snapshot.add_event(
            "info",
            "Memory check completed",
            available_mb=round(available_mb, 2),
            available_percent=round(available_percent, 2),
            threshold_breached=breached,
        )

        if breached:
            await self._handle_threshold_breach(now, reason, available_mb, available_percent)

        self.store.save(self.snapshot)

    def _read_memory(self) -> tuple[float, float]:
        exit_code, stdout, stderr = self.ssh.run(self.settings.memory_check_command)
        if exit_code != 0:
            raise RuntimeError(f"Memory check command failed: {stderr.strip() or stdout.strip()}")
        return parse_meminfo(stdout)

    def _threshold_breached(self, available_mb: float, available_percent: float) -> tuple[bool, str]:
        reasons: list[str] = []
        if (
            self.settings.memory_min_available_mb is not None
            and available_mb < self.settings.memory_min_available_mb
        ):
            reasons.append(
                f"available memory {available_mb:.2f} MB below {self.settings.memory_min_available_mb} MB"
            )
        if (
            self.settings.memory_min_available_percent is not None
            and available_percent < self.settings.memory_min_available_percent
        ):
            reasons.append(
                f"available memory {available_percent:.2f}% below {self.settings.memory_min_available_percent:.2f}%"
            )
        return bool(reasons), "; ".join(reasons)

    async def _handle_threshold_breach(
        self, now: datetime, reason: str, available_mb: float, available_percent: float
    ) -> None:
        if self._restart_is_in_cooldown(now):
            self.snapshot.last_status = "cooldown"
            self.snapshot.add_event("warning", "Threshold breached but restart is cooling down", reason=reason)
            return

        self.snapshot.last_status = "restart-triggered"
        title = "UDM memory threshold reached"
        message = (
            f"{reason}\n"
            f"Current available memory: {available_mb:.2f} MB ({available_percent:.2f}%).\n"
            f"Restart command: {self.settings.service_restart_command}"
        )

        if not self.settings.dry_run_restart:
            await asyncio.to_thread(self._restart_services)
            self.snapshot.last_restart_at = now.isoformat(timespec="seconds")
            self.snapshot.service_restart_count += 1
            self.snapshot.add_event("warning", "UniFi OS services restarted", command=self.settings.service_restart_command)
        else:
            self.snapshot.add_event("warning", "Dry run active, restart skipped", command=self.settings.service_restart_command)

        try:
            sent_via = await self.notifications.send(title, message)
        except Exception as exc:
            self.snapshot.add_event("error", "Notification delivery failed", error=str(exc))
            self.snapshot.last_error = str(exc)
            return

        if sent_via:
            self.snapshot.last_notification_at = now.isoformat(timespec="seconds")
            self.snapshot.add_event("info", "Notification sent", channels=sent_via)

    def _restart_services(self) -> None:
        exit_code, stdout, stderr = self.ssh.run(self.settings.service_restart_command)
        if exit_code != 0:
            raise RuntimeError(f"Restart command failed: {stderr.strip() or stdout.strip()}")

    def _restart_is_in_cooldown(self, now: datetime) -> bool:
        if not self.snapshot.last_restart_at:
            return False
        last_restart_at = datetime.fromisoformat(self.snapshot.last_restart_at)
        if last_restart_at.tzinfo is None:
            last_restart_at = last_restart_at.replace(tzinfo=timezone.utc)
        return now - last_restart_at < timedelta(seconds=self.settings.restart_cooldown_seconds)
