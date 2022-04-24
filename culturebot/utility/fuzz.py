import sys
import typing

import thefuzz.fuzz
import thefuzz.process
import thefuzz.utils

__all__ = ["extract", "extract_mapping"]

T = typing.TypeVar("T")


class ReversedMapping(dict[str, typing.Any]):
    """Mapping for thefuzz because it wants values as keys."""

    def items(self) -> typing.Any:
        return [(value, key) for key, value in super().items()]


def extract_with_scores(
    query: str,
    choices: typing.Collection[str],
    limit: typing.Optional[int] = None,
    *,
    cutoff: float = 0.2,
    processor: typing.Callable[[str], str] = thefuzz.utils.full_process,  # type: ignore[reportUnknownMemberType]
    scorer: typing.Callable[[str, str], int] = thefuzz.fuzz.WRatio,  # type: ignore[reportUnknownMemberType]
) -> list[tuple[int, str, typing.Any]]:
    """Extract the best matches in an iterable.

    Returns a list of (score, matched choice, choice value)
    """
    if 0 < cutoff < 1:
        cutoff *= 100

    if isinstance(choices, typing.Mapping):
        choices = ReversedMapping(typing.cast("typing.Mapping[str, typing.Any]", choices))

    extracted: typing.Sequence[typing.Any] = thefuzz.process.extractBests(  # type: ignore[reportUnknownMemberType]
        query,
        choices,
        limit=limit or sys.maxsize,
        score_cutoff=round(cutoff),
        scorer=typing.cast("typing.Callable[..., int]", scorer),
        processor=typing.cast("typing.Callable[..., str]", processor),
    )

    proper: list[tuple[int, str, str]] = []
    for found in extracted:
        if len(found) == 2:
            proper.append((found[1], found[0], found[0]))
        else:
            proper.append((found[1], found[0], found[2]))

    return proper


@typing.overload
def extract(
    query: str,
    choices: typing.Mapping[str, T],
    limit: typing.Optional[int] = 25,
    *,
    cutoff: float = 0.2,
) -> typing.Sequence[T]:
    ...


@typing.overload
def extract(
    query: str,
    choices: typing.Sequence[str],
    limit: typing.Optional[int] = 25,
    *,
    cutoff: float = 0.2,
) -> typing.Sequence[str]:
    ...


def extract(
    query: str,
    choices: typing.Collection[str],
    limit: typing.Optional[int] = 25,
    *,
    cutoff: float = 0.2,
) -> typing.Sequence[typing.Any]:
    """Extract the best matches as a list of values."""
    extracted = extract_with_scores(query, choices, limit=limit, cutoff=cutoff)

    return [value for score, choice, value in extracted]


def extract_mapping(
    query: str,
    choices: typing.Mapping[str, T],
    limit: typing.Optional[int] = 25,
    *,
    cutoff: float = 0.2,
) -> typing.Mapping[str, T]:
    """Extract the best matches as a mapping."""
    extracted = extract_with_scores(query, choices, limit=limit, cutoff=cutoff)

    return {choice: value for score, choice, value in extracted}
