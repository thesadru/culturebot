import hikari
import tanchi
import tanjun

from culturebot.components import about as about_component

from .embed import INFOS
from .resolve import resolve_argument


@tanchi.as_slash_command()
async def info(
    context: tanjun.abc.SlashContext,
    obj: str,
    *,
    my_user: hikari.OwnUser = tanjun.inject_lc(hikari.OwnUser),
):
    """Get the info of any object"""
    resolved = await resolve_argument(context, obj)

    if isinstance(resolved, hikari.PartialUser) and resolved.id == my_user.id:
        await about_component.about.execute(context)
        return

    for info in INFOS:
        if not isinstance(resolved, info.type):
            continue

        embed = info.callback(resolved)
        await context.respond(embed)
        return

    await context.respond("Could not parse input")


component = tanjun.Component(name="basic").load_from_scope()
loader = component.make_loader()
