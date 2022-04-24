import dataclasses
import typing

import genshin

__all__ = ["GenshinUser"]


@dataclasses.dataclass
class GenshinUser:
    __tablename__ = "auth.genshin"

    discord_id: typing.Optional[int]

    uid: typing.Optional[int]
    hoyolab_id: typing.Optional[int]

    cookies: typing.Optional[str]
    authkey: typing.Optional[str]

    lang: str = "en-us"
    region: str = genshin.Region.OVERSEAS

    @property
    def client(self) -> genshin.Client:
        client = genshin.Client(
            cookies=self.cookies,
            authkey=self.authkey,
            lang=self.lang,
            region=genshin.Region(self.region),
            game=genshin.Game.GENSHIN,
        )

        if self.uid:
            client.uids[genshin.Game.GENSHIN] = int(self.uid)

        return client
