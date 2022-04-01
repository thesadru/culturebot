import typing

import aiohttp
import fastapi
import yarl

from culturebot.sql.models import oauth as oauth_models

__all__ = ["OAuth2", "DiscordOAuth", "GoogleOAuth"]

T = typing.TypeVar("T", covariant=True)


class OAuth2(typing.Generic[T]):
    name: str
    authorize_url: typing.ClassVar[str]
    token_url: typing.ClassVar[str]

    client_id: str
    client_secret: str
    scopes: typing.Sequence[str]
    redirect_uri: typing.Optional[str]

    oauth_model: type = dict

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: typing.Optional[typing.Sequence[str]] = None,
        redirect_uri: typing.Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self.redirect_uri = redirect_uri

    def get_redirect_uri(self, request: fastapi.Request) -> str:
        if self.redirect_uri is None:
            raise RuntimeError("redirect_uri not set")

        url = request.url.replace(path=yarl.URL(self.redirect_uri).path, query={})
        return str(url)

    def auth(self, request: fastapi.Request) -> fastapi.Response:
        query = {
            "client_id": self.client_id,
            "redirect_uri": self.get_redirect_uri(request),
            "response_type": "code",
            "scope": " ".join(self.scopes),
        }
        location = yarl.URL(self.authorize_url).update_query(query)

        return fastapi.responses.RedirectResponse(str(location))

    async def callback(self, request: fastapi.Request) -> typing.Optional[T]:
        if error := request.query_params.get("error"):
            return None

        headers = {"Accept": "application/json"}
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": request.query_params["code"],
            "redirect_uri": self.get_redirect_uri(request),
            "grant_type": "authorization_code",
        }

        async with aiohttp.request("POST", self.token_url, headers=headers, data=body) as r:
            data = await r.json()

        return await self.process(data)

    async def process(self, token: typing.Mapping[str, typing.Any]) -> T:
        return typing.cast("T", token)


class DiscordOAuth(OAuth2[oauth_models.DiscordUser]):
    name = "discord"

    authorize_url = "https://discord.com/api/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"

    async def process(self, token: typing.Mapping[str, typing.Any]) -> oauth_models.DiscordUser:
        url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {token['access_token']}"}

        async with aiohttp.request("GET", url, headers=headers) as response:
            data = await response.json()

        return oauth_models.DiscordUser(**data, oauth=oauth_models.DiscordOAuth(**token, user_id=data["id"]))


class GoogleOAuth(OAuth2[oauth_models.GoogleUser]):
    name = "google"

    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent"
    token_url = "https://oauth2.googleapis.com/token"

    async def process(self, token: typing.Mapping[str, typing.Any]) -> oauth_models.GoogleUser:
        url = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
        headers = {"Authorization": f"Bearer {token['access_token']}"}

        async with aiohttp.request("GET", url, headers=headers) as response:
            data = await response.json()

        return oauth_models.GoogleUser(**data, oauth=oauth_models.GoogleOAuth(**token, user_id=data["id"]))
