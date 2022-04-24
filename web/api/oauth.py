import json
import secrets
import typing

import fastapi

import culturebot
from culturebot import sql
from ext import oauth
from web import dependencies

__all__ = ["router"]

router = fastapi.APIRouter(prefix="/oauth", tags=["oauth"])

config = dependencies.config

handlers: typing.Dict[str, oauth.OAuth2] = {}

if config.tokens.google_client_id and config.tokens.google_client_secret:
    handlers["google"] = oauth.GoogleOAuth(
        config.tokens.google_client_id,
        config.tokens.google_client_secret,
        scopes=["https://www.googleapis.com/auth/userinfo.profile"],
    )
if config.tokens.discord_client_id and config.tokens.discord_client_secret:
    handlers["discord"] = oauth.DiscordOAuth(
        config.tokens.discord_client_id,
        config.tokens.discord_client_secret,
        scopes=["identify"],
    )


@router.get("/{service}")
async def auth(service: str, request: fastapi.Request):
    return handlers[service].auth(request)


@router.get("/{service}/callback", response_model=sql.models.OAuth)
async def callback(
    service: str,
    request: fastapi.Request,
    connection: culturebot.sql.Connection = fastapi.Depends(dependencies.connection),
):
    token = await handlers[service].callback(request)
    if token is None:
        raise fastapi.HTTPException(400, request.query_params.get("error", "unknown"))

    me = await token.get_me()

    if oauth := await connection.select(sql.models.OAuth, service=service, user_id=me["id"]):
        await connection.update(
            "auth.oauth",
            dict(service=service, user_id=me["id"]),
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            scope=token.scope,
            expires=token.expires,
            token_type=token.token_type,
        )
        key = oauth.key
    else:
        key = secrets.token_urlsafe(32)
        await connection.insert(
            "auth.oauth",
            service=service,
            key=key,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            scope=token.scope,
            expires=token.expires,
            token_type=token.token_type,
            user_id=me["id"],
        )

    response = fastapi.responses.Response(json.dumps(dict(**me, token=dict(token)), default=str))
    response.set_cookie(f"{service}_key", key)
    return response


for service, handler in handlers.items():
    handler.redirect_uri = "/api" + router.url_path_for("callback", service=service)
