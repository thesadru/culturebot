from __future__ import annotations

import dataclasses
import logging
import typing

import aiohttp
import aiohttp.typedefs
import hikari
import yarl

from ext import oauth

__all__ = ["Drive"]

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class Resource:
    drive: Drive = dataclasses.field(repr=False)

    kind: str
    id: str
    filename: str
    mimetype: str

    @classmethod
    def create(cls, drive: Drive, data: dict[str, typing.Any]) -> Resource:
        if data["mimeType"] == "application/vnd.google-apps.folder":
            return Folder.create(drive, data)

        return File.create(drive, data)


@dataclasses.dataclass
class File(Resource):
    FIELDS = "kind, id, name, mimeType, size, webViewLink, thumbnailLink"

    size: int
    url: yarl.URL
    thumbnail: yarl.URL

    @classmethod
    def create(cls, drive: Drive, data: dict[str, typing.Any]):
        return cls(
            drive,
            kind=data["kind"],
            id=data["id"],
            filename=data["name"],
            mimetype=data["mimeType"],
            size=int(data["size"]),
            url=yarl.URL(data["webViewLink"]),
            thumbnail=yarl.URL(data["thumbnailLink"]),
        )

    async def download(self, **params: typing.Any) -> aiohttp.StreamReader:
        return await self.drive.download_file(self.id, **params)

    async def get_attachment(self, spoiler: bool = False, **params: typing.Any) -> hikari.Bytes:
        return hikari.Bytes(
            await self.download(),
            self.filename,
            mimetype=self.mimetype,
            spoiler=spoiler,
        )


@dataclasses.dataclass
class Folder(Resource):
    url: yarl.URL

    @classmethod
    def create(cls, drive: Drive, data: dict[str, typing.Any]):
        return cls(
            drive,
            kind=data["kind"],
            id=data["id"],
            filename=data["name"],
            mimetype=data["mimeType"],
            url=yarl.URL(data["webViewLink"]),
        )

    def list(self, **params: typing.Any) -> typing.AsyncIterator[Resource]:
        return self.drive.list_directory(self.id, **params)


class Google:
    BASE_URL: yarl.URL

    def __init__(
        self,
        token: oauth.Token,
        session: typing.Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.token = token
        self._session = session

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()

        return self._session

    async def request(
        self,
        path: str,
        method: str = "GET",
        **kwargs: typing.Any,
    ) -> typing.Any:
        url = self.BASE_URL / path

        await self.token.refresh()

        async with self.session.request(method, url, headers=self.token.headers, **kwargs) as response:
            _LOGGER.debug(f"Requested %s (status code: %d)", path, response.status)

            if response.status == 204:
                return None

            data = await response.json()

            if not response.ok:
                raise Exception(data["error"])

            return data

    async def request_media(
        self,
        path: str,
        method: str = "GET",
        params: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        **kwargs: typing.Any,
    ) -> aiohttp.StreamReader:
        params = dict(params or {})
        params["alt"] = "media"

        await self.token.refresh()

        response = await self.session.request(
            method,
            self.BASE_URL / path,
            headers=self.token.headers,
            params=params,
            **kwargs,
        )

        if not response.ok:
            raise Exception(f"Media ratelimited: {path}\n{await response.text()}")

        _LOGGER.debug(f"Downloading media %r (content length: %s)", path, response.content_length)

        return response.content


class Drive(Google):
    BASE_URL = yarl.URL("https://www.googleapis.com/drive/v3")

    async def request_list(self, *, fields: str = File.FIELDS, **params: typing.Any) -> typing.Any:
        params["fields"] = f"nextPageToken, files({fields})"
        return await self.request("files", params=params)

    async def search_files(self, q: str, **params: typing.Any) -> typing.AsyncIterator[Resource]:
        while True:
            data = await self.request_list(q=q, **params)
            for file in data["files"]:
                yield Resource.create(self, file)

            if "nextPageToken" not in data:
                break

            params["pageToken"] = data["nextPageToken"]

    def list_directory(self, parent: str, **params: typing.Any) -> typing.AsyncIterator[Resource]:
        return self.search_files(f"'{parent}' in parents", **params)

    async def download_file(self, file: str, **params: typing.Any):
        return await self.request_media(f"files/{file}", params=params)
