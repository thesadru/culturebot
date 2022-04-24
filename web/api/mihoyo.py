import asyncio
import typing

import fastapi
import genshin
import pydantic

import culturebot
from web import dependencies

__all__ = ["router", "handle_genshin_exception"]

router = fastapi.APIRouter(prefix="/mihoyo", tags=["mihoyo"])


class LoginRequest(pydantic.BaseModel):
    account: str
    password: str

    mmt_key: str
    geetest: typing.Dict[str, str]


@router.get("/mmt", response_model=typing.Mapping[str, str])
async def mmt(now: int):
    return await genshin.utility.geetest.create_mmt(now)


@router.post("/login", response_model=typing.Sequence[genshin.models.GenshinAccount])
async def login(
    data: LoginRequest,
    lang: typing.Optional[str] = None,
    session: culturebot.sql.Connection = fastapi.Depends(dependencies.connection),
    oauth: typing.Mapping[str, culturebot.sql.models.OAuth] = fastapi.Depends(dependencies.get_oauth),
):
    client = genshin.Client(debug=True)
    await client.login_with_geetest(data.account, data.password, data.mmt_key, data.geetest)
    assert isinstance(client.cookie_manager, genshin.client.CookieManager)

    asyncio.create_task(
        session.insert(
            "auth.genshin",
            discord_id=int(oauth["discord"].user_id),
            hoyolab_id=client.cookie_manager.user_id,
            cookies=client.cookie_manager.header,
        )
    )

    return await client.get_game_accounts(lang=lang)


def handle_genshin_exception(request: fastapi.Request, exception: genshin.GenshinException):
    status_code = 500

    if isinstance(exception, (genshin.CookieException, genshin.DataNotPublic)):
        status_code = 403
    elif isinstance(exception, genshin.AccountNotFound):
        status_code = 404
    elif isinstance(exception, (genshin.AlreadyClaimed, genshin.AuthkeyException, genshin.RedemptionClaimed)):
        status_code = 400

    return fastapi.responses.JSONResponse(
        {
            "message": exception.msg,
            "original": exception.original,
            "retcode": exception.retcode,
            "type": exception.__class__.__name__,
        },
        status_code=status_code,
    )
