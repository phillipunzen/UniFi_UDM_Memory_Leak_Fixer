from app.monitor import parse_meminfo
from app.ssh_client import SSHRunner
from app.config import Settings


def test_parse_meminfo_extracts_total_and_available_mb() -> None:
    raw = """MemTotal:        4096000 kB
MemFree:          512000 kB
MemAvailable:    1024000 kB
Buffers:          128000 kB
"""
    total_mb, available_mb = parse_meminfo(raw)
    assert total_mb == 4000.0
    assert available_mb == 1000.0


def test_password_auth_is_preferred_over_private_key_path() -> None:
    settings = Settings(
        ssh_host="192.168.1.1",
        ssh_username="root",
        ssh_password="secret",
        ssh_private_key_path="/ssh/id_rsa",
        memory_min_available_percent=10,
    )

    runner = SSHRunner(settings)

    assert runner._has_private_key() is False
