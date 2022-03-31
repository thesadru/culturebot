import typing

import aiohttp
import hikari
import hikari.files
import pysaucenao
import pysaucenao.containers
import tanchi
import tanjun

from culturebot import config

component = tanjun.Component(name="source")


def check_url_or_attachment(
    interaction: typing.Union[tanjun.abc.SlashContext, hikari.CommandInteraction],
    url: typing.Optional[str] = None,
    attachment: typing.Optional[typing.Union[hikari.Attachment, str]] = None,
) -> str:
    if isinstance(interaction, tanjun.abc.SlashContext):
        interaction = interaction.interaction

    if attachment is not None:
        if isinstance(attachment, str):
            assert interaction.resolved
            attachment = interaction.resolved.attachments[hikari.Snowflake(attachment)]

        url = attachment.url

    if url is None:
        raise tanjun.CommandError("Either a url or an attachment must be provided")

    return url


@tanchi.as_slash_command()
async def tracemoe(
    context: tanjun.context.SlashContext,
    url: typing.Optional[str] = None,
    attachment: typing.Optional[hikari.Attachment] = None,
    cut_borders: bool = False,
    anilist_id: typing.Optional[int] = None,
    result_size: typing.Literal["s", "m", "l"] = "l",
    *,
    session: aiohttp.ClientSession = tanjun.inject(type=aiohttp.ClientSession),
    tokens: config.Tokens = tanjun.inject(type=config.Tokens),
):
    """Gets the anime source using trace.moe

    Args:
        url: URL link to an image.
        attachment: An image attachment.
        cut_borders: whether to enable black border crop
        anilist_id: search for a matching scene only in a particular anime by Anilist ID
        result_size: the size of the resulting image, defaults to Large
    """
    url = check_url_or_attachment(context, url, attachment)

    query: dict[str, typing.Any] = dict(url=url, anilistInfo=1)
    if cut_borders:
        query.update(cutBorders=1)
    if anilist_id:
        query.update(anilistID=anilist_id)
    if tokens.tracemoe_key:
        query.update(key=tokens.tracemoe_key)

    r = await session.get("https://api.trace.moe/search", params=query)
    data = await r.json()

    if data["error"]:
        context.set_ephemeral_default(True)

        await context.respond(data["error"])
        return

    result = data["result"][0]

    # TODO: Scroll through results
    embed = (
        hikari.Embed(
            color=0x2ECC71,
            title=f"{result['anilist']['title']['romaji']} episode {result['episode']}",
            url=f"https://anilist.co/anime/{result['anilist']['id']}",
            description=f"from {result['from']//60:.0f}:{result['from']%60:.0f} to {result['to']//60:.0f}:{result['to']%60:.0f}\n\nsimilarity {result['similarity']:.2%}",
        )
        .set_image(result["image"] + "&size=" + result_size)
        .set_footer(result["filename"])
    )

    # TODO: Send in same message
    await context.respond(embed=embed)
    await context.create_followup(attachment=result["video"] + "&size=" + result_size, ephemeral=True)


@component.with_client_callback(tanjun.ClientCallbackNames.STARTING)
async def starting(
    client: tanjun.Client = tanjun.inject(type=tanjun.Client),
    tokens: config.Tokens = tanjun.inject(type=config.Tokens),
):
    saucenao = pysaucenao.SauceNao(api_key=tokens.saucenao_key, min_similarity=60)
    client.set_type_dependency(pysaucenao.SauceNao, saucenao)


def parse_saucenao_source(source: pysaucenao.GenericSource) -> hikari.Embed:
    # bug with manga sources:
    if isinstance(source.author_name, list):
        source.author_name = source.author_name[0]

    embed = (
        hikari.Embed(
            title=source.title,
            url=source.url,
        )
        .set_author(name=source.author_name, url=source.author_url)
        .set_image(source.thumbnail)
        .set_footer(
            f"similarity: {source.similarity}",
            # TODO: Better image
            icon="http://www.userlogos.org/files/logos/zoinzberg/SauceNAO.png",
        )
    )

    fields: dict[str, typing.Union[str, list[str], None]] = {}

    if isinstance(source, pysaucenao.PixivSource):
        embed.set_author(
            name=source.author_name,
            url=source.author_url,
            icon="https://www.pixiv.net/favicon.ico",
        )
    if isinstance(source, pysaucenao.BooruSource):
        embed.set_author(
            name=source.author_name,
            url=source.author_url,
            icon="https://danbooru.donmai.us/favicon.svg",
        )

        fields |= {
            "Characters": source.characters,
            "Material": source.material,
            "Boards": ", ".join(
                f"[{name}]({url})"
                for name in ("danbooru", "yande.re", "gelbooru")
                for url in source.urls or []
                if name in url
            ),
        }

    if isinstance(source, pysaucenao.containers.TwitterSource):
        embed.set_author(
            name=source.author_name,
            url=source.author_url,
            icon=f"https://unavatar.io/twitter/{source.twitter_user_handle}",
        )
        embed.title = "Twitter status"

    if isinstance(source, pysaucenao.VideoSource):
        fields |= {
            "Episode": source.episode,
            "Timestamp": source.timestamp,
            "Release Year": source.year,
        }
    if isinstance(source, pysaucenao.AnimeSource):
        embed.url = source.anilist_url or source.mal_url or source.anidb_url
        if source._ids is not None:
            fields |= {
                "Databases": ", ".join(
                    f"[{name}]({url})"
                    for name, url in [
                        ("Anilist", source.anilist_url),
                        ("MAL", source.mal_url),
                        ("AniDB", source.anidb_url),
                        ("Kitsu", source.kitsu_url),
                    ]
                    if url
                )
            }
    if isinstance(source, pysaucenao.MangaSource):
        fields |= {"Chapter": source.chapter}

    embed.description = "\n".join(
        f"{field}: {', '.join(value) if isinstance(value, list) else str(value)}"
        for field, value in fields.items()
        if value
    )

    return embed


@tanchi.as_slash_command()
async def saucenao(
    context: tanjun.context.SlashContext,
    url: typing.Optional[str] = None,
    attachment: typing.Optional[hikari.Attachment] = None,
    *,
    saucenao: pysaucenao.SauceNao = tanjun.inject(type=pysaucenao.SauceNao),
):
    """Gets the source using sauceNAO

    Args:
        url: URL link to an image.
        attachment: An image attachment.
    """
    url = check_url_or_attachment(context, url, attachment)

    try:
        result = await saucenao.from_url(url)
    except pysaucenao.SauceNaoException as e:
        raise tanjun.CommandError(e.args[0])

    if not result.results:
        context.set_ephemeral_default(True)

        await context.create_initial_response("No similar results found", ephemeral=True)
        return

    # TODO: Scroll through results
    embeds = [parse_saucenao_source(source) for source in result.results]

    await context.respond(embeds=embeds)


def find_message_attachment(message: hikari.Message) -> typing.Optional[hikari.files.Resource[typing.Any]]:
    """Find an attachment in a message"""
    if message.attachments:
        return message.attachments[0]

    for embed in message.embeds:
        if embed.thumbnail:
            return embed.thumbnail
        if embed.image:
            return embed.image

    return None


@tanjun.as_message_menu("SauceNAO")
async def saucenao_menu(
    context: tanjun.context.SlashContext,
    message: hikari.Message,
    *,
    saucenao: pysaucenao.SauceNao = tanjun.inject(type=pysaucenao.SauceNao),
):
    attachment = find_message_attachment(message)

    if attachment is None:
        raise tanjun.CommandError("No image found")

    try:
        result = await saucenao.from_url(attachment.url)
    except pysaucenao.SauceNaoException as e:
        raise tanjun.CommandError(e.args[0])

    if not result.results:
        await context.respond("No similar results found")
        return

    # TODO: Scroll through results
    embeds = [parse_saucenao_source(source) for source in result.results]

    await context.respond(embeds=embeds)


component.load_from_scope()
loader = component.make_loader()
