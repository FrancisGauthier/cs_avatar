import logging

import httpx
import pytest

from cs_avatar.auth.steam_profile import (
    MAX_PROFILE_RESPONSE_BYTES,
    ProfileStatus,
    SteamProfileClient,
)

STEAM_ID = "76561198000000000"
API_KEY = "server-only-test-key"


def response_for(player: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"response": {"players": [player]}})


@pytest.mark.asyncio
async def test_matching_profile_is_returned_and_key_stays_server_side() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response_for(
            {
                "steamid": STEAM_ID,
                "personaname": "Example Player",
                "avatarfull": "https://steamcdn-a.akamaihd.net/example.jpg",
            }
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.AVAILABLE
    assert result.persona_name == "Example Player"
    assert result.avatar_url == "https://steamcdn-a.akamaihd.net/example.jpg"
    assert requests[0].url.params["key"] == API_KEY
    assert requests[0].url.params["steamids"] == STEAM_ID


@pytest.mark.asyncio
async def test_mismatched_steam_id_is_unavailable() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return response_for(
            {
                "steamid": "76561198000000001",
                "personaname": "Other Player",
                "avatarfull": "https://steamcdn-a.akamaihd.net/example.jpg",
            }
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.UNAVAILABLE
    assert result.persona_name is None
    assert result.avatar_url is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "player",
    [
        {},
        {"steamid": STEAM_ID, "personaname": 123},
        {"steamid": STEAM_ID, "personaname": " "},
    ],
)
async def test_malformed_or_missing_nickname_is_unavailable(
    player: dict[str, object],
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return response_for(player)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.UNAVAILABLE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "avatar_url",
    [
        "http://steamcdn-a.akamaihd.net/example.jpg",
        "https://evil.example/example.jpg",
        "https://steamcdn-a.akamaihd.net.evil.example/example.jpg",
        "https://steamcdn-a.akamaihd.net:invalid/example.jpg",
        "https://[invalid]/example.jpg",
    ],
)
async def test_invalid_avatar_url_is_rejected_without_losing_valid_nickname(
    avatar_url: str,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return response_for(
            {"steamid": STEAM_ID, "personaname": "Example Player", "avatarfull": avatar_url}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.AVAILABLE
    assert result.persona_name == "Example Player"
    assert result.avatar_url is None


@pytest.mark.asyncio
async def test_oversized_profile_response_is_rejected() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b" " * (MAX_PROFILE_RESPONSE_BYTES + 1))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_timeout_marks_profile_unavailable_without_logging_api_key(caplog) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        caplog.set_level(logging.WARNING)
        result = await SteamProfileClient(API_KEY, client).get_profile(STEAM_ID)

    assert result.profile_status is ProfileStatus.UNAVAILABLE
    assert API_KEY not in caplog.text
