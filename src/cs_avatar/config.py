from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CALLBACK_PATH = "/api/v1/auth/steam/callback"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://cs_avatar:local-dev-only@127.0.0.1:5432/cs_avatar"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://cs_avatar:local-dev-only@127.0.0.1:5432/cs_avatar"
    )
    public_app_origin: str = "http://127.0.0.1:5173"
    steam_openid_realm: str = "http://127.0.0.1:5173/"
    steam_openid_return_to: str = (
        "http://127.0.0.1:5173/api/v1/auth/steam/callback"
    )
    session_secret: SecretStr
    steam_web_api_key: SecretStr

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret.encode("utf-8")) < 32 or secret.startswith("replace-with-"):
            raise ValueError("SESSION_SECRET must contain at least 32 bytes")
        return value

    @field_validator("steam_web_api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value().strip()
        if not secret or secret.startswith("replace-with-"):
            raise ValueError("STEAM_WEB_API_KEY must not be empty")
        return value

    @field_validator("public_app_origin", "steam_openid_realm")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Expected an HTTP(S) origin without credentials or a path")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("Non-local origins must use HTTPS")
        return value

    @field_validator("steam_openid_return_to")
    @classmethod
    def validate_return_to(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path != CALLBACK_PATH
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("STEAM_OPENID_RETURN_TO must be the fixed callback URL")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("Non-local callback URLs must use HTTPS")
        return value

    @model_validator(mode="after")
    def validate_same_origin_callback(self) -> "Settings":
        realm = urlsplit(self.steam_openid_realm)
        callback = urlsplit(self.steam_openid_return_to)
        app_origin = urlsplit(self.public_app_origin)
        if (realm.scheme, realm.netloc) != (callback.scheme, callback.netloc):
            raise ValueError("Steam OpenID realm and callback must share an origin")
        if (app_origin.scheme, app_origin.netloc) != (callback.scheme, callback.netloc):
            raise ValueError("The SPA and Steam callback must share an origin")
        return self
