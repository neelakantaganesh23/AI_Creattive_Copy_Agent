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
GroundingProviderName = Literal["none", "mock", "gemini", "tavily"]


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

    # -- Google sign-in ------------------------------------------------------
    # Empty disables the feature; the frontend hides the button to match.
    google_client_id: str | None = None
    # Role granted to accounts auto-created on first Google sign-in.
    google_default_role: Literal["admin", "marketer", "viewer"] = "marketer"

    # -- Password reset ------------------------------------------------------
    password_reset_expire_minutes: int = 30
    rate_limit_password_reset: str = "5/hour"
    # Used to build the link in the reset email.
    frontend_base_url: str = "http://localhost:5173"
    # This backend's own externally-reachable origin. Used to build absolute
    # media URLs (e.g. a generated image) for contexts, like email, that can't
    # resolve a path relative to the app.
    public_base_url: str = "http://localhost:8000"
    email_provider: Literal["console", "smtp", "resend"] = "console"
    email_from: str = "AI Creative Copy Agent <no-reply@example.com>"
    resend_api_key: str | None = None
    resend_api_url: str = "https://api.resend.com/emails"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    email_timeout_seconds: float = 15.0

    # -- CORS / limits -------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    request_max_bytes: int = 1_048_576
    rate_limit_login: str = "10/minute"
    rate_limit_generation: str = "20/hour"
    # Self-test-send only ever mails the logged-in user's own inbox, but is
    # still rate-limited to keep a stray retry loop from hammering the sender.
    rate_limit_test_email: str = "10/hour"
    rate_limit_enabled: bool = True

    # -- AI providers --------------------------------------------------------
    ai_provider: AIProviderName = "mock"
    gemini_api_key: str | None = None
    gemini_flash_model: str | None = None
    gemini_pro_model: str | None = None
    gemini_timeout_seconds: float = 60.0
    grounding_enabled: bool = False
    grounding_provider: GroundingProviderName = "none"
    tavily_api_key: str | None = None
    tavily_api_url: str = "https://api.tavily.com/search"
    tavily_max_results: int = 5
    # "basic" costs one credit per search; "advanced" costs more.
    tavily_search_depth: Literal["basic", "advanced"] = "basic"
    tavily_timeout_seconds: float = 20.0
    # Simulated per-stage latency for the mock provider, so the workflow UI can
    # be exercised end to end without a real model.
    mock_stage_delay_ms: int = 220

    # -- Generation behaviour ------------------------------------------------
    repetition_similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    repetition_history_size: int = 10
    generation_timeout_seconds: float = 120.0

    # -- Agent runtime -------------------------------------------------------
    # How many times an agent may be asked to correct itself when its output
    # fails rule validation, before the best attempt is accepted with warnings.
    agent_retries: int = Field(default=2, ge=0, le=5)
    agent_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    # Upper bound on model requests within a single agent run.
    agent_request_limit: int = Field(default=6, ge=1)

    # -- Image generation ------------------------------------------------------
    image_generation_enabled: bool = True
    # mock | gemini | stability. Independent of AI_PROVIDER: text and image
    # generation can use different backends, e.g. Gemini for copy with Stability
    # for images if Gemini's image quota is unavailable.
    image_provider: Literal["mock", "gemini", "stability"] = "mock"
    # Required when IMAGE_PROVIDER=gemini. Must be a model with native image
    # output, e.g. "gemini-3-pro-image" -- never hard-coded.
    gemini_image_model: str | None = None
    # Required when IMAGE_PROVIDER=stability.
    stability_api_key: str | None = None
    stability_api_url: str = "https://api.stability.ai/v2beta/stable-image/generate/core"
    stability_output_format: Literal["png", "jpeg", "webp"] = "png"
    stability_timeout_seconds: float = 60.0
    # Ratios both the Gemini and Stability APIs accept, so switching provider
    # never needs a config change here too.
    image_aspect_ratio: Literal["1:1", "2:3", "3:2", "4:5", "5:4", "9:16", "16:9", "21:9"] = "1:1"
    # Local disk directory generated images are written to, served at MEDIA_URL_PREFIX.
    media_dir: str = "./media"
    media_url_prefix: str = "/media"

    # -- LLM-as-Judge --------------------------------------------------------
    judge_enabled: bool = True
    # Verdicts should be stable run to run, so the judge runs much colder than
    # the copywriter.
    judge_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    judge_min_score: float = Field(default=0.7, ge=0.0, le=1.0)
    # Rewrites attempted when the judge rejects the copy. Copy is never
    # discarded: after the last attempt it is returned with warnings.
    judge_max_revisions: int = Field(default=1, ge=0, le=3)

    # -- Channel character limits --------------------------------------------
    # Seed defaults only. Once a database exists, content rules are managed by
    # admins through the Rules UI and the ``rules`` table is authoritative;
    # these values are used to seed that table on a fresh install.
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

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        """Point bare PostgreSQL URLs at psycopg 3.

        Hosted providers hand out ``postgres://`` or ``postgresql://`` URLs, which
        SQLAlchemy resolves to psycopg2 -- a driver this project does not install.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @field_validator(
        "gemini_api_key",
        "gemini_flash_model",
        "gemini_pro_model",
        "gemini_image_model",
        "stability_api_key",
        "google_client_id",
        "tavily_api_key",
        "resend_api_key",
        "smtp_host",
        "smtp_username",
        "smtp_password",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, value: str | None) -> str | None:
        """``KEY=`` in a .env file means "not configured", not an empty value."""
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

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
    def google_login_enabled(self) -> bool:
        return bool(self.google_client_id)

    @property
    def channel_limits(self) -> dict[str, dict[str, int]]:
        """Character limits per channel field, used to seed the ``rules`` table.

        Not consulted during generation -- the rules engine reads the database.
        """
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
