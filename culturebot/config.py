import os
import pathlib
import typing

import dotenv
import hikari
import yaml

from ext import setei

dotenv.load_dotenv(".env")

__all__ = ["Config", "Tokens", "load_config"]


class Tokens(setei.Config):
    bot: str = setei.env("BOT_TOKEN")

    postgres: str = setei.env("POSTGRES")

    google_api_key: typing.Optional[str] = setei.env("GOOGLE_API_KEY")
    google_client_id: typing.Optional[str] = setei.env("GOOGLE_CLIENT_ID")
    google_client_secret: typing.Optional[str] = setei.env("GOOGLE_CLIENT_SECRET")

    github_client_id: typing.Optional[str] = setei.env("GITHUB_CLIENT_ID")
    github_client_secret: typing.Optional[str] = setei.env("GITHUB_CLIENT_SECRET")

    redis_address: typing.Optional[str] = setei.env("REDIS_ADDRESS")
    redis_password: typing.Optional[str] = setei.env("REDIS_PASSWORD")

    tracemoe_key: typing.Optional[str] = setei.env("TRACEMOE_KEY")
    saucenao_key: typing.Optional[str] = setei.env("SAUCENAO_KEY")
    deepl_key: typing.Optional[str] = setei.env("DEEPL_KEY")


class Config(setei.Config):
    tokens: Tokens
    prefixes: typing.List[str] = setei.conf("prefixes")
    log_level: str = setei.conf("log_level", default="INFO")
    intents: hikari.Intents = setei.conf("intents", default=hikari.Intents.ALL_UNPRIVILEGED)
    cache: hikari.api.CacheComponents = setei.conf("cache", default=hikari.api.CacheComponents.ALL)
    declare_global_commands: typing.Union[typing.List[hikari.Snowflake], bool] = setei.conf("test_guilds", default=True)

    memebin: typing.Optional[str] = setei.conf("memebin")


def load_config(config_path: typing.Optional[typing.Union[str, os.PathLike[str]]] = None) -> Config:
    path = pathlib.Path(config_path or "config.yaml")
    config = yaml.safe_load(path.read_text())

    return Config.load(config)


if __name__ == "__main__":
    import devtools

    devtools.debug(load_config())
