from app.monitor import parse_meminfo


def test_parse_meminfo_extracts_total_and_available_mb() -> None:
    raw = """MemTotal:        4096000 kB
MemFree:          512000 kB
MemAvailable:    1024000 kB
Buffers:          128000 kB
"""
    total_mb, available_mb = parse_meminfo(raw)
    assert total_mb == 4000.0
    assert available_mb == 1000.0
