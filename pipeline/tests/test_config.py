import pytest
from opendq.config import Settings


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings.from_env()


def test_settings_use_public_endpoint_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.delenv("OPEN_METEO_BASE_URL", raising=False)
    monkeypatch.delenv("USGS_BASE_URL", raising=False)

    settings = Settings.from_env()

    assert settings.open_meteo_base_url == "https://api.open-meteo.com/v1/forecast"
    assert settings.usgs_base_url.startswith("https://earthquake.usgs.gov/")
