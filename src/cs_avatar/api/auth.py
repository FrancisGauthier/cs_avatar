import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cs_avatar.api.dependencies import (
    get_openid_service,
    get_settings,
    get_steam_profile_client,
)
from cs_avatar.auth.security import digest_secret
from cs_avatar.auth.steam_openid import (
    SteamOpenIDCancelled,
    SteamOpenIDError,
    SteamOpenIDService,
)
from cs_avatar.auth.steam_profile import SteamProfileClient, SteamProfileResult
from cs_avatar.config import CALLBACK_PATH, Settings
from cs_avatar.persistence.database import get_db_session
from cs_avatar.persistence.models import (
    AuthSession,
    OpenIDAttempt,
    ProfileStatus,
    SteamIdentity,
)

logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_COOKIE = "cs_avatar_session"
BINDING_COOKIE = "steam_login_binding"
ATTEMPT_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(hours=12)
NONCE_RETENTION = timedelta(hours=5)
MAX_CALLBACK_QUERY_ITEMS = 64
MAX_CALLBACK_QUERY_LENGTH = 16_384
SESSION_PATH = "/api/v1/auth"


class SteamSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    steam_id: str = Field(alias="steamId", pattern=r"^[0-9]{17}$")
    persona_name: str | None = Field(alias="personaName", max_length=128)
    avatar_url: str | None = Field(alias="avatarUrl", max_length=2048)
    profile_status: ProfileStatus = Field(alias="profileStatus")


def _frontend_url(settings: Settings, status: str | None = None) -> str:
    base = settings.public_app_origin.rstrip("/") + "/"
    if status is None:
        return base
    return f"{base}?steam_login={quote(status)}"


def _cookie_secure(settings: Settings) -> bool:
    return settings.public_app_origin.lower().startswith("https://")


def _clear_binding_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        BINDING_COOKIE,
        path=CALLBACK_PATH,
        secure=_cookie_secure(settings),
        httponly=True,
        samesite="lax",
    )


def _failed_callback(settings: Settings) -> Response:
    response = Response(
        status_code=302,
        headers={"Location": _frontend_url(settings, "failed")},
    )
    _clear_binding_cookie(response, settings)
    return response


def _callback_query(request: Request) -> dict[str, str] | None:
    pairs = list(request.query_params.multi_items())
    if len(pairs) > MAX_CALLBACK_QUERY_ITEMS:
        return None
    if sum(len(key) + len(value) for key, value in pairs) > MAX_CALLBACK_QUERY_LENGTH:
        return None
    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            return None
        query[key] = value
    return query


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _finish_attempt(
    session: AsyncSession,
    state_digest: bytes,
    binding_digest: bytes,
    return_to: str,
    now: datetime,
    nonce_digest: bytes | None = None,
) -> bool:
    statement = (
        update(OpenIDAttempt)
        .where(
            OpenIDAttempt.state_digest == state_digest,
            OpenIDAttempt.browser_binding_digest == binding_digest,
            OpenIDAttempt.return_to == return_to,
            OpenIDAttempt.expires_at > now,
            OpenIDAttempt.consumed_at.is_(None),
            OpenIDAttempt.provider_nonce_digest.is_(None),
        )
        .values(consumed_at=now, provider_nonce_digest=nonce_digest)
    )
    result = await session.execute(statement)
    return result.rowcount == 1


def _invalid_profile(profile: SteamProfileResult, steam_id: str) -> SteamProfileResult:
    if (
        profile.steam_id != steam_id
        or profile.profile_status is ProfileStatus.UNAVAILABLE
        or not profile.persona_name
        or len(profile.persona_name) > 128
    ):
        return SteamProfileResult.unavailable(steam_id)
    return profile


@router.get("/steam/login", include_in_schema=True)
async def steam_login(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    openid: Annotated[SteamOpenIDService, Depends(get_openid_service)],
) -> Response:
    now = datetime.now(UTC)
    state = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(32)
    try:
        authorization_url = openid.begin(state)
    except (SteamOpenIDError, ValueError):
        logger.warning("Steam sign-in could not be started")
        raise HTTPException(status_code=503, detail="Steam sign-in is unavailable") from None

    await session.execute(
        delete(OpenIDAttempt).where(
            OpenIDAttempt.expires_at < now - NONCE_RETENTION
        )
    )
    session.add(
        OpenIDAttempt(
            state_digest=digest_secret(settings.session_secret, state),
            browser_binding_digest=digest_secret(settings.session_secret, binding),
            return_to=settings.steam_openid_return_to,
            created_at=now,
            expires_at=now + ATTEMPT_TTL,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning("Steam sign-in attempt could not be persisted")
        raise HTTPException(status_code=503, detail="Steam sign-in is unavailable") from None

    response = Response(status_code=302, headers={"Location": authorization_url})
    response.set_cookie(
        BINDING_COOKIE,
        binding,
        max_age=int(ATTEMPT_TTL.total_seconds()),
        path=CALLBACK_PATH,
        secure=_cookie_secure(settings),
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/steam/callback", include_in_schema=True)
async def steam_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    openid: Annotated[SteamOpenIDService, Depends(get_openid_service)],
    profile_client: Annotated[SteamProfileClient, Depends(get_steam_profile_client)],
) -> Response:
    query = _callback_query(request)
    state = query.get("state") if query is not None else None
    binding = request.cookies.get(BINDING_COOKIE)
    if not state or not binding or query is None:
        return _failed_callback(settings)

    state_digest = digest_secret(settings.session_secret, state)
    binding_digest = digest_secret(settings.session_secret, binding)
    now = datetime.now(UTC)
    attempt = await session.execute(
        select(
            OpenIDAttempt.browser_binding_digest,
            OpenIDAttempt.return_to,
            OpenIDAttempt.expires_at,
            OpenIDAttempt.consumed_at,
        ).where(OpenIDAttempt.state_digest == state_digest)
    )
    attempt_values = attempt.one_or_none()
    await session.rollback()
    if (
        attempt_values is None
        or not hmac.compare_digest(attempt_values.browser_binding_digest, binding_digest)
        or attempt_values.return_to != settings.steam_openid_return_to
        or _aware(attempt_values.expires_at) <= now
        or attempt_values.consumed_at is not None
    ):
        return _failed_callback(settings)

    try:
        identity = openid.verify(query)
    except (SteamOpenIDCancelled, SteamOpenIDError) as error:
        await _finish_attempt(
            session,
            state_digest,
            binding_digest,
            settings.steam_openid_return_to,
            now,
        )
        await session.commit()
        if isinstance(error, SteamOpenIDCancelled):
            logger.info("Steam sign-in was cancelled by the player")
        else:
            logger.warning(
                "Steam OpenID assertion was rejected (reason=%s)",
                error.reason,
            )
        return _failed_callback(settings)

    profile = _invalid_profile(
        await profile_client.get_profile(identity.steam_id),
        identity.steam_id,
    )
    nonce_digest = digest_secret(settings.session_secret, identity.response_nonce)
    raw_session_token = secrets.token_urlsafe(32)
    session_digest = digest_secret(settings.session_secret, raw_session_token)
    expires_at = now + SESSION_TTL

    try:
        if not await _finish_attempt(
            session,
            state_digest,
            binding_digest,
            settings.steam_openid_return_to,
            now,
            nonce_digest,
        ):
            await session.rollback()
            return _failed_callback(settings)
        if await session.get(SteamIdentity, identity.steam_id) is None:
            session.add(SteamIdentity(steam_id=identity.steam_id))
        session.add(
            AuthSession(
                id_digest=session_digest,
                steam_id=identity.steam_id,
                persona_name=profile.persona_name,
                avatar_url=profile.avatar_url,
                profile_status=profile.profile_status,
                created_at=now,
                expires_at=expires_at,
            )
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info("Steam sign-in attempt was already consumed")
        return _failed_callback(settings)

    response = Response(
        status_code=302,
        headers={"Location": _frontend_url(settings)},
    )
    response.set_cookie(
        SESSION_COOKIE,
        raw_session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        path=SESSION_PATH,
        secure=_cookie_secure(settings),
        httponly=True,
        samesite="lax",
    )
    _clear_binding_cookie(response, settings)
    return response


@router.get("/session", response_model=SteamSessionResponse)
async def current_session(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SteamSessionResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or len(token) > 128:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_digest = digest_secret(settings.session_secret, token)
    now = datetime.now(UTC)
    record = await session.scalar(
        select(AuthSession).where(
            AuthSession.id_digest == session_digest,
            AuthSession.expires_at > now,
            AuthSession.revoked_at.is_(None),
        )
    )
    if record is None:
        response.delete_cookie(
            SESSION_COOKIE,
            path=SESSION_PATH,
            secure=_cookie_secure(settings),
            httponly=True,
            samesite="lax",
        )
        raise HTTPException(status_code=401, detail="Not authenticated")

    return SteamSessionResponse(
        steam_id=record.steam_id,
        persona_name=record.persona_name,
        avatar_url=record.avatar_url,
        profile_status=record.profile_status,
    )
