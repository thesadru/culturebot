import asyncio
import functools
import re
import typing

import hikari
import tanjun

__all__ = ["resolve_argument"]

T = typing.TypeVar("T", bound=typing.Any)


def is_snowflake(potential: typing.Any) -> bool:
    return isinstance(potential, int) and 10**19 > potential > 10**16


def find_id(iterable: typing.Iterable[T], obj_id: hikari.Snowflakeish) -> typing.Optional[T]:
    for obj in iterable:
        if obj.id == obj_id:
            return obj

    return None


def parse_id(
    argument: tanjun.conversion._ArgumentT,
    parser: typing.Optional[tanjun.conversion._IDMatcherSig] = None,
) -> typing.Optional[hikari.Snowflake]:
    parser = parser or tanjun.conversion._make_snowflake_parser(re.compile(r"^(\d+)$"))

    try:
        snowflake = parser(argument)
    except ValueError:
        return None

    if is_snowflake(snowflake):
        return snowflake

    return None


def parse_message_id(argument: str) -> typing.Tuple[typing.Optional[int], typing.Optional[int]]:
    try:
        channel_id, message_id = tanjun.conversion.parse_message_id(argument)
    except ValueError:
        return None, None

    if is_snowflake(message_id) and not (channel_id is not None and not is_snowflake(channel_id)):
        return channel_id, message_id

    return None, None


def get_obj(
    argument: tanjun.conversion._ArgumentT,
    getter: typing.Callable[[int], T],
    parser: typing.Optional[tanjun.conversion._IDMatcherSig] = None,
) -> typing.Optional[T]:
    snowflake = parse_id(argument, parser)
    if snowflake is None:
        return None

    try:
        return getter(snowflake)
    except (ValueError, hikari.NotFoundError, hikari.ForbiddenError):
        return None


async def aget_obj(
    argument: tanjun.conversion._ArgumentT,
    getter: typing.Callable[[int], typing.Coroutine[typing.Any, typing.Any, T]],
    parser: typing.Optional[tanjun.conversion._IDMatcherSig] = None,
) -> typing.Optional[T]:
    snowflake = parse_id(argument, parser)
    if snowflake is None:
        return None

    try:
        return await getter(snowflake)
    except (ValueError, hikari.NotFoundError, hikari.ForbiddenError):
        return None


INVITE_PATTERN = re.compile(r"(?:(?:https?\:\/\/)?discord(?:\.gg|(?:app)?\.com\/invite)\/)?([A-Za-z\d\-\_]{3,8})(?!\w)")


def resolve_argument_cache(context: tanjun.abc.Context, argument: str):
    if context.cache is None:
        return None

    cache: hikari.api.Cache = context.cache

    get = functools.partial(get_obj, argument)

    if context.guild_id is not None:
        if value := get(functools.partial(cache.get_member, context.guild_id), tanjun.conversion.parse_user_id):
            return value
    if value := get(cache.get_user, tanjun.conversion.parse_user_id):
        return value
    if value := get(cache.get_guild_channel, tanjun.conversion.parse_channel_id):
        return value
    if value := get(cache.get_emoji, tanjun.conversion.parse_emoji_id):
        return value
    if value := get(cache.get_guild):
        return value
    if value := get(cache.get_role, tanjun.conversion.parse_role_id):
        return value

    _, message_id = parse_message_id(argument)
    if message_id and (value := cache.get_message(message_id)):
        return value

    if match := INVITE_PATTERN.match(argument):
        if invite := cache.get_invite(match[1]):
            return invite

    return None


async def resolve_argument_rest(context: tanjun.abc.Context, argument: str):
    rest: hikari.api.RESTClient = context.rest

    get = functools.partial(aget_obj, argument)

    # do expensive fetches only in case of a mention
    if not re.match(r"\d+", argument):
        fetchers: list[typing.Awaitable[typing.Any]] = [
            get(rest.fetch_user, tanjun.conversion.parse_user_id),
            get(rest.fetch_channel, tanjun.conversion.parse_channel_id),
        ]

        if context.guild_id is not None:
            fetchers += [
                get(functools.partial(rest.fetch_member, context.guild_id), tanjun.conversion.parse_user_id),
                get(functools.partial(rest.fetch_emoji, context.guild_id), tanjun.conversion.parse_emoji_id),
            ]

        for value in await asyncio.gather(*fetchers):
            if value is not None:
                return value
    else:
        # users and guilds are the only ones worth fetching in case of an id
        fetchers = [get(rest.fetch_user), get(rest.fetch_guild_preview)]
        if context.guild_id is not None:
            fetchers += [get(functools.partial(rest.fetch_member, context.guild_id))]

        for value in await asyncio.gather(*fetchers):
            if value is not None:
                return value

    channel_id, message_id = parse_message_id(argument)
    if message_id and channel_id and (value := await rest.fetch_message(channel_id, message_id)):
        return value

    if match := INVITE_PATTERN.match(argument):
        try:
            if invite := await rest.fetch_invite(match[1]):
                return invite
        except (hikari.NotFoundError, hikari.ForbiddenError):
            pass

    return None


async def resolve_argument(context: tanjun.abc.Context, argument: str):
    if value := resolve_argument_cache(context, argument):
        return value

    if value := (await resolve_argument_rest(context, argument)):
        return value

    if snowflake := parse_id(argument):
        return hikari.Snowflake(snowflake)

    try:
        return hikari.Color.of(argument)
    except ValueError:
        pass

    return argument
