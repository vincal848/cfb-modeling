"""CFBD credential handling. The key is read from the environment and never logged."""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "CFBD_API_KEY"

SETUP_INSTRUCTIONS = f"""\
{ENV_VAR} is not set. Live CFBD calls are disabled; synthetic-fixture work still runs.

To enable live access with your Tier 3 subscription:
  1. Copy your key from https://collegefootballdata.com (account page).
  2. Set it for your user (PowerShell, persists across sessions):
       [Environment]::SetEnvironmentVariable("{ENV_VAR}", "<your key>", "User")
     or for the current shell only:
       $env:{ENV_VAR} = "<your key>"
     or put it in a git-ignored .env file at the repo root (see .env.example).
  3. Open a new terminal and run:  uv run cfb doctor
"""


class MissingCredentialError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(SETUP_INSTRUCTIONS)


def _read_dotenv(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and name.strip() == ENV_VAR:
            return value.strip().strip('"').strip("'") or None
    return None


def get_api_key(dotenv: Path | None = None) -> str | None:
    """Return the key from the environment, falling back to a local .env file."""
    key = os.environ.get(ENV_VAR, "").strip()
    if key:
        return key
    if dotenv is None:
        from cfb.config import REPO_ROOT

        dotenv = REPO_ROOT / ".env"
    return _read_dotenv(dotenv)


def require_api_key(dotenv: Path | None = None) -> str:
    key = get_api_key(dotenv)
    if not key:
        raise MissingCredentialError()
    return key


def redact(text: str, key: str | None) -> str:
    """Remove the key from any string bound for logs, ledgers, or exceptions."""
    if not key:
        return text
    return text.replace(key, "***REDACTED***")
