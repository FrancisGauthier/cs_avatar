from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ProfileStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class Base(DeclarativeBase):
    pass


class SteamIdentity(Base):
    __tablename__ = "steam_identity"

    steam_id: Mapped[str] = mapped_column(String(17), primary_key=True)
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="identity")


class OpenIDAttempt(Base):
    __tablename__ = "steam_openid_attempt"
    __table_args__ = (
        CheckConstraint(
            "expires_at > created_at",
            name="ck_steam_openid_attempt_expiry",
        ),
        UniqueConstraint(
            "provider_nonce_digest",
            name="uq_steam_openid_attempt_provider_nonce_digest",
        ),
    )

    state_digest: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    browser_binding_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    return_to: Mapped[str] = mapped_column(String(2048), nullable=False)
    provider_nonce_digest: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_session"
    __table_args__ = (
        CheckConstraint(
            "profile_status IN ('AVAILABLE', 'UNAVAILABLE')",
            name="ck_auth_session_profile_status",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_session_expiry",
        ),
    )

    id_digest: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    steam_id: Mapped[str] = mapped_column(
        String(17),
        ForeignKey("steam_identity.steam_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    persona_name: Mapped[str | None] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    profile_status: Mapped[ProfileStatus] = mapped_column(
        SqlEnum(
            ProfileStatus,
            name="auth_session_profile_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identity: Mapped[SteamIdentity] = relationship(back_populates="sessions")
