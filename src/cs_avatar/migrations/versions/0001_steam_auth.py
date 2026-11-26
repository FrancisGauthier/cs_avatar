"""Create Steam login persistence tables.

Revision ID: 0001_steam_auth
Revises:
Create Date: 2026-11-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_steam_auth"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "steam_identity",
        sa.Column("steam_id", sa.String(length=17), nullable=False),
        sa.PrimaryKeyConstraint("steam_id"),
    )
    op.create_table(
        "steam_openid_attempt",
        sa.Column("state_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("browser_binding_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("return_to", sa.String(length=2048), nullable=False),
        sa.Column("provider_nonce_digest", sa.LargeBinary(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_steam_openid_attempt_expiry",
        ),
        sa.PrimaryKeyConstraint("state_digest"),
        sa.UniqueConstraint(
            "provider_nonce_digest",
            name="uq_steam_openid_attempt_provider_nonce_digest",
        ),
    )
    op.create_table(
        "auth_session",
        sa.Column("id_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("steam_id", sa.String(length=17), nullable=False),
        sa.Column("persona_name", sa.String(length=128), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("profile_status", sa.String(length=11), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_session_expiry",
        ),
        sa.CheckConstraint(
            "profile_status IN ('AVAILABLE', 'UNAVAILABLE')",
            name="ck_auth_session_profile_status",
        ),
        sa.ForeignKeyConstraint(
            ["steam_id"],
            ["steam_identity.steam_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id_digest"),
    )
    op.create_index("ix_auth_session_steam_id", "auth_session", ["steam_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_session_steam_id", table_name="auth_session")
    op.drop_table("auth_session")
    op.drop_table("steam_openid_attempt")
    op.drop_table("steam_identity")
