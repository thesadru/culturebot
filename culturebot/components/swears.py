import collections
import json
import typing

import alluka
import hikari
import tanchi
import tanjun

from culturebot import sql

component = tanjun.Component(name="swears")

with open("swears.json") as file:
    data = json.load(file)
    SWEARS: typing.Mapping[str, str] = {swear: swear for swear in data["swears"]}
    SWEARS.update(data["aliases"])

INFLECTIONS = ["", "s", "es", "ed", "ing", "in", "ly", "ed", "er", "est"]


def count_swears(text: str, swears: typing.Mapping[str, str]) -> collections.Counter[str]:
    """Count swears in text."""
    counter: collections.Counter[str] = collections.Counter()
    for word in text.split():
        for inflection in INFLECTIONS:
            if word.endswith(inflection) and word.removesuffix(inflection) in swears:
                counter.update({swears[word.removesuffix(inflection)]: 1})
                break

    return counter


@component.with_listener(hikari.GuildMessageCreateEvent)
async def on_message(
    event: hikari.GuildMessageCreateEvent,
    *,
    connection: alluka.Injected[sql.Connection],
) -> None:
    if not event.content:
        return

    counter = count_swears(event.content, SWEARS)
    if not counter:
        return

    user = await connection.select(sql.models.SwearUser, user_id=event.author.id, guild_id=event.guild_id)
    if user:
        if user.optout:
            return
    else:
        expression = "INSERT INTO swears.user (user_id, guild_id) VALUES ($1, $2)"
        await connection.execute(expression, event.author.id, event.guild_id)

    expression = (
        "INSERT INTO swears.swear (swear, amount, user_id, guild_id) VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (user_id, guild_id, swear) DO UPDATE SET amount = swear.amount + $2"
    )

    for swear, amount in counter.items():
        x = await connection.execute(expression, swear, amount, event.author.id, event.guild_id)


swear_group = tanjun.slash_command_group("swears", "Swear commands")


@swear_group.with_command
@tanjun.with_guild_check
@tanchi.as_slash_command("user")
async def user_swears(
    context: tanjun.context.SlashContext,
    user: typing.Optional[hikari.Member] = None,
    *,
    connection: alluka.Injected[sql.Connection],
):
    """View the swears of a user.

    Args:
        user: The user to view the swears of.
    """
    user = user or context.member
    assert user is not None

    expression = "SELECT * FROM swears.swear WHERE user_id = $1 AND guild_id = $2 ORDER BY amount DESC LIMIT 10"
    swears = await connection.fetch(expression, user.id, context.guild_id, cls=sql.models.Swear)
    if not swears:
        await context.respond(f"{user} has never sworn in this server.")

    embed = hikari.Embed(
        title=f"{user}'s top 10 swears",
        color=0xFF0000,
        description="List of the the top 10 most used swears.",
    )
    embed.set_thumbnail(user.display_avatar_url)

    for rank, swear in enumerate(swears, 1):
        embed.add_field(
            f"{rank}. {swear.swear}",
            f"Used {swear.amount} time{'s' if swear.amount != 1 else ''}.",
        )

    await context.respond(embed=embed)


@swear_group.with_command
@tanjun.with_guild_check
@tanchi.as_slash_command("guild")
async def guild_swears(
    context: tanjun.context.SlashContext,
    *,
    connection: alluka.Injected[sql.Connection],
    cache: alluka.Injected[hikari.api.Cache],
):
    """View the swears of this guild."""
    expression = (
        "SELECT user_id, SUM(amount) as total FROM swears.swear WHERE guild_id = $1"
        "GROUP BY user_id ORDER BY 2 DESC LIMIT 10"
    )
    users = await connection.fetch(expression, context.guild_id, cls=sql.connection.AttributeRecord)
    if not users:
        await context.respond("There are no swears in this server.")

    user_ids = [user.user_id for user in users]
    s = ", ".join(sql.make_s(len(users), start=2))
    expression = f"SELECT * FROM swears.swear WHERE user_id IN ({s}) AND guild_id = $1 ORDER BY amount DESC"
    swears = await connection.fetch(expression, context.guild_id, *user_ids, cls=sql.models.Swear)

    #
    leaderboard: typing.Dict[int, typing.Tuple[int, typing.List[sql.models.Swear]]] = {
        user.user_id: (user.total, []) for user in users
    }
    for swear in swears:
        leaderboard[swear.user_id][1].append(swear)

    embed = hikari.Embed(
        title=f"Top 10 users.",
        color=0xFF0000,
        description="List of the the top 10 users with the most swears.",
    )

    for rank, (user_id, (total, swears)) in enumerate(leaderboard.items(), 1):
        embed.add_field(
            f"{rank}. {cache.get_user(user_id) or ''}",
            f"<@{user_id}> has sworn a total of **{total}** times.\n"
            f"Most common swears: {', '.join(f'**{swear.swear}**' for swear in swears[:5])}",
        )

    await context.respond(embed=embed)


component.load_from_scope()
loader = component.make_loader()
