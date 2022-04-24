from __future__ import annotations

import logging
import typing

import aiohttp
import alluka
import hikari
import hikari.applications
import tanjun

from ext import oauth, prettier

from . import config, sql
from .utility import files

__all__ = ["build_gateway_bot"]

_LOGGER = logging.getLogger(__name__)


async def starting(client: alluka.Injected[tanjun.Client], config: alluka.Injected[config.Config]):
    client.set_type_dependency(aiohttp.ClientSession, aiohttp.ClientSession())

    if config.tokens.google_client_id and config.tokens.google_client_secret:
        google = oauth.GoogleOAuth(
            config.tokens.google_client_id,
            config.tokens.google_client_secret,
            scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/drive.file"],
        )
        client.set_type_dependency(type(google), google)
    if config.tokens.discord_client_id and config.tokens.discord_client_secret:
        discord = oauth.DiscordOAuth(
            config.tokens.discord_client_id,
            config.tokens.discord_client_secret,
            scopes=["identify"],
        )
        client.set_type_dependency(type(discord), discord)


async def closing(
    session: alluka.Injected[typing.Optional[aiohttp.ClientSession]],
):
    if session:
        await session.close()


def build_gateway_bot(
    configuration: typing.Optional[config.Config] = None,
) -> tuple[hikari.impl.GatewayBot, tanjun.Client]:
    """Build a gateway bot with a bound client."""
    if configuration is None:
        configuration = config.load_config()

    bot = hikari.GatewayBot(
        configuration.tokens.bot,
        logs=configuration.log_level,
        intents=configuration.intents,
        cache_settings=hikari.impl.CacheSettings(components=configuration.cache),
    )

    connection = sql.Connection(configuration.tokens.postgres)

    # TODO: on_error
    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            declare_global_commands=configuration.declare_global_commands,
        )
        .add_prefix(configuration.prefixes)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, connection.connect)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, connection.close)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, starting)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, closing)
        .set_type_dependency(sql.Connection, connection)
        .set_type_dependency(config.Config, configuration)
        .set_type_dependency(config.Tokens, configuration.tokens)
        .set_type_dependency(tanjun.LazyConstant[hikari.Application], tanjun.LazyConstant(bot.rest.fetch_application))
        .load_modules(*files.search_directory("culturebot/components"))
    )

    _LOGGER.debug("Created client with following configuration:\n%s", prettier.pformat(configuration))

    return bot, client
