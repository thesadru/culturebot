import dataclasses

__all__ = ["Swear", "SwearUser"]


@dataclasses.dataclass
class Swear:
    __tablename__ = "swears.swear"

    user_id: int
    guild_id: int

    swear: str
    amount: int


@dataclasses.dataclass
class SwearUser:
    __tablename__ = "swears.user"

    user_id: int
    guild_id: int
