import typing

import sqlmodel

__all__ = ["GenshinUser"]


class GenshinUser(sqlmodel.SQLModel, table=True):
    discord_id: typing.Optional[str] = sqlmodel.Field(default=None, primary_key=True)

    uid: str = sqlmodel.Field(default=None, index=True)
    hoyolab_id: typing.Optional[str] = None

    cookies: typing.Optional[str] = None
    authkey: typing.Optional[str] = sqlmodel.Field(max_length=2000)
