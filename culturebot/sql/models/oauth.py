from __future__ import annotations

import datetime
import typing

import hikari
import hikari.users
import pydantic
import sqlalchemy
import sqlmodel

from culturebot.sql.patch import Relationship

TZAWARE_DT = sqlmodel.DateTime(timezone=True)


class OAuthUser(sqlmodel.SQLModel):
    if typing.TYPE_CHECKING:
        id: str
        oauth: OAuth


class OAuth(sqlmodel.SQLModel):
    access_token: str = ""
    refresh_token: str = ""
    scope: str = ""
    token_type: str = "Bearer"
    expires: typing.Optional[datetime.datetime] = sqlmodel.Field(sa_column=sqlalchemy.Column(TZAWARE_DT))

    if typing.TYPE_CHECKING:
        user: OAuthUser

    @pydantic.root_validator(pre=True)
    def __parse_expires_in(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        if expires_in := values.get("expires_in"):
            now = datetime.datetime.now().astimezone(datetime.timezone.utc)
            values["expires"] = now + datetime.timedelta(seconds=expires_in)

        return values

    @property
    def scopes(self) -> typing.Sequence[str]:
        return self.scope.split(" ")


class GoogleUser(OAuthUser, table=True):
    id: str = sqlmodel.Field(primary_key=True)
    name: str
    picture: typing.Optional[str] = None
    locale: str = "en"

    oauth: GoogleOAuth = Relationship(back_populates="user", uselist=False)


class GoogleOAuth(OAuth, table=True):
    user_id: str = sqlmodel.Field(primary_key=True, foreign_key="googleuser.id")

    user: GoogleUser = Relationship(back_populates="oauth", uselist=False)


class DiscordUser(OAuthUser, table=True):
    id: str = sqlmodel.Field(primary_key=True)
    username: str
    discriminator: str
    avatar: str
    mfa_enabled: bool
    locale: str
    flags: hikari.UserFlag

    oauth: DiscordOAuth = Relationship(back_populates="user", uselist=False)

    @property
    def hikari_user(self) -> hikari.OwnUser:
        return self.get_hikari_user()

    def get_hikari_user(self, app: typing.Optional[hikari.EntityFactoryAware] = None):
        if isinstance(app, hikari.EntityFactoryAware):
            entity_factory = app.entity_factory
        else:
            entity_factory = hikari.impl.EntityFactoryImpl(NotImplemented)

        return entity_factory.deserialize_my_user(self.dict())


class DiscordOAuth(OAuth, table=True):
    user_id: str = sqlmodel.Field(primary_key=True, foreign_key="discorduser.id")

    user: DiscordUser = Relationship(back_populates="oauth", uselist=False)
