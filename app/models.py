from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Event:
    timestamp: str
    level: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MonitorSnapshot:
    device_name: str | None = None
    last_check_at: str | None = None
    last_restart_at: str | None = None
    last_notification_at: str | None = None
    last_status: str = "never-run"
    last_error: str | None = None
    available_mb: float | None = None
    available_percent: float | None = None
    total_mb: float | None = None
    threshold_breached: bool = False
    service_restart_count: int = 0
    memory_history: list[dict[str, float | str]] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    def add_event(self, level: str, message: str, **details: Any) -> None:
        event = Event(
            timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            level=level,
            message=message,
            details=details,
        )
        self.events.insert(0, event)
        del self.events[50:]

    def add_memory_sample(self, timestamp: str, available_mb: float, available_percent: float) -> None:
        self.memory_history.append(
            {
                "timestamp": timestamp,
                "available_mb": round(available_mb, 2),
                "available_percent": round(available_percent, 2),
            }
        )
        del self.memory_history[:-72]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["events"] = [asdict(event) for event in self.events]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonitorSnapshot":
        events = [Event(**event) for event in data.get("events", [])]
        snapshot_data = {key: value for key, value in data.items() if key != "events"}
        return cls(events=events, **snapshot_data)
