from fastapi import Request

from cs_avatar.auth.steam_openid import SteamOpenIDService
from cs_avatar.auth.steam_profile import SteamProfileClient
from cs_avatar.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_openid_service(request: Request) -> SteamOpenIDService:
    return SteamOpenIDService(get_settings(request))


def get_steam_profile_client(request: Request) -> SteamProfileClient:
    settings = get_settings(request)
    return SteamProfileClient(settings.steam_web_api_key)
