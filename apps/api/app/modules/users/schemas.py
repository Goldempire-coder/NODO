from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.shared.validation import StrictRequestModel
from app.modules.users.terms import CURRENT_TERMS_VERSION


class TelegramAuthRequest(StrictRequestModel):
    init_data: str = Field(min_length=1, max_length=8192)


class RefreshRequest(StrictRequestModel):
    refresh_token: str = Field(min_length=16, max_length=512)


class LogoutRequest(StrictRequestModel):
    refresh_token: str = Field(min_length=16, max_length=512)

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


class TermsAcceptanceRequest(StrictRequestModel):
    terms_version: str = Field(default=CURRENT_TERMS_VERSION, min_length=1, max_length=32)


class UserProfileUpdateRequest(StrictRequestModel):
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
