from __future__ import annotations

import datetime
import typing

import sqlmodel


class OAuth(sqlmodel.SQLModel):
    access_token: str = ""
    refresh_token: str = ""
    scope: str = ""
    token_type: str = "Bearer"
    expires: typing.Optional[datetime.datetime] = None


class GoogleUser(sqlmodel.SQLModel, table=True):
    id: str = sqlmodel.Field(primary_key=True)
    name: str
    picture: typing.Optional[str] = None
    locale: str = "en"

    oauth: GoogleOAuth = sqlmodel.Relationship(back_populates="user")


class GoogleOAuth(OAuth, table=True):
    user_id: str = sqlmodel.Field(primary_key=True, foreign_key="googleuser.id")

    user: GoogleUser = sqlmodel.Relationship(back_populates="oauth")


class GithubOauth(OAuth, table=True):
    ...
