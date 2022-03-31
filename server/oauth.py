import typing

import aiohttp
import alluka
import yarl
from aiohttp import web

from culturebot import sql
from culturebot.sql.models import oauth as oauth_models
from server import dependencies

routes = web.RouteTableDef()

app = web.Application()


class Oauth2(web.AbstractRouteDef):
    NAME: str
    AUTHORIZE_URL: typing.ClassVar[yarl.URL]
    TOKEN_URL: typing.ClassVar[yarl.URL]

    client_id: str
    client_secret: str
    scopes: list[str]

    oauth_model: typing.Type[typing.Any] = dict

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: typing.Optional[list[str]] = None,
        *,
        session: typing.Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self._session = session

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()

        return self._session

    def register(self, router: web.UrlDispatcher) -> list[web.AbstractRoute]:
        return [
            router.add_route("GET", f"/{self.NAME}", self.auth, name=f"oauth.{self.NAME}.auth"),
            router.add_route("GET", f"/{self.NAME}/callback", self.callback, name=f"oauth.{self.NAME}.callback"),
        ]

    def get_redirect_uri(self, request: web.Request) -> str:
        relative = request.app.router[f"oauth.{self.NAME}.callback"].url_for()
        return str(request.url.with_path(relative.path))

    async def auth(self, request: web.Request) -> web.Response:
        query = {
            "client_id": self.client_id,
            "redirect_uri": self.get_redirect_uri(request),
            "response_type": "code",
            "scope": " ".join(self.scopes),
        }

        location = self.AUTHORIZE_URL.update_query(query)
        return web.HTTPTemporaryRedirect(location=location)

    async def callback(self, request: web.Request) -> web.Response:
        if error := request.query.get("error"):
            return await self.on_error(request, error)

        headers = {"Accept": "application/json"}
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": request.query["code"],
            "redirect_uri": self.get_redirect_uri(request),
            "grant_type": "authorization_code",
        }

        async with self.session.post(self.TOKEN_URL, headers=headers, data=body) as r:
            data = await r.json()

        return await self.on_login(request, self.oauth_model(**data))

    async def on_login(self, request: web.Request, data: typing.Any) -> web.Response:
        return web.json_response(data)

    async def on_error(self, request: web.Request, error: str) -> web.Response:
        raise web.HTTPInternalServerError(text=f"Unhandled OAuth2 Error: {error}")


class StorerOauth(Oauth2):
    oauth_model = oauth_models.OAuth

    @dependencies.injected
    async def store(self, model: typing.Any, session: alluka.Injected[sql.AsyncSession] = ...) -> None:
        session.add(model)
        await session.commit()

    async def on_login(self, request: web.Request, data: typing.Any) -> web.Response:
        return await super().on_login(request, data)


class GithubOauth(Oauth2):
    NAME = "github"

    AUTHORIZE_URL = yarl.URL("https://github.com/login/oauth/authorize")
    TOKEN_URL = yarl.URL("https://github.com/login/oauth/access_token")

    oauth_model = oauth_models.GoogleOAuth


class GoogleOauth(Oauth2):
    NAME = "google"

    AUTHORIZE_URL = yarl.URL("https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent")
    TOKEN_URL = yarl.URL("https://oauth2.googleapis.com/token")

    async def on_login(self, request: web.Request, data: dict[str, typing.Any]) -> web.Response:
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        async with self.session.get(
            "https://www.googleapis.com/oauth2/v1/userinfo?alt=json", headers=headers
        ) as response:
            print(await response.text())
            data = await response.json()

        return web.json_response(data)

    oauth_model = oauth_models.GithubOauth
