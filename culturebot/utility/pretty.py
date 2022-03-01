__all__ = ["human_size"]


def human_size(size: float, decimal_places: int = 2) -> str:
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    else:
        unit = "TiB"

    return f"{size:.{decimal_places}f} {unit}"
