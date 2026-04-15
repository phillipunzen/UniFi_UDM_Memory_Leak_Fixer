# UDM Memory Controller

Kleiner Docker-Dienst fuer eine UniFi UDM Pro oder UDM SE. Die Anwendung verbindet sich per SSH, prueft regelmaessig den verfuegbaren Arbeitsspeicher, startet bei einem konfigurierbaren Schwellenwert einmalig die UniFi-OS-Dienste neu und kann Benachrichtigungen verschicken.

## Funktionen

- SSH-Verbindung zur UDM Pro mit Passwort oder Private Key
- Speicherpruefung alle 5 Minuten oder in frei konfigurierbarem Intervall
- Schwellwerte in MB und/oder Prozent verfuegbar
- Cooldown, damit bei dauerhaft niedrigem Speicher nicht in einer Schleife neu gestartet wird
- Benachrichtigungen ueber Telegram, Gotify oder SMTP/E-Mail
- Kleine WebUI mit Status, manuellem Trigger und Ereignisverlauf
- Health-Endpoint unter `/healthz`

## Schnellstart

1. `.env.example` nach `.env` kopieren und Werte anpassen.
2. Optional SSH-Key unter `./ssh/id_rsa` ablegen.
3. Container starten:

```bash
docker compose up -d --build
```

Danach ist die WebUI standardmaessig unter [http://localhost:8080](http://localhost:8080) erreichbar.

## Wichtige Konfiguration

### SSH

- `SSH_HOST`: IP oder Hostname der UDM
- `SSH_USERNAME`: meist `root`
- `SSH_PASSWORD`: alternativ zum Key
- `SSH_PRIVATE_KEY_PATH`: Pfad im Container, z. B. `/ssh/id_rsa`
- `VERIFY_HOST_KEY=false`: bequem fuer den Start, fuer produktiv besser aktivieren und Known Hosts pflegen

### Speicher-Schwellen

- `MEMORY_MIN_AVAILABLE_MB`: Restart, wenn verfuegbarer RAM darunter liegt
- `MEMORY_MIN_AVAILABLE_PERCENT`: Restart, wenn verfuegbarer RAM in Prozent darunter liegt
- Es reicht, einen der beiden Werte zu setzen. Sind beide gesetzt, loest jeder Verstoss aus.

### Restart

- `SERVICE_RESTART_COMMAND`: Standard ist `unifi-os restart`
- `RESTART_COOLDOWN_SECONDS`: Sperrzeit nach einem Restart
- `DRY_RUN_RESTART=true`: ideal zum Testen ohne echten Neustart

### Benachrichtigungen

- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Gotify: `GOTIFY_URL`, `GOTIFY_TOKEN`
- E-Mail: `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_TO`, optional Login-Daten

## Hinweise zur UDM Pro

- Auf einigen UniFi-OS-Versionen kann der passende Restart-Befehl abweichen. Falls `unifi-os restart` nicht funktioniert, bitte einen passenden Befehl in `SERVICE_RESTART_COMMAND` hinterlegen.
- Fuer den Speichercheck wird standardmaessig `cat /proc/meminfo` ausgefuehrt und `MemAvailable` ausgewertet.

## Lokale Entwicklung

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
