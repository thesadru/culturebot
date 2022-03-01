from aiohttp import web
from . import dependencies
from . import oauth
import culturebot


app = web.Application()
app["client"] = dependencies.client

# oauth:

config = culturebot.load_config()

assert config.tokens.google_client_id and config.tokens.google_client_secret
assert config.tokens.github_client_id and config.tokens.github_client_secret

oauth_app = web.Application()

google = oauth.GoogleOauth(
    config.tokens.google_client_id,
    config.tokens.google_client_secret,
    scopes=["https://www.googleapis.com/auth/drive.file"],
)
github = oauth.GithubOauth(
    config.tokens.github_client_id,
    config.tokens.github_client_secret,
)
oauth_app.add_routes([google])


app.add_subapp("/oauth", oauth_app)
web.run_app(app, port=5000)
