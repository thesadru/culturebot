import dataclasses
import typing

import aiohttp
import yarl

__all__ = ["DeepL", "DeepLException"]


class DeepLException(Exception):
    """Base class for deepl module exceptions."""


class QuotaExceededException(DeepLException):
    """Quota for this billing period has been exceeded."""


class TooManyRequestsException(DeepLException):
    """The maximum number of failed attempts were reached."""


@dataclasses.dataclass
class TextResult:
    text: str
    detected_source_language: str


@dataclasses.dataclass
class Usage:
    character_count: int
    character_limit: int


@dataclasses.dataclass
class Language:
    language: str
    name: str
    supports_formality: bool = False


class DeepL:
    _session: typing.Optional[aiohttp.ClientSession] = None

    def __init__(self, token: str, version: int = 2, session: aiohttp.ClientSession = None) -> None:
        self.token = token
        self.version = version
        self._session = session

    @property
    def free(self) -> bool:
        return self.token.endswith(":fx")

    @property
    def base_url(self) -> yarl.URL:
        url = "https://api-free.deepl.com/" if self.free else "https://api.deepl.com/"
        url += f"v{self.version}/"
        return yarl.URL(url)

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        await self.session.close()

    def raise_for_status(self, status_code: int, json: typing.Dict[str, typing.Any]):
        message = ""
        if json is not None:
            if "message" in json:
                message += ", message: " + json["message"]
            if "detail" in json:
                message += ", detail: " + json["detail"]

        if 200 <= status_code < 400:
            return
        elif status_code == 456:
            raise QuotaExceededException(f"Quota has been exceeded{message}")
        elif status_code == 404:
            raise DeepLException(f"Not found, check server_url{message}")
        elif status_code == 400:
            raise DeepLException(f"Bad request{message}")
        elif status_code == 429:
            raise TooManyRequestsException(f"Too many requests{message}")
        else:
            raise DeepLException(f"Unexpected error: {json}")

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: typing.Dict[str, typing.Any] = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        headers = headers or {}

        headers["Authorization"] = "DeepL-Auth-Key " + self.token

        url = self.base_url.join(yarl.URL(endpoint))

        async with self.session.request(method, url, headers=headers, **kwargs) as response:
            data = await response.json()

            self.raise_for_status(response.status, data)

        return data

    async def get_usage(self):
        data = await self.request("GET", "usage")
        return Usage(**data)

    # TODO: Cache
    async def get_languages(self, target: bool = True) -> typing.List[Language]:
        data = {"type": "target" if target else "source"}
        json = await self.request("GET", "languages", data=data)
        return [Language(**i) for i in json]

    async def _supports_formality(self, lang: str) -> bool:
        languages = await self.get_languages(target=True)
        for language in languages:
            if language.language == lang:
                return language.supports_formality

        raise ValueError(f"Unknown language: {lang}")

    async def _translate(
        self,
        text: str,
        *,
        source_lang: str = None,
        target_lang: str,
        formal: bool = None,
    ) -> typing.List[TextResult]:

        data: typing.Dict[str, typing.Any] = {}

        data["text"] = text
        data["target_lang"] = str(target_lang).upper()
        if source_lang is not None:
            data["source_lang"] = str(source_lang).upper()
        if formal is not None and await self._supports_formality(target_lang):
            data["formality"] = "more" if formal else "less"

        json = await self.request("GET", "translate", data=data)

        return [TextResult(**i) for i in json.get("translations", [])]

    async def translate(
        self,
        text: str,
        *,
        source_lang: str = None,
        target_lang: str,
        formal: bool = None,
    ) -> str:
        data = await self._translate(
            text,
            source_lang=source_lang,
            target_lang=target_lang,
            formal=formal,
        )
        return "\n".join(i.text for i in data)
