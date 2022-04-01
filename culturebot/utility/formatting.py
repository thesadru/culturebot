import itertools
import textwrap
import typing

__all__ = ["codeblock_wrap", "grouper", "multiline_join", "paginate_string"]

T = typing.TypeVar("T")

paginator_wrapper = textwrap.TextWrapper(
    width=2000 - 12,
    drop_whitespace=False,
    break_on_hyphens=False,
    tabsize=4,
)


def codeblock_wrap(*string: str, lang: str = "") -> str:
    """Wraps a string in codeblocks."""
    return f"```{lang}\n" + "".join(string) + "\n```"


def multiline_join(strings: list[str], sep: str = "", prefix: str = "", suffix: str = "") -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return "\n".join(prefix + sep.join(i) + suffix for i in parts)


def grouper(iterable: typing.Iterable[T], chunk_size: int) -> typing.Iterator[list[T]]:
    """Like chunkify but for any iterable"""
    it = iter(iterable)
    while chunk := list(itertools.islice(it, chunk_size)):
        yield chunk


def paginate_string(
    string: str,
    size: int = 2000,
    *,
    codeblock: typing.Optional[typing.Union[bool, str]] = None,
) -> typing.Sequence[str]:
    """Takes in a string or a list of lines and splits it into chunks."""
    if isinstance(codeblock, bool):
        codeblock = "" if codeblock else None
    if codeblock is not None:
        size -= 8 + len(codeblock)  # ```{}\n\n```

    chunks = [""]
    for i in string.split("\n"):
        i += "\n"
        if len(chunks[-1]) + len(i) < size:
            chunks[-1] += i
        elif len(i) < size:
            chunks.append(i)
        else:
            chunks.extend(
                textwrap.wrap(
                    string,
                    width=size,
                    drop_whitespace=False,
                    break_on_hyphens=False,
                    tabsize=4,
                )
            )

    if codeblock is not None:
        chunks = [codeblock_wrap(i, lang=codeblock) for i in chunks]

    return chunks
