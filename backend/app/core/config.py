"""Application configuration.

All configuration is environment driven. Nothing environment specific (URLs, keys,
model identifiers) is hard-coded anywhere else in the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AIProviderName = Literal["mock", "gemini"]
GroundingProviderName = Literal["none", "mock", "gemini"]


class Settings(BaseSettings):
    """Runtime settings, loaded from the environment and an optional ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application ---------------------------------------------------------
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "AI Creative Copy Agent"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    # -- Database ------------------------------------------------------------
    database_url: str = "sqlite:///./creative_copy.db"
    # Convenience for local development: create tables at startup when no
    # migration has been run yet. Always false in production deployments.
    auto_create_tables: bool = True
    seed_on_startup: bool = True

    # -- Security ------------------------------------------------------------
    jwt_secret_key: str = "development-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    refresh_cookie_name: str = "ccagent_refresh"
    allow_registration: bool = True

    # -- CORS / limits -------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    request_max_bytes: int = 1_048_576
    rate_limit_login: str = "10/minute"
    rate_limit_generation: str = "20/hour"
    rate_limit_enabled: bool = True

    # -- AI providers --------------------------------------------------------
    ai_provider: AIProviderName = "mock"
    gemini_api_key: str | None = None
    gemini_flash_model: str | None = None
    gemini_pro_model: str | None = None
    gemini_timeout_seconds: float = 60.0
    grounding_enabled: bool = False
    grounding_provider: GroundingProviderName = "none"
    # Simulated per-stage latency for the mock provider, so the workflow UI can
    # be exercised end to end without a real model.
    mock_stage_delay_ms: int = 220

    # -- Generation behaviour ------------------------------------------------
    repetition_similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    repetition_history_size: int = 10
    generation_timeout_seconds: float = 120.0

    # -- Channel character limits (configurable per §13 of the spec) ---------
    limit_email_headline: int = 80
    limit_email_sub_heading: int = 160
    limit_email_cta: int = 40
    limit_mobile_superline: int = 30
    limit_mobile_pre_heading: int = 50
    limit_mobile_headline: int = 70
    limit_mobile_sub_heading: int = 140
    limit_mobile_cta: int = 40
    limit_sms_description: int = 160

    # -- Observability -------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

    # -- Development seed users ---------------------------------------------
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "ChangeMe123!"
    seed_marketer_email: str = "marketer@example.com"
    seed_marketer_password: str = "ChangeMe123!"

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Settings:
        if self.app_env == "production":
            if self.jwt_secret_key == "development-only-insecure-secret-change-me":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a unique value when APP_ENV=production"
                )
            if self.auto_create_tables:
                raise ValueError(
                    "AUTO_CREATE_TABLES must be false in production; run Alembic migrations"
                )
            if self.seed_on_startup:
                raise ValueError("SEED_ON_STARTUP must be false in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env in ("development", "test")

    @property
    def channel_limits(self) -> dict[str, dict[str, int]]:
        """Character limits per channel field, used by validation and prompts."""
        return {
            "email": {
                "headline": self.limit_email_headline,
                "sub_heading": self.limit_email_sub_heading,
                "cta": self.limit_email_cta,
            },
            "mobile": {
                "superline": self.limit_mobile_superline,
                "pre_heading": self.limit_mobile_pre_heading,
                "headline": self.limit_mobile_headline,
                "sub_heading": self.limit_mobile_sub_heading,
                "cta": self.limit_mobile_cta,
            },
            "sms": {"description": self.limit_sms_description},
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency and at import time."""
    return Settings()


settings = get_settings()
