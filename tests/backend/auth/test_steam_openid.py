from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from httpx import ASGITransport, AsyncClient
from openid.message import OPENID2_NS
from openid.store.nonce import mkNonce
from sqlalchemy import select

from cs_avatar.api.dependencies import get_openid_service, get_steam_profile_client
from cs_avatar.auth import steam_openid
from cs_avatar.auth.steam_openid import (
    SteamOpenIDCancelled,
    SteamOpenIDError,
    SteamOpenIDService,
    VerifiedSteamIdentity,
)
from cs_avatar.auth.steam_profile import ProfileStatus, SteamProfileResult
from cs_avatar.persistence.models import AuthSession, OpenIDAttempt

CALLBACK = "https://testserver/api/v1/auth/steam/callback"
STEAM_ID = "76561198000000000"
IDENTITY_URL = f"https://steamcommunity.com/openid/id/{STEAM_ID}"
RESPONSE_NONCE = mkNonce()


def valid_assertion() -> dict[str, str]:
    return {
        "openid.mode": "id_res",
        "openid.ns": OPENID2_NS,
        "openid.claimed_id": IDENTITY_URL,
        "openid.identity": IDENTITY_URL,
        "openid.op_endpoint": steam_openid.STEAM_OPENID_ENDPOINT,
        "openid.response_nonce": RESPONSE_NONCE,
        "openid.return_to": f"{CALLBACK}?state=test-state",
        "state": "test-state",
    }


class FakeMessage:
    def getArg(self, namespace: str, name: str) -> str | None:
        if namespace.endswith("auth/2.0") and name == "response_nonce":
            return RESPONSE_NONCE
        return None


class FakeConsumer:
    response: object
    expected_return_to: str

    def __init__(self, store: object) -> None:
        self.store = store

    def complete(self, message: object, endpoint: object, current_url: str) -> object:
        assert current_url == self.expected_return_to
        if message.getArg(OPENID2_NS, "return_to") != current_url:
            return response(
                "failure",
                failure_reason="return_to does not match return URL",
            )
        return self.response


def response(
    status: str,
    identity_url: str | None = None,
    failure_reason: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        status=status,
        identity_url=identity_url,
        message=failure_reason or FakeMessage(),
    )


def test_login_redirect_uses_fixed_steam_openid_endpoint(app_client_settings) -> None:
    service = SteamOpenIDService(app_client_settings)
    state = "test-state"

    url = service.begin(state)
    params = parse_qs(urlsplit(url).query)
    return_to = params["openid.return_to"][0]

    assert url.startswith("https://steamcommunity.com/openid/login?")
    assert params["openid.mode"] == ["checkid_setup"]
    assert params["openid.identity"] == [
        "http://specs.openid.net/auth/2.0/identifier_select"
    ]
    assert params["openid.claimed_id"] == [
        "http://specs.openid.net/auth/2.0/identifier_select"
    ]
    assert parse_qs(urlsplit(return_to).query)["state"] == [state]


def test_direct_verification_posts_form_encoded_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        headers: dict[str, str] = {}
        encoding = "utf-8"

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def iter_bytes(self, chunk_size: int):
            yield b"is_valid:true\n"

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str, **kwargs: object) -> FakeResponse:
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(steam_openid.httpx, "Client", FakeClient)
    steam_openid._SteamOpenIDFetcher().fetch(
        steam_openid.STEAM_OPENID_ENDPOINT,
        body="openid.mode=check_authentication",
    )

    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"


def test_verified_assertion_extracts_only_a_steam_identity(
    app_client_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = response("success", IDENTITY_URL)
    FakeConsumer.response = expected
    FakeConsumer.expected_return_to = (
        f"{app_client_settings.steam_openid_return_to}?state=test-state"
    )
    monkeypatch.setattr(steam_openid, "GenericConsumer", FakeConsumer)
    service = SteamOpenIDService(app_client_settings)

    identity = service.verify(valid_assertion())

    assert identity == VerifiedSteamIdentity(
        steam_id=STEAM_ID,
        response_nonce=RESPONSE_NONCE,
    )


def test_cancelled_assertion_does_not_produce_an_identity(
    app_client_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeConsumer.response = response("cancel")
    FakeConsumer.expected_return_to = (
        f"{app_client_settings.steam_openid_return_to}?state=test-state"
    )
    monkeypatch.setattr(steam_openid, "GenericConsumer", FakeConsumer)

    with pytest.raises(SteamOpenIDCancelled) as error:
        SteamOpenIDService(app_client_settings).verify(
            {"openid.mode": "cancel", "state": "test-state"}
        )
    assert error.value.reason == "cancelled"


def test_invalid_mode_has_a_safe_diagnostic_reason(app_client_settings) -> None:
    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(
            {"openid.mode": "unexpected", "state": "test-state"}
        )
    assert error.value.reason == "invalid_mode"


def test_invalid_signature_or_mismatched_return_url_fails_closed(
    app_client_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeConsumer.response = response(
        "failure",
        failure_reason="Server denied check_authentication",
    )
    FakeConsumer.expected_return_to = (
        f"{app_client_settings.steam_openid_return_to}?state=test-state"
    )
    monkeypatch.setattr(steam_openid, "GenericConsumer", FakeConsumer)

    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(valid_assertion())
    assert error.value.reason == "signature_rejected"

    FakeConsumer.response = response("success", IDENTITY_URL)
    assertion = valid_assertion()
    assertion["openid.return_to"] = "https://attacker.example/callback?state=test-state"
    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(assertion)
    assert error.value.reason == "return_to_authority_mismatch"

    assertion["openid.return_to"] = f"{CALLBACK}?state=unexpected"
    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(assertion)
    assert error.value.reason == "return_to_state_mismatch"

    assertion["openid.return_to"] = CALLBACK
    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(assertion)
    assert error.value.reason == "return_to_state_missing"


def test_non_steam_claimed_identity_is_rejected_before_provider_network_call(
    app_client_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_consumer(_: object) -> object:
        raise AssertionError("untrusted claimed identity must not reach provider verification")

    monkeypatch.setattr(steam_openid, "GenericConsumer", unexpected_consumer)
    assertion = valid_assertion()
    assertion["openid.claimed_id"] = "https://attacker.example/openid/id/76561198000000000"
    assertion["openid.identity"] = assertion["openid.claimed_id"]

    with pytest.raises(SteamOpenIDError) as error:
        SteamOpenIDService(app_client_settings).verify(assertion)
    assert error.value.reason == "identity_mismatch"


@pytest.mark.asyncio
async def test_expired_attempt_is_rejected_without_verifying_or_signing_in(app_client):
    app, client = app_client
    openid = FakeRouteOpenID()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: FakeProfileClient()

    login_response = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login_response.headers["location"]).query)["state"][0]
    async with app.state.session_factory() as session:
        attempt = await session.scalar(select(OpenIDAttempt))
        assert attempt is not None
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=11)
        attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    callback = await client.get(
        "/api/v1/auth/steam/callback",
        params={"state": state, "openid.mode": "id_res"},
    )

    assert callback.status_code == 302
    assert "steam_login=failed" in callback.headers["location"]
    assert openid.verify_calls == 0
    assert (await client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.asyncio
async def test_replayed_callback_cannot_create_a_second_session(app_client):
    app, client = app_client
    openid = FakeRouteOpenID()
    profile = FakeProfileClient()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: profile

    login_response = await client.get("/api/v1/auth/steam/login")
    state = parse_qs(urlsplit(login_response.headers["location"]).query)["state"][0]
    params = {"state": state, "openid.mode": "id_res"}

    first = await client.get("/api/v1/auth/steam/callback", params=params)
    second = await client.get("/api/v1/auth/steam/callback", params=params)

    assert first.status_code == 302
    assert second.status_code == 302
    assert openid.verify_calls == 1
    assert profile.calls == 1
    async with app.state.session_factory() as session:
        assert len((await session.scalars(select(OpenIDAttempt))).all()) == 1
        assert len((await session.scalars(select(AuthSession))).all()) == 1


@pytest.mark.asyncio
async def test_provider_nonce_cannot_be_reused_across_login_attempts(app_client):
    app, first_client = app_client
    openid = FakeRouteOpenID()
    profile = FakeProfileClient()
    app.dependency_overrides[get_openid_service] = lambda: openid
    app.dependency_overrides[get_steam_profile_client] = lambda: profile

    first_login = await first_client.get("/api/v1/auth/steam/login")
    first_state = parse_qs(urlsplit(first_login.headers["location"]).query)["state"][0]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
    ) as second_client:
        second_login = await second_client.get("/api/v1/auth/steam/login")
        second_state = parse_qs(urlsplit(second_login.headers["location"]).query)[
            "state"
        ][0]
        first_callback = await first_client.get(
            "/api/v1/auth/steam/callback",
            params={"state": first_state, "openid.mode": "id_res"},
        )
        second_callback = await second_client.get(
            "/api/v1/auth/steam/callback",
            params={"state": second_state, "openid.mode": "id_res"},
        )

    assert first_callback.headers["location"] == "https://testserver/"
    assert "steam_login=failed" in second_callback.headers["location"]
    assert openid.verify_calls == 2
    async with app.state.session_factory() as session:
        assert len((await session.scalars(select(AuthSession))).all()) == 1


class FakeRouteOpenID:
    verify_calls = 0

    def begin(self, state: str) -> str:
        return (
            "https://steamcommunity.com/openid/login"
            f"?openid.mode=checkid_setup&state={state}"
        )

    def verify(self, query: dict[str, str]) -> VerifiedSteamIdentity:
        self.verify_calls += 1
        assert query.get("state")
        return VerifiedSteamIdentity(STEAM_ID, "2026-11-25T00:00:00Z-route-nonce")


class FakeProfileClient:
    calls = 0

    async def get_profile(self, steam_id: str) -> SteamProfileResult:
        self.calls += 1
        assert steam_id == STEAM_ID
        return SteamProfileResult(
            steam_id=steam_id,
            persona_name="Example Player",
            avatar_url="https://steamcdn-a.akamaihd.net/example.jpg",
            profile_status=ProfileStatus.AVAILABLE,
        )
