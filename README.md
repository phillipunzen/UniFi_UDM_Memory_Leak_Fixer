# UDM Memory Controller

A lightweight Docker service for UniFi UDM Pro or UDM SE devices. It connects over SSH, checks available memory on a schedule, restarts UniFi OS services when a configurable threshold is crossed, and can send notifications.

## Features

- SSH connectivity to the UDM Pro using either password or private key authentication
- Memory checks every 5 minutes by default, with a configurable polling interval
- Thresholds based on available memory in MB and/or percent
- Restart cooldown protection to avoid repeated restart loops
- Notifications via Telegram, Gotify, or SMTP email
- Small Web UI with current status, manual trigger, and event history
- Health endpoint at `/healthz`

## Quick Start

1. Copy `.env.example` to `.env` and adjust the values.
2. Optionally place an SSH private key in `./ssh/id_rsa`.
3. Start the container:

```bash
docker compose up -d --build
```

The Web UI will then be available at [http://localhost:8080](http://localhost:8080) by default.

## Important Configuration

### SSH

- `SSH_HOST`: IP address or hostname of the UDM
- `SSH_USERNAME`: usually `root`
- `SSH_PASSWORD`: use this if you prefer password authentication
- `SSH_PRIVATE_KEY_PATH`: path inside the container, for example `/ssh/id_rsa`
- If you are using password authentication, leave `SSH_PRIVATE_KEY_PATH` empty
- `VERIFY_HOST_KEY=false`: convenient for first setup, but enabling host key verification is recommended for production use

### Memory Thresholds

- `MEMORY_MIN_AVAILABLE_MB`: restart when available memory drops below this value
- `MEMORY_MIN_AVAILABLE_PERCENT`: restart when available memory drops below this percentage
- You only need to set one of them. If both are set, either condition can trigger a restart.

Example:

```env
MEMORY_MIN_AVAILABLE_PERCENT=15
```

This means the service will restart UniFi OS services if available memory falls below `15%`.

### Restart Behavior

- `SERVICE_RESTART_COMMAND`: defaults to `unifi-os restart`
- `RESTART_COOLDOWN_SECONDS`: cooldown period after a restart
- `DRY_RUN_RESTART=true`: useful for testing without performing a real restart

### Notifications

- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Gotify: `GOTIFY_URL`, `GOTIFY_TOKEN`
- Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_TO`, plus optional authentication settings

## Notes for UDM Pro

- On some UniFi OS versions, the correct restart command may differ. If `unifi-os restart` does not work on your system, set `SERVICE_RESTART_COMMAND` to the correct command for your device.
- The memory check uses `cat /proc/meminfo` by default and evaluates `MemAvailable`.

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
