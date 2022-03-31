from aiohttp import web

import culturebot

from . import dependencies, oauth

app = web.Application()
app["client"] = dependencies.client

# =================

config = culturebot.load_config()

assert config.tokens.google_client_id and config.tokens.google_client_secret
assert config.tokens.github_client_id and config.tokens.github_client_secret

oauth_app = web.Application()

session = culturebot.create_session(config.tokens.postgres)
dependencies.client.set_type_dependency(type(session), session)

google = oauth.GoogleOauth(
    config.tokens.google_client_id,
    config.tokens.google_client_secret,
    scopes=["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/userinfo.profile"],
)
github = oauth.GithubOauth(
    config.tokens.github_client_id,
    config.tokens.github_client_secret,
)
oauth_app.add_routes([google, github])


app.add_subapp("/oauth", oauth_app)

if __name__ == "__main__":
    web.run_app(app, port=5000)
