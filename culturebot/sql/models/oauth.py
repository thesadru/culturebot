import dataclasses
import datetime
import typing

from ext import oauth

__all__ = ["OAuth"]


@dataclasses.dataclass
class OAuth:
    __tablename__ = "auth.oauth"

    service: str
    key: str
    access_token: str
    refresh_token: typing.Optional[str]
    scope: typing.Optional[str]
    expires: typing.Optional[datetime.datetime]
    token_type: str

    user_id: str

    def make_token(self, service: oauth.OAuth2) -> oauth.Token:
        return oauth.Token(
            service,
            dict(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                expires=self.expires,
                token_type=self.token_type,
                scope=self.scope,
            ),
        )
