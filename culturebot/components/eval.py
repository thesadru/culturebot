import ast
import asyncio
import contextlib
import inspect
import io
import re
import time
import traceback
import typing
from collections import abc as collections

import devtools
import hikari
import tanjun
import yuyo

from culturebot.utility import files

# THIS IS STOLEN FROM REINHARD
# PURELY FOR TESTING, NOT MEANT TO BE A FEATURE OF THE BOT

pformat = devtools.PrettyFormat(width=100, indent_step=2)


class EvaluationResult(typing.NamedTuple):
    stdout: io.StringIO
    stderr: io.StringIO

    return_value: typing.Any

    exec_time: int
    failed: bool

    @property
    def streams(self) -> typing.Dict[str, io.StringIO]:
        return {"stdout": self.stdout, "stderr": self.stderr}

    def stream_iterator(self) -> collections.Iterator[str]:
        """Iterate over the stream and yield all lines"""
        for name, stream in self.streams.items():
            if not (lines := stream.readlines(1)):
                continue

            yield f"- /dev/{name}:"
            yield from (line[:-1] for line in lines)

            while lines := stream.readlines(25):
                yield from (line[:-1] for line in lines)

        if self.return_value is not None:
            yield f"- return value:"
            yield from pformat(self.return_value).split("\n")


async def eval_python_code(
    context: tanjun.abc.Context,
    code: str,
) -> EvaluationResult:
    stdout = io.StringIO()
    stderr = io.StringIO()

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        start_time = time.perf_counter()
        try:
            r = await eval_python_code_no_capture(context, "<string>", code)
            failed = False
        except Exception:
            traceback.print_exc(file=stderr)
            failed = True
            r = None
        finally:
            exec_time = round((time.perf_counter() - start_time) * 1000)

    stdout.seek(0)
    stderr.seek(0)
    return EvaluationResult(stdout, stderr, r, exec_time, failed)


async def eval_python_code_no_capture(
    context: tanjun.abc.Context,
    file_name: str,
    code: str,
) -> typing.Any:
    try:
        compiled_code = compile(code, file_name, "eval", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError:
        compiled_code = compile(code, file_name, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    globalns = {
        "asyncio": asyncio,
        "hikari": hikari,
        "tanjun": tanjun,
        "pformat": pformat,
        "pprint": lambda v, **kw: print(pformat(v), **kw),
        "debug": devtools.debug,
    }
    localns = {
        "app": context.shards,
        "bot": context.shards,
        "client": context.client,
        "context": context,
        "ctx": context,
    }

    if compiled_code.co_flags & inspect.CO_COROUTINE:
        r = await eval(compiled_code, globalns, localns)
    else:
        r = eval(compiled_code, globalns, localns)

    return r


CODE_RE = re.compile(r"(?:```\w{0,2}|`)([^`]+?)(?:```|`)", re.M)


@tanjun.as_message_command("eval", "exec")
async def eval_command(
    context: tanjun.abc.MessageContext,
) -> None:
    assert context.message.content is not None  # This shouldn't ever be the case in a command client.

    code = CODE_RE.findall(context.message.content)
    if not code:
        raise tanjun.CommandError("Expected a python code block.")

    results = await eval_python_code(context, code[0])

    for page, index in yuyo.sync_paginate_string(
        results.stream_iterator(),
        wrapper="```diff\n{}\n```",
        char_limit=1900,
        line_limit=1000,
    ):
        await context.respond(page, reply=True)


@tanjun.as_message_command("reload")
async def reload_bot(
    context: tanjun.abc.MessageContext,
    *,
    client: tanjun.Client = tanjun.inject(type=tanjun.Client),
):

    await client.reload_modules_async(*files.search_directory("culturebot/components"))

    await context.respond("Reloaded all!", reply=True)


component = tanjun.Component(name="eval").load_from_scope()
component.add_check(tanjun.checks.OwnerCheck())
loader = component.make_loader()
