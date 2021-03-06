import asyncio
import datetime
import random
import typing

import aiohttp
import alluka
import tanchi
import tanjun

from culturebot import config, sql
from culturebot.utility import dependencies, fuzz, pretty
from ext import oauth

from .drive import Drive, File, Folder

component = tanjun.Component(name="google")


@component.with_client_callback(tanjun.ClientCallbackNames.STARTED)
async def on_started(
    client: alluka.Injected[tanjun.Client],
    config: alluka.Injected[config.Config],
    connection: alluka.Injected[sql.Connection],
    google_service: alluka.Injected[oauth.GoogleOAuth],
    session: alluka.Injected[aiohttp.ClientSession],
):
    oauth_model = await connection.select(sql.models.OAuth, service="google", user_id=config.memebin.user)
    assert oauth_model is not None, "No google oauth token found"

    client.set_type_dependency(Drive, Drive(oauth_model.make_token(google_service), session=session))


async def gather_files_recursively(
    drive: alluka.Injected[Drive],
    parent: str,
) -> typing.List[File]:
    """Gather all files recursively."""
    files: typing.List[File] = []

    async for resource in drive.list_directory(parent, pageSize=1000):
        if isinstance(resource, File):
            files.append(resource)
        elif isinstance(resource, Folder):
            files += await gather_files_recursively(drive, resource.id)

    return files


@dependencies.cached_callback(datetime.timedelta(hours=6))
async def gather_memebin_files(
    drive: alluka.Injected[Drive],
    config: alluka.Injected[config.Config],
) -> typing.Sequence[File]:
    """Gather all files as a cached callback."""
    if config.memebin is None:
        raise ValueError("No memebin configuration found")

    return await gather_files_recursively(drive, config.memebin.file)


def filter_files(
    files: typing.Sequence[File],
    max_size: typing.Optional[int] = None,
    mimetype: typing.Optional[str] = None,
    filename: typing.Optional[str] = None,
    limit: typing.Optional[int] = None,
) -> typing.Sequence[File]:
    """Filter files by some pre-set configuration."""
    if max_size:
        files = [file for file in files if file.size <= max_size]

    if mimetype and mimetype != "any":
        files = [file for file in files if mimetype in file.mimetype]

    if filename:
        files = fuzz.extract(filename, {file.filename: file for file in files}, limit=limit)

    elif limit:
        files = random.sample(files, k=limit)

    return files


@tanchi.as_slash_command()
async def meme(
    context: tanjun.context.SlashContext,
    max_size: int = 0x600000,
    mimetype: typing.Literal["any", "video", "image"] = "any",
    filename: typing.Optional[str] = None,
    *,
    files: typing.Sequence[File] = alluka.inject(callback=gather_memebin_files),
):
    """Sends a random meme from the owner's meme folder. Might be very offensive, please don't judge me.

    Args:
        max_size: Max file size in bytes. (default = 6MiB, max = 8MiB)
        mimetype: The mimetype to filter by
        filename: A specific name of the file you want to see
    """
    files = filter_files(files, max_size=max_size, mimetype=mimetype, filename=filename, limit=1)
    if not files:
        raise tanjun.CommandError("Could not find requested file")

    file = files[0]

    await asyncio.create_task(context.respond(f"Sending `{file.filename}` ({pretty.human_size(file.size)}) ???"))

    attachment = await file.get_attachment()

    await context.edit_initial_response(content="", attachment=attachment)


@meme.with_str_autocomplete("filename")
async def autocomplete(
    context: tanjun.context.AutocompleteContext,
    filename: str,
    *,
    files: typing.Sequence[File] = alluka.inject(callback=gather_memebin_files),
):
    """Autocomplete filename by adding some metadata."""
    # TODO: Use max size and mimetype
    files = filter_files(files, max_size=0x600000, filename=filename, limit=25)

    choices = {f"{file.filename} ({pretty.human_size(file.size)})": file.filename for file in files}
    await context.set_choices(choices)


component.load_from_scope()
loader = component.make_loader()
