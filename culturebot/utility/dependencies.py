import datetime
import typing

import tanjun

__all__ = ["cached_callback"]

CallableT = typing.TypeVar("CallableT", bound=typing.Callable[..., typing.Any])
Identity = typing.Callable[[CallableT], CallableT]


def cached_callback(expire_after: typing.Union[int, float, datetime.timedelta, None] = None) -> Identity[CallableT]:
    """Make an injection callback cached."""

    def wrapper(callback: CallableT) -> CallableT:
        cached = tanjun.dependencies.data.cache_callback(callback, expire_after=expire_after)
        return typing.cast("CallableT", cached)

    return wrapper
