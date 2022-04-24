import os
import pathlib
import typing

import dotenv
import hikari
import yaml

from ext import setei

dotenv.load_dotenv(".env")  # type: ignore[reportUnknownMemberType]

__all__ = ["Config", "Tokens", "load_config"]


class Tokens(setei.Config):
    bot: str = setei.env("BOT_TOKEN")

    postgres: str = setei.env("POSTGRES")

    google_api_key: typing.Optional[str] = setei.env("GOOGLE_API_KEY")
    google_client_id: typing.Optional[str] = setei.env("GOOGLE_CLIENT_ID")
    google_client_secret: typing.Optional[str] = setei.env("GOOGLE_CLIENT_SECRET")

    github_client_id: typing.Optional[str] = setei.env("GITHUB_CLIENT_ID")
    github_client_secret: typing.Optional[str] = setei.env("GITHUB_CLIENT_SECRET")

    discord_client_id: typing.Optional[str] = setei.env("DISCORD_CLIENT_ID")
    discord_client_secret: typing.Optional[str] = setei.env("DISCORD_CLIENT_SECRET")

    redis_address: typing.Optional[str] = setei.env("REDIS_ADDRESS")
    redis_password: typing.Optional[str] = setei.env("REDIS_PASSWORD")

    tracemoe_key: typing.Optional[str] = setei.env("TRACEMOE_KEY")
    saucenao_key: typing.Optional[str] = setei.env("SAUCENAO_KEY")
    deepl_key: typing.Optional[str] = setei.env("DEEPL_KEY")


class Memebin(setei.Config):
    file: str = setei.conf("memebin.file")
    user: str = setei.conf("memebin.user")


class Config(setei.Config):
    tokens: Tokens

    prefixes: typing.List[str] = setei.conf("prefixes")
    log_level: str = setei.conf("log_level", default="INFO")
    intents: hikari.Intents = setei.conf("intents", default=hikari.Intents.ALL_UNPRIVILEGED)
    cache: hikari.api.CacheComponents = setei.conf("cache", default=hikari.api.CacheComponents.ALL)
    declare_global_commands: typing.Union[typing.List[hikari.Snowflake], bool] = setei.conf("test_guilds", default=True)

    memebin: Memebin


_cached: Config = NotImplemented


def load_config(
    config_path: typing.Optional[typing.Union[str, os.PathLike[str]]] = None,
    *,
    force: bool = False,
) -> Config:
    """Load the main configuration."""
    global _cached
    if not force and _cached is not NotImplemented:
        return _cached

    path = pathlib.Path(config_path or "config.yaml")
    config = yaml.safe_load(path.read_text())

    return (_cached := Config.load(config))


if __name__ == "__main__":
    from ext import prettier

    prettier.debug(load_config())
