"""content rules and the validation stage

Creates the ``rules`` table and seeds it from the ``LIMIT_*`` defaults that were
previously enforced from configuration, so an existing deployment keeps exactly
the character limits it had before the upgrade. From here on the table is the
source of truth and admins edit it through the UI.

Revision ID: 0003_content_rules
Revises: 0002_google_signin_password_reset
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003_content_rules'
down_revision: str | None = '0002_google_signin_password_reset'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (channel, field, max characters) mirroring the previous LIMIT_* defaults.
_SEEDED_LIMITS: tuple[tuple[str, str, int], ...] = (
    ("email", "headline", 80),
    ("email", "sub_heading", 160),
    ("email", "cta", 40),
    ("mobile", "superline", 30),
    ("mobile", "pre_heading", 50),
    ("mobile", "headline", 70),
    ("mobile", "sub_heading", 140),
    ("mobile", "cta", 40),
    ("sms", "description", 160),
)

_SEEDED_GUIDELINES: tuple[tuple[str, str, str], ...] = (
    (
        "Sounds natural",
        "The copy must read like something a person would say out loud. No keyword "
        "stuffing, no robotic phrasing, no stacked adjectives.",
        "error",
    ),
    (
        "No internal repetition",
        "No two fields may reuse the same distinctive phrase or sentence shape.",
        "warning",
    ),
)


def upgrade() -> None:
    op.create_table(
        'rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=30), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=True),
        sa.Column('field_name', sa.String(length=40), nullable=True),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('audience_segment_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['audience_segment_id'], ['audience_segments.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('rules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rules_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_rules_rule_type'), ['rule_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_rules_channel'), ['channel'], unique=False)
        batch_op.create_index(batch_op.f('ix_rules_brand_id'), ['brand_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_rules_audience_segment_id'), ['audience_segment_id'], unique=False
        )

    _seed()


def _seed() -> None:
    """Reproduce the previous configuration-driven limits as rows."""
    rules = sa.table(
        'rules',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('rule_type', sa.String),
        sa.column('value', sa.Text),
        sa.column('severity', sa.String),
        sa.column('channel', sa.String),
        sa.column('field_name', sa.String),
        sa.column('priority', sa.Integer),
        sa.column('is_active', sa.Boolean),
    )

    rows = [
        {
            "name": f"{channel.upper()} {field.replace('_', ' ')} length",
            "description": "Seeded from the character limit this deployment already used.",
            "rule_type": "max_chars",
            "value": str(limit),
            # Error severity means the model is asked to rewrite rather than the
            # overrun merely being reported, which is the point of the change.
            "severity": "error",
            "channel": channel,
            "field_name": field,
            "priority": 100,
            "is_active": True,
        }
        for channel, field, limit in _SEEDED_LIMITS
    ]
    rows += [
        {
            "name": name,
            "description": None,
            "rule_type": "guideline",
            "value": text,
            "severity": severity,
            "channel": None,
            "field_name": None,
            "priority": 50,
            "is_active": True,
        }
        for name, text, severity in _SEEDED_GUIDELINES
    ]
    op.bulk_insert(rules, rows)


def downgrade() -> None:
    with op.batch_alter_table('rules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rules_audience_segment_id'))
        batch_op.drop_index(batch_op.f('ix_rules_brand_id'))
        batch_op.drop_index(batch_op.f('ix_rules_channel'))
        batch_op.drop_index(batch_op.f('ix_rules_rule_type'))
        batch_op.drop_index(batch_op.f('ix_rules_name'))
    op.drop_table('rules')
