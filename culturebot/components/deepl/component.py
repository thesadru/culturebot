import aiohttp
import tanchi
import tanjun

from culturebot import config
from culturebot.utility import fuzz

from .deepl import DeepL

component = tanjun.Component(name="deepl")


@component.with_client_callback(tanjun.ClientCallbackNames.STARTED)
async def starting(
    client: tanjun.Client = tanjun.inject(type=tanjun.Client),
    tokens: config.Tokens = tanjun.inject(type=config.Tokens),
    session: aiohttp.ClientSession = tanjun.inject(type=aiohttp.ClientSession),
):
    if tokens.deepl_key is None:
        return

    client.set_type_dependency(DeepL, DeepL(tokens.deepl_key, session=session))


@tanchi.as_slash_command()
async def translate(
    context: tanjun.abc.SlashContext,
    text: str,
    target_language: str,
    formal: bool = False,
    *,
    deepl: DeepL = tanjun.inject(type=DeepL),
):
    """Translate text."""
    await context.create_initial_response("disabled", ephemeral=True)

    text = await deepl.translate(text, target_lang=target_language, formal=formal)
    await context.respond(text)


@translate.with_str_autocomplete("target_language")
async def autocomplete_target_lang(
    context: tanjun.abc.AutocompleteContext,
    lang: str,
    *,
    deepl: DeepL = tanjun.inject(type=DeepL),
) -> None:
    languages = {l.name: l.language for l in await deepl.get_languages(target=True)}
    resolved = fuzz.extract_mapping(lang, languages)

    if len(resolved) == 0:
        languages = sorted(languages.items())[:25]
        await context.set_choices(languages)
        return

    await context.set_choices(resolved)


# component.load_from_scope()
loader = component.make_loader()
