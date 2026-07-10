from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TelegramAuthRequest(BaseModel):
    init_data: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str | None
    first_name: str | None
    last_name: str | None
    phone: str | None = None
    role: str
    status: str
    trust_level: str | None = None
    last_seen_at: str | None = None
    terms_accepted_at: str | None = None
    terms_version: str | None = None


class TermsAcceptanceRequest(BaseModel):
    terms_version: str = "2026-07-06"


class UserProfileUpdateRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=24, pattern=r"^\+?[0-9][0-9 ()-]{5,22}[0-9]$")


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: PublicUser | None = None


class LogoutResponse(BaseModel):
    logged_out: bool
