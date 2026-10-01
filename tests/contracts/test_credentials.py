import pytest

from cfb import credentials


def test_missing_key_gives_setup_instructions(monkeypatch, tmp_path):
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    assert credentials.get_api_key(dotenv=tmp_path / ".env") is None
    with pytest.raises(credentials.MissingCredentialError, match="SetEnvironmentVariable"):
        credentials.require_api_key(dotenv=tmp_path / ".env")


def test_env_takes_precedence_over_dotenv(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("CFBD_API_KEY=from-file\n")
    monkeypatch.setenv("CFBD_API_KEY", "from-env")
    assert credentials.get_api_key(dotenv=tmp_path / ".env") == "from-env"
    monkeypatch.delenv("CFBD_API_KEY")
    assert credentials.get_api_key(dotenv=tmp_path / ".env") == "from-file"


def test_redact_removes_key():
    msg = "GET /games Authorization: Bearer s3cr3t failed"
    assert "s3cr3t" not in credentials.redact(msg, "s3cr3t")
