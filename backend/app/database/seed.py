"""Development seed data (§10, §21).

Idempotent: running it twice makes no further changes. The seeded accounts are for
local development only and must be changed or removed before any deployment.

Run standalone with::

    python -m app.database.seed
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.models.enums import Channel, Role
from app.repositories.taxonomy_repository import (
    AudienceSegmentRepository,
    BrandRepository,
    CTARuleRepository,
    ProductRepository,
    TemplateRepository,
)
from app.repositories.user_repository import UserRepository

logger = get_logger("app.seed")

AUDIENCE_SEGMENTS = [
    {
        "name": "Trendsetters",
        "description": "Style-forward customers looking for distinctive products.",
        "tone_guidance": (
            "Confident and fashion-led. Lead with design, exclusivity and standout style."
        ),
    },
    {
        "name": "Enthusiasts",
        "description": "Passionate customers focused on product details and exclusivity.",
        "tone_guidance": (
            "Knowledgeable and specific. Reference craft, materials and technical detail."
        ),
    },
    {
        "name": "Performance Seekers",
        "description": "Active customers prioritizing function, reliability, and performance.",
        "tone_guidance": (
            "Energetic and direct. Lead with performance benefits, durability and results."
        ),
    },
    {
        "name": "General / All",
        "description": "Broad audiences valuing style, comfort, quality, and versatility.",
        "tone_guidance": "Warm, clear and inclusive. Avoid jargon and niche references.",
    },
]

BRANDS = [
    {
        "name": "AeroFlex",
        "description": "Performance running and training footwear.",
        "guidelines": (
            "Confident, active and inclusive. Never claim medical or injury-prevention "
            "benefits. Always capitalise the brand as AeroFlex."
        ),
    },
    {
        "name": "Northline",
        "description": "Everyday outdoor apparel and accessories.",
        "guidelines": (
            "Calm, practical and understated. Avoid superlatives and unverified "
            "sustainability claims."
        ),
    },
]

PRODUCTS = [
    {
        "brand": "AeroFlex",
        "name": "AeroFlex Running Shoes",
        "sku": "AF-RUN-001",
        "description": (
            "Lightweight, breathable running shoes built for speed and comfort, "
            "available in four colorways."
        ),
        "features": "lightweight, breathable, speed, comfort, durability, responsive cushioning, "
        "modern design",
    },
    {
        "brand": "AeroFlex",
        "name": "AeroFlex Trail Pro",
        "sku": "AF-TRL-002",
        "description": "Grip-focused trail shoes for mixed terrain.",
        "features": "durability, grip, comfort, performance",
    },
    {
        "brand": "Northline",
        "name": "Northline Rain Shell",
        "sku": "NL-RSH-010",
        "description": "A packable waterproof shell for everyday conditions.",
        "features": "waterproof, breathable, lightweight, versatility",
    },
]

# Highest priority wins; a rule is skipped when its placeholders cannot be filled.
CTA_RULES = [
    {"template": "SHOP {product}", "priority": 100, "channel": None},
    {"template": "EXPLORE {brand}", "priority": 50, "channel": None},
    {"template": "SHOP THE COLLECTION", "priority": 10, "channel": None},
]

TEMPLATES = [
    {
        "name": "Email launch announcement",
        "channel": Channel.EMAIL.value,
        "description": "Standard product launch email with headline, sub-heading and CTA.",
        "prompt_template": (
            "Write launch email copy. The headline should carry the key campaign message. "
            "The sub-heading should introduce the product and name two concrete benefits. "
            "Keep the tone aligned to the audience segment."
        ),
    },
    {
        "name": "Mobile push launch",
        "channel": Channel.MOBILE.value,
        "description": "Push/in-app layout with superline, pre-heading, headline and sub-heading.",
        "prompt_template": (
            "Write mobile copy. The superline is a short label in capitals. The pre-heading "
            "names the brand and audience. The headline must fit on one line."
        ),
    },
    {
        "name": "SMS promotional blast",
        "channel": Channel.SMS.value,
        "description": "Single promotional description within the SMS character budget.",
        "prompt_template": (
            "Write one SMS promotional sentence. Lead with the product, name one benefit, "
            "and close with a short action."
        ),
    },
]


def seed_users(session: Session) -> None:
    repo = UserRepository(session)
    accounts = [
        ("Admin User", settings.seed_admin_email, settings.seed_admin_password, Role.ADMIN),
        (
            "Marketing User",
            settings.seed_marketer_email,
            settings.seed_marketer_password,
            Role.MARKETER,
        ),
    ]
    for name, email, password, role in accounts:
        if repo.get_by_email(email):
            continue
        repo.create(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        logger.info("seeded user", extra={"email": email, "role": str(role)})


def seed_taxonomy(session: Session) -> None:
    brands = BrandRepository(session)
    products = ProductRepository(session)
    segments = AudienceSegmentRepository(session)
    rules = CTARuleRepository(session)
    templates = TemplateRepository(session)

    for payload in AUDIENCE_SEGMENTS:
        if not segments.get_by_name(payload["name"]):
            segments.create(**payload, is_active=True)

    brand_ids: dict[str, int] = {}
    for payload in BRANDS:
        brand = brands.get_by_name(payload["name"])
        if brand is None:
            brand = brands.create(**payload, is_active=True)
        brand_ids[brand.name] = brand.id

    for payload in PRODUCTS:
        if products.get_by_name(payload["name"]):
            continue
        data = dict(payload)
        brand_name = data.pop("brand")
        products.create(brand_id=brand_ids[brand_name], **data, is_active=True)

    existing_templates = {rule.template for rule in rules.list(limit=200)[0]}
    for payload in CTA_RULES:
        if payload["template"] in existing_templates:
            continue
        rules.create(**payload, is_active=True)

    existing_names = {template.name for template in templates.list(limit=200)[0]}
    for payload in TEMPLATES:
        if payload["name"] in existing_names:
            continue
        templates.create(**payload, is_active=True)


def seed_all(session: Session) -> None:
    """Seed users and taxonomy. Safe to call on every startup."""
    seed_users(session)
    seed_taxonomy(session)
    session.commit()
    logger.info("seed data applied")


def main() -> None:  # pragma: no cover - CLI entry point
    from app.database.base import Base
    from app.database.session import engine, session_scope

    configure_logging()
    Base.metadata.create_all(bind=engine)
    with session_scope() as session:
        seed_all(session)
    print("Seed data applied.")
    print(f"  admin:    {settings.seed_admin_email} / {settings.seed_admin_password}")
    print(f"  marketer: {settings.seed_marketer_email} / {settings.seed_marketer_password}")
    print("These credentials are for local development only.")


if __name__ == "__main__":  # pragma: no cover
    main()
