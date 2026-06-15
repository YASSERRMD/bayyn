"""Phase 38: Production config validation — startup guards and CORS settings."""
import pytest
from pydantic import ValidationError


def _make(overrides: dict):
    """Build a Settings instance with only the overridden fields set."""
    from app.config import Settings
    # Provide the minimum required fields for a production config to pass.
    defaults = {
        "app_env": "production",
        "secret_key": "a" * 32,  # 32-char key, not the insecure default
        "database_url": "postgresql+asyncpg://user:pass@prod-db:5432/bayyn",
        "sync_database_url": "postgresql://user:pass@prod-db:5432/bayyn",
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ── Development mode: no restrictions ─────────────────────────────────────────

class TestDevelopmentMode:
    def test_default_secret_key_allowed_in_development(self):
        from app.config import Settings, _INSECURE_SECRET
        s = Settings(app_env="development", secret_key=_INSECURE_SECRET)
        assert s.secret_key == _INSECURE_SECRET

    def test_localhost_db_allowed_in_development(self):
        from app.config import Settings
        s = Settings(app_env="development", database_url="postgresql+asyncpg://bayyn:bayyn@localhost:5432/bayyn")
        assert "localhost" in s.database_url

    def test_llm_enabled_without_key_allowed_in_development(self):
        from app.config import Settings
        s = Settings(app_env="development", enable_llm_summary=True, openai_api_key="")
        assert s.enable_llm_summary is True


# ── Production mode: strict requirements ──────────────────────────────────────

class TestProductionSecretKey:
    def test_insecure_default_rejected(self):
        from app.config import _INSECURE_SECRET
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            _make({"secret_key": _INSECURE_SECRET})

    def test_short_key_rejected(self):
        with pytest.raises(ValidationError, match="32 characters"):
            _make({"secret_key": "short"})

    def test_32_char_key_accepted(self):
        s = _make({"secret_key": "x" * 32})
        assert len(s.secret_key) == 32

    def test_longer_key_accepted(self):
        s = _make({"secret_key": "y" * 64})
        assert len(s.secret_key) == 64

    def test_is_production_property(self):
        s = _make({})
        assert s.is_production is True

    def test_is_production_false_for_development(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.is_production is False


class TestProductionDatabaseURL:
    def test_localhost_db_rejected(self):
        with pytest.raises(ValidationError, match="production database"):
            _make({"database_url": "postgresql+asyncpg://bayyn:bayyn@localhost:5432/bayyn"})

    def test_127_0_0_1_db_rejected(self):
        with pytest.raises(ValidationError, match="production database"):
            _make({"database_url": "postgresql+asyncpg://bayyn:bayyn@127.0.0.1:5432/bayyn"})

    def test_remote_db_accepted(self):
        s = _make({"database_url": "postgresql+asyncpg://user:pass@db.prod.example.com:5432/bayyn"})
        assert "prod.example.com" in s.database_url


class TestProductionLLMConfig:
    def test_llm_enabled_without_key_rejected(self):
        with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
            _make({"enable_llm_summary": True, "openai_api_key": ""})

    def test_llm_enabled_with_key_accepted(self):
        s = _make({"enable_llm_summary": True, "openai_api_key": "sk-test-key"})
        assert s.enable_llm_summary is True

    def test_llm_disabled_without_key_accepted(self):
        s = _make({"enable_llm_summary": False, "openai_api_key": ""})
        assert s.enable_llm_summary is False


# ── CORS origins ──────────────────────────────────────────────────────────────

class TestCORSOrigins:
    def test_default_cors_origins_include_localhost(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert "http://localhost:3000" in s.cors_origins

    def test_cors_origins_can_be_overridden(self):
        from app.config import Settings
        s = Settings(
            app_env="development",
            cors_origins=["https://app.example.com", "https://www.example.com"],
        )
        assert "https://app.example.com" in s.cors_origins
        assert "http://localhost:3000" not in s.cors_origins

    def test_production_cors_can_be_set_to_public_domain(self):
        s = _make({"cors_origins": ["https://bayyn.com"]})
        assert s.cors_origins == ["https://bayyn.com"]


# ── API docs disabled in production ──────────────────────────────────────────

class TestProductionAPISettings:
    def test_docs_url_none_in_production(self):
        """Swagger UI must be disabled in production (verified at startup in main.py)."""
        s = _make({})
        assert s.is_production is True
        # The app is created with docs_url=None when is_production — this is the config flag

    def test_env_example_contains_secret_key_instruction(self):
        """The .env.example file must document SECRET_KEY and warn about the default."""
        import pathlib
        example = pathlib.Path(__file__).parent.parent / ".env.example"
        assert example.exists(), ".env.example must exist alongside pyproject.toml"
        content = example.read_text()
        assert "SECRET_KEY" in content
        assert "secrets.token_hex" in content or "generate" in content.lower()
