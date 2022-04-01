import typing

import fastapi

import culturebot
from web.utility import oauth

__all__ = ["router"]

router = fastapi.APIRouter(prefix="/oauth", include_in_schema=False)

config = culturebot.load_config()

handlers: typing.Dict[str, oauth.OAuth2[typing.Any]] = {}

if config.tokens.google_client_id and config.tokens.google_client_secret:
    handlers["google"] = oauth.GoogleOAuth(
        config.tokens.google_client_id,
        config.tokens.google_client_secret,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/drive.file"],
    )
if config.tokens.discord_client_id and config.tokens.discord_client_secret:
    handlers["discord"] = oauth.DiscordOAuth(
        config.tokens.discord_client_id,
        config.tokens.discord_client_secret,
        scopes=["identify"],
    )

engine = culturebot.sql.create_engine(config.tokens.postgres, future=True)


async def sessionmaker():
    async with culturebot.create_session(engine) as session:
        yield session


@router.get("/{service}")
async def auth(service: str, request: fastapi.Request):
    return handlers[service].auth(request)


@router.get("/{service}/callback")
async def callback(
    service: str,
    request: fastapi.Request,
    session: culturebot.sql.AsyncSession = fastapi.Depends(sessionmaker),
):
    model = await handlers[service].callback(request)
    if model is None:
        raise fastapi.HTTPException(400, request.query_params.get("error", "unknown"))

    await session.merge(model)

    return model


for service, handler in handlers.items():
    handler.redirect_uri = "/api" + router.url_path_for("callback", service=service)
