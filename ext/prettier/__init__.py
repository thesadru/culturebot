"""Prettier print that runs on devtools."""
import typing

import devtools

__all__ = ["debug", "Debug", "PrettyFormat", "pformat", "pprint"]


class Debug(devtools.Debug):
    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return super().__call__(*args, **kwargs)


class PrettyFormat(devtools.PrettyFormat):
    def __init__(
        self,
        indent_step: int = 4,
        indent_char: str = " ",
        repr_strings: bool = False,
        simple_cutoff: int = 10,
        width: int = 120,
        yield_from_generators: bool = True,
    ) -> None:
        super().__init__(
            indent_step=indent_step,
            indent_char=indent_char,
            repr_strings=repr_strings,
            simple_cutoff=simple_cutoff,
            width=width,
            yield_from_generators=yield_from_generators,
        )

    def __call__(
        self,
        value: typing.Any,
        *,
        indent: int = 0,
        indent_first: bool = False,
        highlight: bool = False,
    ) -> str:
        return super().__call__(value, indent=indent, indent_first=indent_first, highlight=highlight)

    def pprint(
        self,
        value: typing.Any,
        *,
        file: typing.Optional[str] = None,
        indent: int = 0,
        indent_first: bool = False,
        highlight: bool = False,
    ) -> str:
        print(self(value, indent=indent, indent_first=indent_first, highlight=highlight), file=file, flush=flush)


pformat = PrettyFormat()
pprint = pformat.pprint
debug = Debug()
