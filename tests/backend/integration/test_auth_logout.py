from urllib.parse import parse_qs, urlsplit

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from cs_avatar.api.auth import SESSION_COOKIE
from cs_avatar.api.dependencies import get_openid_service, get_steam_profile_client
from cs_avatar.auth.steam_openid import VerifiedSteamIdentity
from cs_avatar.auth.steam_profile import ProfileStatus, SteamProfileResult
from cs_avatar.persistence.models import AuthSession

FIRST_STEAM_ID = "76561198000000000"
SECOND_STEAM_ID = "76561198000000001"


class SwitchingOpenIDService:
    def __init__(self) -> None:
        self.identities = [FIRST_STEAM_ID, SECOND_STEAM_ID]

    def begin(self, state: str) -> str:
        return (
            "https://steamcommunity.com/openid/login"
            f"?openid.mode=checkid_setup&state={state}"
        )

    def verify(self, query: dict[str, str]) -> VerifiedSteamIdentity:
        steam_id = self.identities.pop(0)
        return VerifiedSteamIdentity(
            steam_id,
            f"2026-11-26T00:00:00Z-{steam_id}",
        )


class SwitchingProfileClient:
    async def get_profile(self, steam_id: str) -> SteamProfileResult:
        return SteamProfileResult(
            steam_id=steam_id,
            persona_name=f"Player {steam_id[-1]}",
            avatar_url="https://steamcdn-a.akamaihd.net/example.jpg",
            profile_status=ProfileStatus.AVAILABLE,
        )


async def _complete_login(client) -> None:
    login = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    callback = await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "id_res"},
    )
    assert callback.status_code == 302


@pytest.mark.asyncio
async def test_sign_out_then_sign_in_with_different_steam_identity(app_client):
    app, client = app_client
    openid = SwitchingOpenIDService()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: SwitchingProfileClient()

    await _complete_login(client)
    first_session = await client.get("/api/v1/auth/session")
    assert first_session.status_code == 200
    assert first_session.json()["steamId"] == FIRST_STEAM_ID
    first_token = client.cookies.get(SESSION_COOKIE)

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert (await client.get("/api/v1/auth/session")).status_code == 401

    await _complete_login(client)
    second_session = await client.get("/api/v1/auth/session")

    assert second_session.status_code == 200
    assert second_session.json()["steamId"] == SECOND_STEAM_ID
    assert second_session.json()["personaName"] == "Player 1"
    assert second_session.json()["steamId"] != first_session.json()["steamId"]

    assert first_token is not None
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies={SESSION_COOKIE: first_token},
    ) as replay_client:
        assert (await replay_client.get("/api/v1/auth/session")).status_code == 401

    async with app.state.session_factory() as session:
        first_record = await session.scalar(
            select(AuthSession).where(AuthSession.steam_id == FIRST_STEAM_ID)
        )
        assert first_record is not None
        assert first_record.revoked_at is not None
