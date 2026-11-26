import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

import httpx
from openid import fetchers
from openid.consumer.consumer import CANCEL, SUCCESS, GenericConsumer
from openid.consumer.discover import (
    OPENID_2_0_TYPE,
    OpenIDServiceEndpoint,
)
from openid.message import OPENID2_NS, Message
from openid.store.interface import OpenIDStore
from openid.store.nonce import SKEW

from cs_avatar.config import Settings

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_IDENTITY_PATTERN = re.compile(
    r"^https://steamcommunity\.com/openid/id/([0-9]{17})$"
)
STEAM_OPENID_TIMEOUT_SECONDS = 5.0
MAX_OPENID_RESPONSE_BYTES = 64 * 1024


class SteamOpenIDError(Exception):
    """The provider response could not be verified as a Steam identity."""

    def __init__(self, reason: str = "assertion_rejected") -> None:
        self.reason = reason
        super().__init__("Steam sign-in could not be verified")


class SteamOpenIDCancelled(SteamOpenIDError):
    """The player cancelled Steam sign-in."""

    def __init__(self) -> None:
        super().__init__("cancelled")


@dataclass(frozen=True)
class VerifiedSteamIdentity:
    steam_id: str
    response_nonce: str


class _SteamVerificationStore(OpenIDStore):
    def storeAssociation(self, server_url: str, association: object) -> None:
        return None

    def getAssociation(self, server_url: str, handle: str | None = None) -> None:
        return None

    def removeAssociation(self, server_url: str, handle: str) -> bool:
        return False

    def useNonce(self, server_url: str, timestamp: int, salt: str) -> bool:
        return abs(time.time() - timestamp) <= SKEW

    def cleanupNonces(self) -> int:
        return 0

    def cleanupAssociations(self) -> int:
        return 0


class _SteamOpenIDFetcher(fetchers.HTTPFetcher):
    def fetch(
        self,
        url: str,
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> fetchers.HTTPResponse:
        if url != STEAM_OPENID_ENDPOINT or body is None:
            raise ValueError("OpenID direct verification is restricted to Steam")

        request_headers = dict(headers or {})
        if not any(key.casefold() == "content-type" for key in request_headers):
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        with httpx.Client(
            timeout=STEAM_OPENID_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            with client.stream(
                "POST",
                url,
                content=body,
                headers=request_headers,
            ) as response:
                body_bytes = bytearray()
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    body_bytes.extend(chunk)
                    if len(body_bytes) > MAX_OPENID_RESPONSE_BYTES:
                        raise ValueError("Steam OpenID response exceeded its size limit")
                return fetchers.HTTPResponse(
                    final_url=url,
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=bytes(body_bytes).decode(response.encoding or "utf-8", errors="replace"),
                )


def configure_steam_openid_fetcher() -> None:
    fetchers.setDefaultFetcher(_SteamOpenIDFetcher())


class SteamOpenIDService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def begin(self, state: str) -> str:
        endpoint = OpenIDServiceEndpoint.fromOPEndpointURL(STEAM_OPENID_ENDPOINT)
        request = GenericConsumer(None).begin(endpoint)
        request.return_to_args["state"] = state
        return request.redirectURL(
            self._settings.steam_openid_realm,
            self._settings.steam_openid_return_to,
        )

    def verify(self, query: Mapping[str, str]) -> VerifiedSteamIdentity:
        if query.get("openid.mode") == "cancel":
            raise SteamOpenIDCancelled
        if query.get("openid.mode") != "id_res":
            raise SteamOpenIDError("invalid_mode")

        try:
            message = Message.fromPostArgs(dict(query))
            if not message.isOpenID2():
                raise SteamOpenIDError("invalid_protocol")
            claimed_id = message.getArg(OPENID2_NS, "claimed_id")
            identity_url = message.getArg(OPENID2_NS, "identity")
            op_endpoint = message.getArg(OPENID2_NS, "op_endpoint")
            response_nonce = message.getArg(OPENID2_NS, "response_nonce")
        except (KeyError, TypeError, ValueError) as error:
            raise SteamOpenIDError("malformed_message") from error

        identity_match = STEAM_IDENTITY_PATTERN.fullmatch(claimed_id or "")
        if (
            identity_match is None
            or identity_url != claimed_id
            or op_endpoint != STEAM_OPENID_ENDPOINT
            or response_nonce is None
        ):
            raise SteamOpenIDError("identity_mismatch")

        actual_return_to = message.getArg(OPENID2_NS, "return_to")
        callback_return_to = self._validated_callback_return_to(
            actual_return_to,
            query,
        )
        if callback_return_to is None:
            raise SteamOpenIDError(
                self._callback_return_to_reason(actual_return_to, query)
            )

        endpoint = OpenIDServiceEndpoint(
            claimed_id=claimed_id,
            server_url=STEAM_OPENID_ENDPOINT,
            type_uris=[OPENID_2_0_TYPE],
            local_id=identity_url,
        )
        configure_steam_openid_fetcher()
        consumer = GenericConsumer(_SteamVerificationStore())
        response = consumer.complete(message, endpoint, callback_return_to)
        if response.status == CANCEL:
            raise SteamOpenIDCancelled
        if response.status != SUCCESS or response.identity_url != claimed_id:
            raise SteamOpenIDError(
                self._failure_reason(response, actual_return_to, query)
            )

        return VerifiedSteamIdentity(
            steam_id=identity_match.group(1),
            response_nonce=response_nonce,
        )

    def _validated_callback_return_to(
        self,
        actual_return_to: str | None,
        query: Mapping[str, str],
    ) -> str | None:
        try:
            actual = urlsplit(actual_return_to or "")
            expected = urlsplit(self._settings.steam_openid_return_to)
            actual_port = actual.port
            expected_port = expected.port
        except ValueError:
            return None

        if (
            actual.scheme != expected.scheme
            or actual.hostname != expected.hostname
            or actual_port != expected_port
            or actual.path != expected.path
            or actual.username is not None
            or actual.password is not None
            or actual.fragment
        ):
            return None

        try:
            parameters = parse_qsl(
                actual.query,
                keep_blank_values=True,
                strict_parsing=True,
            )
        except ValueError:
            return None

        callback_parameters = dict(parameters)
        if callback_parameters.get("state") != query.get("state"):
            return None
        if len(callback_parameters) != len(parameters):
            return None
        return actual_return_to

    def _callback_return_to_reason(
        self,
        actual_return_to: str | None,
        query: Mapping[str, str],
    ) -> str:
        try:
            actual = urlsplit(actual_return_to or "")
            expected = urlsplit(self._settings.steam_openid_return_to)
            actual_port = actual.port
            expected_port = expected.port
        except ValueError:
            return "return_to_invalid"
        if actual.scheme != expected.scheme:
            return "return_to_scheme_mismatch"
        if actual.hostname != expected.hostname or actual_port != expected_port:
            return "return_to_authority_mismatch"
        if actual.path != expected.path:
            return "return_to_path_mismatch"
        return self._return_to_parameter_reason(actual_return_to, query)

    def _failure_reason(
        self,
        response: object,
        actual_return_to: str | None,
        query: Mapping[str, str],
    ) -> str:
        if getattr(response, "status", None) == SUCCESS:
            return "identity_mismatch"

        detail = str(getattr(response, "message", "")).casefold()
        if "does not match return url" in detail:
            try:
                actual = urlsplit(actual_return_to or "")
                expected = urlsplit(self._settings.steam_openid_return_to)
                actual_port = actual.port
                expected_port = expected.port
            except ValueError:
                return "return_to_invalid"
            if actual.scheme != expected.scheme:
                return "return_to_scheme_mismatch"
            if (
                actual.hostname != expected.hostname
                or actual_port != expected_port
            ):
                return "return_to_authority_mismatch"
            if actual.path != expected.path:
                return "return_to_path_mismatch"
            return self._return_to_parameter_reason(actual_return_to, query)
        if "return_to" in detail:
            return self._return_to_parameter_reason(actual_return_to, query)
        if "nonce" in detail:
            return "nonce_rejected"
        if "signature" in detail or "check_authentication" in detail:
            return "signature_rejected"
        if "discovery" in detail:
            return "identity_discovery_failed"
        if "signed" in detail or "required field" in detail:
            return "malformed_assertion"
        return "provider_rejected"

    @staticmethod
    def _return_to_parameter_reason(
        actual_return_to: str | None,
        query: Mapping[str, str],
    ) -> str:
        try:
            return_to_params = parse_qsl(
                urlsplit(actual_return_to or "").query,
                keep_blank_values=True,
                strict_parsing=True,
            )
        except ValueError:
            return "return_to_invalid"

        for key, value in return_to_params:
            if query.get(key) != value:
                if key == "state":
                    return "return_to_state_mismatch"
                return "return_to_argument_mismatch"
        for key, value in query.items():
            if key.startswith("openid.") or (key, value) in return_to_params:
                continue
            if key == "state":
                return "return_to_state_missing"
            return "callback_parameter_not_in_return_to"
        return "return_to_parameters_mismatch"
