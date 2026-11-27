from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from cs_avatar.api.auth import SESSION_COOKIE
from cs_avatar.api.dependencies import get_openid_service, get_steam_profile_client
from cs_avatar.auth.steam_openid import (
    SteamOpenIDCancelled,
    SteamOpenIDError,
    VerifiedSteamIdentity,
)
from cs_avatar.auth.steam_profile import ProfileStatus, SteamProfileResult
from cs_avatar.persistence.models import AuthSession

STEAM_ID = "76561198000000000"


class StubOpenIDService:
    def __init__(self, outcome: str = "success") -> None:
        self.outcome = outcome
        self.verify_calls = 0

    def begin(self, state: str) -> str:
        return (
            "https://steamcommunity.com/openid/login"
            f"?openid.mode=checkid_setup&state={state}"
        )

    def verify(self, query: dict[str, str]) -> VerifiedSteamIdentity:
        self.verify_calls += 1
        if self.outcome == "cancel":
            raise SteamOpenIDCancelled
        if self.outcome == "invalid":
            raise SteamOpenIDError
        return VerifiedSteamIdentity(STEAM_ID, "2026-11-25T00:00:00Z-integration-nonce")


class StubProfileClient:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.calls = 0

    async def get_profile(self, steam_id: str) -> SteamProfileResult:
        self.calls += 1
        assert steam_id == STEAM_ID
        if not self.available:
            return SteamProfileResult.unavailable(steam_id)
        return SteamProfileResult(
            steam_id=steam_id,
            persona_name="Example Player",
            avatar_url="https://steamcdn-a.akamaihd.net/example.jpg",
            profile_status=ProfileStatus.AVAILABLE,
        )


@pytest.mark.asyncio
async def test_login_redirects_to_steam_and_sets_browser_binding(app_client):
    app, client = app_client
    response = await client.get("/api/v1/auth/steam/login")

    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert location.scheme == "https"
    assert location.netloc == "steamcommunity.com"
    assert parse_qs(location.query)["openid.mode"] == ["checkid_setup"]
    cookies = response.headers.get_list("set-cookie")
    assert any("steam_login_binding=" in value for value in cookies)
    assert any(
        "HttpOnly" in value and "Secure" in value and "SameSite=lax" in value
        for value in cookies
    )
    assert (await client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.asyncio
async def test_verified_callback_sets_secure_session_and_returns_profile(app_client):
    app, client = app_client
    openid = StubOpenIDService()
    profile = StubProfileClient()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: profile

    login = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    callback = await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "id_res"},
    )

    assert callback.status_code == 302
    assert urlsplit(callback.headers["location"]).path == "/"
    cookies = callback.headers.get_list("set-cookie")
    session_cookie = next(value for value in cookies if value.startswith("cs_avatar_session="))
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=43200" in session_cookie
    session = await client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json() == {
        "steamId": STEAM_ID,
        "personaName": "Example Player",
        "avatarUrl": "https://steamcdn-a.akamaihd.net/example.jpg",
        "profileStatus": "AVAILABLE",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["cancel", "invalid"])
async def test_failed_or_cancelled_callback_never_creates_a_session(app_client, outcome):
    app, client = app_client
    openid = StubOpenIDService(outcome)
    profile = StubProfileClient()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: profile

    login = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    callback = await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "cancel" if outcome == "cancel" else "id_res"},
    )

    assert callback.status_code == 302
    assert "steam_login=failed" in callback.headers["location"]
    assert not any(
        value.startswith("cs_avatar_session=")
        for value in callback.headers.get_list("set-cookie")
    )
    assert profile.calls == 0
    assert (await client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.asyncio
async def test_profile_unavailable_keeps_verified_identity_authenticated(app_client):
    app, client = app_client
    app.dependency_overrides[get_openid_service] = lambda: StubOpenIDService()
    app.dependency_overrides[get_steam_profile_client] = lambda: StubProfileClient(False)

    login = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "id_res"},
    )

    session = await client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["steamId"] == STEAM_ID
    assert session.json()["personaName"] is None
    assert session.json()["avatarUrl"] is None
    assert session.json()["profileStatus"] == "UNAVAILABLE"


async def _sign_in_test_player(app, client) -> str:
    app.dependency_overrides[get_openid_service] = lambda: StubOpenIDService()
    app.dependency_overrides[get_steam_profile_client] = lambda: StubProfileClient()

    login = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    callback = await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "id_res"},
    )
    assert callback.status_code == 302
    token = client.cookies.get(SESSION_COOKIE)
    assert token is not None
    return token


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(app_client):
    app, client = app_client
    old_token = await _sign_in_test_player(app, client)

    logout = await client.post("/api/v1/auth/logout")

    assert logout.status_code == 204
    cookie_headers = logout.headers.get_list("set-cookie")
    cleared_cookie = next(
        value for value in cookie_headers if value.startswith(f"{SESSION_COOKIE}=")
    )
    assert "Max-Age=0" in cleared_cookie
    assert "Path=/api/v1/auth" in cleared_cookie
    assert "HttpOnly" in cleared_cookie
    assert "Secure" in cleared_cookie
    assert "SameSite=lax" in cleared_cookie
    assert (await client.get("/api/v1/auth/session")).status_code == 401

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies={SESSION_COOKIE: old_token},
    ) as replay_client:
        assert (await replay_client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.asyncio
async def test_logout_is_idempotent_without_cookie_or_after_expiration(app_client):
    app, client = app_client

    absent_logout = await client.post("/api/v1/auth/logout")
    assert absent_logout.status_code == 204
    assert any(
        value.startswith(f"{SESSION_COOKIE}=")
        for value in absent_logout.headers.get_list("set-cookie")
    )

    old_token = await _sign_in_test_player(app, client)
    async with app.state.session_factory() as session:
        record = await session.scalar(select(AuthSession))
        assert record is not None
        record.created_at = datetime.now(UTC) - timedelta(hours=2)
        record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await session.commit()

    expired_logout = await client.post("/api/v1/auth/logout")
    assert expired_logout.status_code == 204
    assert (await client.get("/api/v1/auth/session")).status_code == 401

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies={SESSION_COOKIE: old_token},
    ) as replay_client:
        assert (await replay_client.post("/api/v1/auth/logout")).status_code == 204
