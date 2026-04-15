from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import MonitorSnapshot


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def load(self) -> MonitorSnapshot:
        if not self.path.exists():
            return MonitorSnapshot()
        with self._lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        return MonitorSnapshot.from_dict(data)

    def save(self, snapshot: MonitorSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(snapshot.to_dict(), indent=2)
        with self._lock:
            self.path.write_text(payload, encoding="utf-8")
