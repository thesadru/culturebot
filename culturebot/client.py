from __future__ import annotations

import functools
import logging
import typing

import aiohttp
import alluka
import devtools
import hikari
import hikari.applications
import tanjun
from sqlalchemy.ext import asyncio as asqlalchmey

from . import config, sql
from .utility import files

__all__ = ["build_gateway_bot"]

_LOGGER = logging.getLogger(__name__)


async def starting(client: alluka.Injected[tanjun.Client]):
    client.set_type_dependency(aiohttp.ClientSession, aiohttp.ClientSession())


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

    engine = sql.create_engine(configuration.tokens.postgres, future=True)
    session = sql.create_session(engine)

    # TODO: on_error
    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            declare_global_commands=configuration.declare_global_commands,
        )
        .add_prefix(configuration.prefixes)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, functools.partial(sql.create_tables, engine))
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, session.close)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, starting)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, closing)
        .set_type_dependency(asqlalchmey.AsyncEngine, engine)
        .set_type_dependency(sql.AsyncSession, session)
        .set_type_dependency(config.Config, configuration)
        .set_type_dependency(config.Tokens, configuration.tokens)
        .set_type_dependency(tanjun.LazyConstant[hikari.Application], tanjun.LazyConstant(bot.rest.fetch_application))
        .load_modules(*files.search_directory("culturebot/components"))
    )

    _LOGGER.debug("Created client with following configuration:\n%s", devtools.pformat(configuration))

    return bot, client
