import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from cs_avatar.persistence.models import ProfileStatus

logger = logging.getLogger(__name__)

STEAM_PROFILE_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_ID_PATTERN = re.compile(r"^[0-9]{17}$")
STEAM_AVATAR_HOSTS = frozenset(
    {
        "avatars.akamai.steamstatic.com",
        "avatars.steamstatic.com",
        "cdn.akamai.steamstatic.com",
        "steamcdn-a.akamaihd.net",
    }
)
PROFILE_TIMEOUT_SECONDS = 5.0
MAX_PROFILE_RESPONSE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class SteamProfileResult:
    steam_id: str
    persona_name: str | None
    avatar_url: str | None
    profile_status: ProfileStatus

    @classmethod
    def unavailable(cls, steam_id: str) -> "SteamProfileResult":
        return cls(
            steam_id=steam_id,
            persona_name=None,
            avatar_url=None,
            profile_status=ProfileStatus.UNAVAILABLE,
        )


def _validated_avatar_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.lower() not in STEAM_AVATAR_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or not parsed.path.startswith("/")
        or parsed.fragment
    ):
        return None
    return value


class SteamProfileClient:
    def __init__(
        self,
        api_key: SecretStr | str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (
            api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        )
        self._client = client

    async def get_profile(self, steam_id: str) -> SteamProfileResult:
        if not STEAM_ID_PATTERN.fullmatch(steam_id):
            raise ValueError("Expected a verified decimal Steam identifier")

        try:
            if self._client is not None:
                content = await self._read_response(self._client, steam_id)
            else:
                async with httpx.AsyncClient(
                    timeout=PROFILE_TIMEOUT_SECONDS,
                    follow_redirects=False,
                ) as client:
                    content = await self._read_response(client, steam_id)
        except httpx.HTTPError as error:
            logger.warning(
                "Steam profile lookup failed for a verified identity (%s)",
                type(error).__name__,
            )
            return SteamProfileResult.unavailable(steam_id)

        if content is None:
            return SteamProfileResult.unavailable(steam_id)

        try:
            payload = json.loads(content)
        except ValueError:
            logger.warning("Steam profile lookup returned malformed JSON")
            return SteamProfileResult.unavailable(steam_id)

        summary = self._matching_summary(payload, steam_id)
        if summary is None:
            logger.warning("Steam profile lookup did not match the verified identity")
            return SteamProfileResult.unavailable(steam_id)

        persona_name = summary.get("personaname")
        if (
            not isinstance(persona_name, str)
            or not persona_name.strip()
            or len(persona_name) > 128
        ):
            logger.warning("Steam profile lookup omitted a valid nickname")
            return SteamProfileResult.unavailable(steam_id)

        return SteamProfileResult(
            steam_id=steam_id,
            persona_name=persona_name.strip(),
            avatar_url=_validated_avatar_url(summary.get("avatarfull")),
            profile_status=ProfileStatus.AVAILABLE,
        )

    async def _read_response(
        self,
        client: httpx.AsyncClient,
        steam_id: str,
    ) -> bytes | None:
        async with client.stream(
            "GET",
            STEAM_PROFILE_URL,
            params={"key": self._api_key, "steamids": steam_id},
            timeout=PROFILE_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as response:
            if response.status_code != 200:
                logger.warning("Steam profile lookup returned an unavailable response")
                return None

            content = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                if len(content) + len(chunk) > MAX_PROFILE_RESPONSE_BYTES:
                    logger.warning("Steam profile lookup exceeded the response size limit")
                    return None
                content.extend(chunk)
            return bytes(content)

    @staticmethod
    def _matching_summary(payload: Any, steam_id: str) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        response = payload.get("response")
        if not isinstance(response, dict):
            return None
        players = response.get("players")
        if not isinstance(players, list) or len(players) != 1:
            return None
        summary = players[0]
        if not isinstance(summary, dict) or summary.get("steamid") != steam_id:
            return None
        return summary
