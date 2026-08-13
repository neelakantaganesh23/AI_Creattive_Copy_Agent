from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import AuthProvider, Role

if TYPE_CHECKING:
    from app.models.generation import Generation
    from app.models.password_reset import PasswordResetToken
    from app.models.refresh_token import RefreshToken


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    # Null for accounts that only ever sign in through an identity provider.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[Role] = mapped_column(String(20), nullable=False, default=Role.MARKETER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auth_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AuthProvider.LOCAL
    )
    # Google's stable subject id; never the email, which users can change.
    google_sub: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    generations: Mapped[list[Generation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
