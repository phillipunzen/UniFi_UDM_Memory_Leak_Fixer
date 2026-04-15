from __future__ import annotations

from pathlib import Path

import paramiko

from .config import Settings


class SSHRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _build_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        if self.settings.verify_host_key:
            client.load_system_host_keys()
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    def _connect(self) -> paramiko.SSHClient:
        client = self._build_client()
        connect_args: dict[str, object] = {
            "hostname": self.settings.ssh_host,
            "port": self.settings.ssh_port,
            "username": self.settings.ssh_username,
            "timeout": self.settings.ssh_timeout_seconds,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if self.settings.ssh_password:
            connect_args["password"] = self.settings.ssh_password
        elif self._has_private_key():
            private_key = self._load_private_key()
            connect_args["pkey"] = private_key
        client.connect(**connect_args)
        return client

    def _has_private_key(self) -> bool:
        if not self.settings.ssh_private_key_path:
            return False
        return Path(self.settings.ssh_private_key_path).is_file()

    def _load_private_key(self) -> paramiko.PKey:
        key_loaders: list[type[paramiko.PKey]] = []
        for loader_name in ("RSAKey", "Ed25519Key", "ECDSAKey"):
            loader = getattr(paramiko, loader_name, None)
            if loader is not None:
                key_loaders.append(loader)

        last_error: Exception | None = None
        for loader in key_loaders:
            try:
                return loader.from_private_key_file(
                    self.settings.ssh_private_key_path,
                    password=self.settings.ssh_private_key_passphrase,
                )
            except Exception as exc:  # pragma: no cover - depends on key type
                last_error = exc
        raise RuntimeError(f"Unable to load private key: {last_error}") from last_error

    def run(self, command: str) -> tuple[int, str, str]:
        client = self._connect()
        try:
            _, stdout, stderr = client.exec_command(command, timeout=self.settings.ssh_timeout_seconds)
            exit_status = stdout.channel.recv_exit_status()
            return exit_status, stdout.read().decode(), stderr.read().decode()
        finally:
            client.close()
