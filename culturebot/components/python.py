import logging
import re
import shlex
import typing

import black
import black.mode
import hikari
import isort.api
import mypy.api
import tanchi
import tanjun

blib_logger = logging.getLogger("blib2to3")
blib_logger.setLevel(logging.CRITICAL)

BLOCK_RE = re.compile(r"```py\s((?:.|\n)+?)```")


def format_code(string: str, line_length: int = 88, sort_imports: bool = False) -> str:
    try:
        string = black.format_str(string, mode=black.mode.Mode(line_length=line_length))
    except ValueError as e:
        return "# Couldn't format this code block due to a syntax error\n" + string

    if sort_imports:
        string = isort.api.sort_code_string(string, line_length=line_length, profile="black")

    return string


def format_code_blocks(content: str, line_length: int = 88, sort_imports: bool = False) -> str:
    return BLOCK_RE.sub(
        lambda match: f"```py\n{format_code(match.group(1), line_length=line_length, sort_imports=sort_imports)}```",
        content,
    )


def mypy_type_check(content: str, args: typing.Sequence[str]) -> str:
    stdout, stderr, code = mypy.api.run([*args, "-c", content])
    return stdout


def mypy_type_check_code_blocks(content: str, args: typing.Optional[typing.Sequence[str]] = None) -> str:
    args = args or []

    result: typing.List[str] = []
    for codeblock in BLOCK_RE.findall(content):
        result.append("```\n" + mypy_type_check(codeblock, args) + "\n```")

    return "\n\n".join(result)


@tanchi.as_slash_command()
async def format(
    context: tanjun.abc.SlashContext,
    message: hikari.Message,
    ephemeral: bool = True,
    line_length: int = 88,
    sort_imports: bool = False,
):
    """Format all python code blocks in a message.

    Args:
        message: A link to a message to format.
        ephemeral: Whether the response should be ephemeral.
        line_length: How many characters per line to allow. [default: 88]
        sort_imports: Whether to sort imports using isort
    """
    assert message.content

    content = format_code_blocks(message.content, line_length=line_length, sort_imports=sort_imports)
    await context.create_initial_response(content, ephemeral=ephemeral)


@tanjun.as_message_menu("Format Python Code Block")
async def format_ctx(context: tanjun.abc.SlashContext, message: hikari.Message):
    assert message.content

    content = format_code_blocks(message.content)
    await context.create_initial_response(content, ephemeral=True)


@tanchi.as_slash_command()
async def type_check(
    context: tanjun.abc.SlashContext,
    message: hikari.Message,
    ephemeral: bool = True,
    strict: bool = False,
    arguments: str = "",
):
    """Type-check all python code blocks in a message.

    Args:
        message: A link to a message to type-check.
        ephemeral: Whether the response should be ephemeral.
        strict: Whether to use the --strict flag.
        arguments: Command line arguments to use with mypy.
    """
    assert message.content

    args = shlex.split(arguments)
    if strict:
        args += ["--strict"]

    content = mypy_type_check_code_blocks(message.content, args)

    await context.create_initial_response(content, ephemeral=ephemeral)


@tanjun.as_message_menu("Type-Check Python Code Block")
async def type_check_ctx(context: tanjun.abc.SlashContext, message: hikari.Message):
    assert message.content

    content = mypy_type_check_code_blocks(message.content)
    await context.respond(content)


component = tanjun.Component(name="python").load_from_scope()
loader = component.make_loader()
