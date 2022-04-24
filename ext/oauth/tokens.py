from __future__ import annotations

import collections
import collections.abc
import datetime
import typing

import aiohttp
import aiohttp.typedefs

from . import oauth

__all__ = ["Token"]


class Token(collections.abc.Mapping[str, typing.Any]):
    service: oauth.OAuth2

    access_token: str
    refresh_token: str
    expires: datetime.datetime
    token_type: str
    scope: str

    def __init__(self, service: oauth.OAuth2, token: typing.Mapping[str, typing.Any]) -> None:
        self.service = service

        self.access_token = token["access_token"]
        self.refresh_token = token["refresh_token"]

        if expires := token.get("expires"):
            self.expires = expires
        else:
            self.expires_in = token["expires_in"]

        self.token_type = token.get("token_type", "Bearer")
        self.scope = token["scope"]

    def __getitem__(self, key: str) -> typing.Any:
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(*e.args) from e

    def __len__(self) -> int:
        return 3

    def __iter__(self) -> typing.Iterator[str]:
        return iter(("access_token", "refresh_token", "expires", "scope"))

    @property
    def expires_in(self) -> float:
        return (self.expires - datetime.datetime.now(datetime.timezone.utc)).total_seconds()

    @expires_in.setter
    def expires_in(self, expires_in: float) -> None:
        self.expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)

    @property
    def headers(self) -> typing.Mapping[str, typing.Any]:
        return {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}

    async def _refresh(self) -> None:
        body = {"refresh_token": self.refresh_token}
        token = await self.service.request_token(body, "refresh_token")

        self.access_token = token["access_token"]
        self.expires_in = token["expires_in"]

    async def refresh(self) -> None:
        if self.expires <= datetime.datetime.now(datetime.timezone.utc):
            await self._refresh()

    async def request(self, method: str, url: aiohttp.typedefs.StrOrURL, **kwargs: typing.Any) -> typing.Any:
        await self.refresh()

        async with aiohttp.request(method, url, headers=self.headers, **kwargs) as response:
            return await response.json()

    async def get_me(self) -> typing.Mapping[str, typing.Any]:
        return await self.request("GET", self.service.me_url)
