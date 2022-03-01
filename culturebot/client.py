from __future__ import annotations

import logging
import os
import pkgutil
import typing

import aiohttp
import devtools
import hikari
import hikari.applications
import tanjun
import yuyo

from . import config

__all__ = ["build_gateway_bot"]

_LOGGER = logging.getLogger(__name__)


def search_directory(path: str) -> typing.Iterator[str]:
    """Walk through a directory and yield all modules."""
    relpath = os.path.relpath(path)  # relative and normalized

    prefix = relpath.replace(os.sep, ".")

    for finder, name, ispkg in pkgutil.iter_modules([path]):
        if ispkg:
            name = name + "." + "component"

        yield prefix + "." + name


async def starting(client: tanjun.Client = tanjun.inject(type=tanjun.Client)):
    client.set_type_dependency(aiohttp.ClientSession, aiohttp.ClientSession())


async def closing(client: tanjun.Client = tanjun.inject(type=tanjun.Client)):
    session = client.get_type_dependency(aiohttp.ClientSession)
    if not isinstance(session, tanjun.injecting.Undefined):
        await session.close()


async def on_reaction_add(event: hikari.ReactionAddEvent):
    if not isinstance(event.app, hikari.CacheAware):
        return
    if not (me := event.app.cache.get_me()):
        return

    if not event.is_for_emoji("🛑"):
        return

    if message := event.app.cache.get_message(event.message_id):
        if message.author.id == me.id:
            await message.delete()


def build_gateway_bot(configuration: config.Config = None) -> tuple[hikari.impl.GatewayBot, tanjun.Client]:
    """Build a gateway bot with a bound client."""
    if configuration is None:
        configuration = config.load_config()

    bot = hikari.GatewayBot(
        configuration.tokens.bot,
        logs=configuration.log_level,
        intents=configuration.intents,
        cache_settings=hikari.CacheSettings(components=configuration.cache),
    )
    bot.subscribe(hikari.ReactionAddEvent, on_reaction_add)

    # TODO: Deletion custom id
    component_client = yuyo.ComponentClient.from_gateway_bot(bot, event_managed=False)

    # TODO: on_error
    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            declare_global_commands=configuration.declare_global_commands,
        )
        .add_prefix(configuration.prefixes)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, component_client.open)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, component_client.close)
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, starting)
        .add_client_callback(tanjun.ClientCallbackNames.CLOSING, closing)
        .set_type_dependency(yuyo.ComponentClient, component_client)
        .set_type_dependency(config.Config, configuration)
        .set_type_dependency(config.Tokens, configuration.tokens)
        .set_type_dependency(tanjun.LazyConstant[hikari.Application], tanjun.LazyConstant(bot.rest.fetch_application))
        .load_modules(*search_directory("culturebot/components"))
    )

    _LOGGER.debug("Created client with following configuration:\n%s", devtools.pformat(configuration))

    return bot, client
