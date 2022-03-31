import datetime
import platform
import time
import typing

import hikari
import psutil
import tanchi
import tanjun
from hikari import snowflakes

culturebot = tanjun.slash_command_group("culturebot", "Info about this bot")


_about_lines: list[tuple[str, typing.Callable[[hikari.api.Cache], int]]] = [
    ("Guild channels: {0}", lambda c: len(c.get_guild_channels_view())),
    ("Emojis: {0}", lambda c: len(c.get_emojis_view())),
    ("Available Guilds: {0}", lambda c: len(c.get_available_guilds_view())),
    ("Unavailable Guilds: {0}", lambda c: len(c.get_unavailable_guilds_view())),
    ("Invites: {0}", lambda c: len(c.get_invites_view())),
    ("Members: {0}", lambda c: sum(len(record) for record in c.get_members_view().values())),
    ("Messages: {0}", lambda c: len(c.get_messages_view())),
    ("Presences: {0}", lambda c: sum(len(record) for record in c.get_presences_view().values())),
    ("Roles: {0}", lambda c: len(c.get_roles_view())),
    ("Users: {0}", lambda c: len(c.get_users_view())),
    ("Voice states: {0}", lambda c: sum(len(record) for record in c.get_voice_states_view().values())),
]


def cache_check(ctx: tanjun.abc.Context) -> bool:
    if ctx.cache:
        return True

    raise tanjun.CommandError("Client is cache-less")


@culturebot.with_command
@tanchi.as_slash_command()
async def about(
    context: tanjun.abc.Context,
    *,
    process: psutil.Process = tanjun.cached_inject(psutil.Process),
    me: hikari.OwnUser = tanjun.inject_lc(hikari.OwnUser),
    my_application: hikari.Application = tanjun.inject_lc(hikari.Application),
    cache: typing.Optional[hikari.api.Cache] = tanjun.inject(type=typing.Optional[hikari.api.Cache]),
) -> None:
    """Get basic information about the current bot instance."""
    start_date = datetime.datetime.fromtimestamp(process.create_time())
    uptime = datetime.datetime.now() - start_date
    memory_usage: float = process.memory_full_info().uss / 1024**2
    cpu_usage: float = process.cpu_percent() / psutil.cpu_count()
    memory_percent: float = process.memory_percent()

    if context.shards and context.shards.shard_count > 2 and context.guild_id:
        shard_id = snowflakes.calculate_shard_id(context.shards.shard_count, context.guild_id)
        name = f"{me.username}: Shard {shard_id + 1} of {context.shards.shard_count}"
    else:
        name = me.username

    embed = (
        hikari.Embed(description=my_application.description)
        .set_author(name=name, url=hikari.__url__, icon=me.avatar_url)
        .add_field(name="Uptime", value=str(uptime), inline=True)
        .add_field(
            name="Process",
            value=f"{memory_usage:.2f} MB ({memory_percent:.0f}%)\n{cpu_usage:.2f}% CPU",
            inline=True,
        )
        .set_footer(text=f"Made with Hikari v{hikari.__version__} (python {platform.python_version()})")
    )

    if cache is not None:
        cache_stats_lines: list[str] = []

        for line_template, callback in _about_lines:
            line = line_template.format(callback(cache))
            cache_stats_lines.append(line)

        # This also accounts for the decimal place and 4 decimal places
        cache_stats = "\n".join(cache_stats_lines)
        embed.add_field(name="Standard cache stats", value=f"```{cache_stats}```")

    await context.respond(embed=embed)


@culturebot.with_command
@tanchi.as_slash_command()
async def ping(context: tanjun.abc.Context) -> None:
    """Get the bot's current delay."""
    heartbeat_latency = context.shards.heartbeat_latency * 1_000 if context.shards else float("NAN")

    start_time = time.perf_counter()
    await context.respond(f"PONG\n - REST: calculating\n - Gateway: {heartbeat_latency:.0f}ms")
    time_taken = (time.perf_counter() - start_time) * 1_000

    await context.edit_last_response(f"PONG\n - REST: {time_taken:.0f}ms\n - Gateway: {heartbeat_latency:.0f}ms")


component = tanjun.Component(name="about").load_from_scope()
loader = component.make_loader()
