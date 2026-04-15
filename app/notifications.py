from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from .config import Settings


class NotificationManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, title: str, message: str) -> list[str]:
        sent_via: list[str] = []
        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            await self._send_telegram(title, message)
            sent_via.append("telegram")
        if self.settings.gotify_url and self.settings.gotify_token:
            await self._send_gotify(title, message)
            sent_via.append("gotify")
        if self.settings.smtp_host and self.settings.smtp_to and self.settings.smtp_from:
            await self._send_email(title, message)
            sent_via.append("email")
        return sent_via

    async def _send_telegram(self, title: str, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": f"*{title}*\n\n{message}",
            "parse_mode": "Markdown",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    async def _send_gotify(self, title: str, message: str) -> None:
        url = self.settings.gotify_url.rstrip("/") + "/message"
        headers = {"X-Gotify-Key": self.settings.gotify_token}
        payload = {"title": title, "message": message, "priority": 5}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

    async def _send_email(self, title: str, message: str) -> None:
        email = EmailMessage()
        email["Subject"] = title
        email["From"] = self.settings.smtp_from
        email["To"] = self.settings.smtp_to
        email.set_content(message)

        def _deliver() -> None:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(email)

        import asyncio

        await asyncio.to_thread(_deliver)
