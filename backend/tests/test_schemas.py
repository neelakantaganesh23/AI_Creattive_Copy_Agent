"""Schema validation, security primitives and rate-limit unit tests (§18)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.errors import TokenError
from app.core.logging import redact
from app.core.rate_limit import RateLimiter, RateLimitPolicy
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.schemas.copy_output import (
    CopyBundle,
    EmailCopy,
    MobileCopy,
    SMSCopy,
    check_channel_limits,
)
from app.schemas.generation import GenerationCreate
from app.utils.text import similarity, slugify_title, truncate


# -- Copy schemas -----------------------------------------------------------
def test_email_copy_requires_every_field() -> None:
    with pytest.raises(PydanticValidationError):
        EmailCopy(headline="Only a headline")


def test_copy_fields_are_collapsed_to_one_line() -> None:
    copy = EmailCopy(headline="Run\n lighter", sub_heading="A  b", cta="SHOP")
    assert copy.headline == "Run lighter"
    assert copy.sub_heading == "A b"


def test_check_channel_limits_flags_overlong_fields() -> None:
    bundle = CopyBundle(
        email=EmailCopy(headline="x" * 200, sub_heading="fine", cta="SHOP"),
        mobile=MobileCopy(
            superline="NEW",
            pre_heading="Brand",
            headline="fine",
            sub_heading="fine",
            cta="SHOP",
        ),
        sms=SMSCopy(description="fine"),
    )
    warnings = check_channel_limits(bundle)
    assert len(warnings) == 1
    assert "EMAIL headline" in warnings[0]


def test_check_channel_limits_passes_valid_copy() -> None:
    bundle = CopyBundle(
        email=EmailCopy(headline="Short", sub_heading="Short", cta="SHOP"),
        mobile=MobileCopy(
            superline="NEW", pre_heading="Brand", headline="Short", sub_heading="Short", cta="SHOP"
        ),
        sms=SMSCopy(description="Short"),
    )
    assert check_channel_limits(bundle) == []


# -- Generation request -----------------------------------------------------
def test_brief_length_bounds_are_enforced() -> None:
    with pytest.raises(PydanticValidationError):
        GenerationCreate(brief="short", channel="email")
    with pytest.raises(PydanticValidationError):
        GenerationCreate(brief="x" * 4001, channel="email")


def test_brief_is_trimmed() -> None:
    payload = GenerationCreate(brief="  " + "a" * 40 + "  ", channel="email")
    assert payload.brief == "a" * 40


# -- Security ---------------------------------------------------------------
def test_password_round_trip() -> None:
    hashed = hash_password("ChangeMe123!")
    assert hashed != "ChangeMe123!"
    assert verify_password("ChangeMe123!", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_verify_password_tolerates_malformed_hashes() -> None:
    assert verify_password("anything", "not-a-hash") is False


def test_password_over_bcrypt_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("x" * 73)


def test_access_token_round_trip() -> None:
    token, _expires = create_access_token("42", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_tampered_token_is_rejected() -> None:
    token, _expires = create_access_token("42", role="admin")
    with pytest.raises(TokenError):
        decode_access_token(token + "tampered")


def test_refresh_tokens_are_hashed_not_stored() -> None:
    assert hash_token("secret-token") != "secret-token"
    assert len(hash_token("secret-token")) == 64


# -- Logging redaction ------------------------------------------------------
def test_redact_masks_credential_like_keys() -> None:
    payload = redact(
        {
            "password": "hunter2",
            "authorization": "Bearer abc",
            "gemini_api_key": "key",
            "nested": {"refresh_token": "abc", "safe": "value"},
        }
    )
    assert payload["password"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["gemini_api_key"] == "[REDACTED]"
    assert payload["nested"]["refresh_token"] == "[REDACTED]"
    assert payload["nested"]["safe"] == "value"


# -- Rate limiting ----------------------------------------------------------
def test_rate_limiter_blocks_past_the_limit() -> None:
    clock = [0.0]
    limiter = RateLimiter(clock=lambda: clock[0])
    policy = RateLimitPolicy.parse("2/minute")

    assert limiter.check("login", "1.1.1.1", policy).allowed
    assert limiter.check("login", "1.1.1.1", policy).allowed
    blocked = limiter.check("login", "1.1.1.1", policy)
    assert not blocked.allowed
    assert blocked.retry_after_seconds > 0

    # A different client has its own budget.
    assert limiter.check("login", "2.2.2.2", policy).allowed

    # The window rolls forward.
    clock[0] = 61.0
    assert limiter.check("login", "1.1.1.1", policy).allowed


def test_rate_limit_policy_parsing() -> None:
    assert RateLimitPolicy.parse("20/hour") == RateLimitPolicy(20, 3600)
    with pytest.raises(ValueError, match="Invalid rate limit"):
        RateLimitPolicy.parse("20/fortnight")


# -- Text helpers -----------------------------------------------------------
def test_similarity_bounds() -> None:
    assert similarity("run lighter", "run lighter") == pytest.approx(1.0)
    assert similarity("run lighter", "") == 0.0


def test_truncate_prefers_word_boundaries() -> None:
    assert truncate("Run lighter and go farther", 15) == "Run lighter"
    assert truncate("Short", 20) == "Short"


def test_slugify_title_uses_the_first_sentence() -> None:
    assert slugify_title("We are launching AeroFlex. More detail follows.") == (
        "We are launching AeroFlex."
    )
    assert slugify_title("   ") == "Untitled campaign"
