import typing

import aiohttp
import fastapi
import yarl

from . import tokens

__all__ = ["OAuth2"]

T = typing.TypeVar("T", covariant=True)


class OAuth2:
    name: typing.ClassVar[str]
    authorize_url: typing.ClassVar[str]
    token_url: typing.ClassVar[str]
    me_url: typing.ClassVar[str]

    client_id: str
    client_secret: str
    scopes: typing.Sequence[str]
    redirect_uri: typing.Optional[str]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: typing.Optional[typing.Sequence[str]] = None,
        *,
        redirect_uri: typing.Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self.redirect_uri = redirect_uri

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "name"):
            cls.name = cls.__name__.split("OAuth")[0].lower()

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

    async def callback(self, request: fastapi.Request) -> typing.Optional[tokens.Token]:
        if error := request.query_params.get("error"):
            return None

        body = {"code": request.query_params["code"], "redirect_uri": self.get_redirect_uri(request)}
        token = await self.request_token(body, "authorization_code")

        return tokens.Token(self, token)

    async def request_token(
        self,
        body: typing.Mapping[str, typing.Any],
        grant_type: typing.Optional[str] = None,
    ) -> typing.Dict[str, typing.Any]:
        body = dict(body).copy()
        body.update(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type=grant_type or body["grant_type"],
        )
        headers = {"Accept": "application/json"}

        async with aiohttp.request("POST", self.token_url, headers=headers, data=body) as r:
            return await r.json()
