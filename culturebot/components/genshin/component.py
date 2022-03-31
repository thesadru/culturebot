import typing

import alluka
import sqlmodel
import tanchi
import tanjun

import culturebot.sql
from culturebot.sql.models import genshin as genshin_models

group = tanjun.slash_command_group("genshin", "Genshin API")


# TODO: modal


@group.with_command
@tanchi.as_slash_command(default_to_ephemeral=True)
async def register(
    context: tanjun.abc.SlashContext,
    /,
    uid: str,
    hoyolab_id: typing.Optional[str] = None,
    authkey: typing.Optional[str] = None,
    cookies: typing.Optional[str] = None,
    *,
    session: alluka.Injected[culturebot.sql.AsyncSession],
):
    """Register your genshin data

    Args:
        uid: Your genshin uid
        hoyolab_id: Your hoyolab id
        authkey: The authkey found in your logfiles
        cookies: The raw cookie header
    """
    statement = (
        sqlmodel.select(genshin_models.GenshinUser)
        .where(genshin_models.GenshinUser.discord_id == str(context.author.id))
        .limit(1)
    )
    user = (await session.exec(statement)).first()

    if user is not None:
        user.uid = uid
        user.hoyolab_id = user.hoyolab_id or hoyolab_id
        user.authkey = user.authkey or authkey
        user.cookies = user.cookies or cookies

        await context.respond(f"Changed uid to {uid}")
    else:
        user = genshin_models.GenshinUser(
            uid=uid,
            hoyolab_id=hoyolab_id,
            discord_id=str(context.author.id),
            cookies=cookies,
            authkey=authkey,
        )

        await context.respond(f"Registered new user as {uid}")

    session.add(user)
    await session.commit()


# TODO: Remove
@group.with_command
@tanchi.as_slash_command(default_to_ephemeral=True)
async def register_info(
    context: tanjun.abc.SlashContext,
    *,
    session: alluka.Injected[culturebot.sql.AsyncSession],
):
    """Display registered genshin data"""
    statement = (
        sqlmodel.select(genshin_models.GenshinUser)
        .where(genshin_models.GenshinUser.discord_id == str(context.author.id))
        .limit(1)
    )
    user = (await session.exec(statement)).first()
    if user is None:
        await context.respond("Not registered")
        return

    await context.respond("```json\n" + user.json() + "\n```")


component = tanjun.Component(name="genshin").load_from_scope()
loader = component.make_loader()
