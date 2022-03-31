import hikari
import tanjun

component = tanjun.Component(name="meta")

DELETE_EMOJI = "🛑"


@component.with_listener(hikari.ReactionAddEvent)
async def on_reaction_add(
    event: hikari.ReactionAddEvent,
    *,
    me: hikari.OwnUser = tanjun.inject_lc(hikari.OwnUser),
):
    if not isinstance(event.app, hikari.CacheAware):
        return

    if not event.is_for_emoji("🛑"):
        return

    if message := event.app.cache.get_message(event.message_id):
        if message.author.id == me.id:
            await message.delete()


loader = component.make_loader()
