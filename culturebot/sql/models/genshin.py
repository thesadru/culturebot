import typing

import genshin
import pydantic
import sqlalchemy
import sqlmodel
from genshin.client import manager as cookie_manager

__all__ = ["GenshinUser"]

UNIQUE_STR = sqlalchemy.Column(sqlalchemy.VARCHAR, unique=True)


class GenshinUser(sqlmodel.SQLModel, table=True):
    discord_id: typing.Optional[str] = sqlmodel.Field(default=None, primary_key=True)

    genshin_uid: str = sqlmodel.Field(default=None, sa_column=UNIQUE_STR)
    honkai_uid: str = sqlmodel.Field(default=None, sa_column=UNIQUE_STR)
    hoyolab_id: typing.Optional[str] = None

    cookies: typing.Optional[str] = None
    authkey: typing.Optional[str] = sqlmodel.Field(max_length=2000)

    lang: str = "en-us"
    region: genshin.Region = genshin.Region.OVERSEAS

    @property
    def client(self) -> genshin.Client:
        client = genshin.Client(
            cookies=self.cookies,
            authkey=self.authkey,
            lang=self.lang,
            region=self.region,
        )
        client.uids[genshin.Game.GENSHIN] = int(self.genshin_uid)
        client.uids[genshin.Game.HONKAI] = int(self.honkai_uid)
        return client

    @pydantic.validator("hoyolab_id")
    def __check_hoyolab_uid(
        cls,
        value: typing.Optional[int],
        values: typing.Dict[str, typing.Any],
    ) -> typing.Optional[int]:
        """Correct hoyolab_uid based on the cookies."""
        manager = cookie_manager.CookieManager(values.get("cookies"))
        if manager.user_id is None or value is None:
            return manager.user_id or value

        assert value == manager.user_id, "ltuid and hoyolab_id must match"

        return value
