from . import oauth

__all__ = ["DiscordOAuth", "GoogleOAuth"]


class DiscordOAuth(oauth.OAuth2):
    authorize_url = "https://discord.com/api/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"
    me_url = "https://discord.com/api/v10/users/@me"


class GoogleOAuth(oauth.OAuth2):
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent"
    token_url = "https://oauth2.googleapis.com/token"
    me_url = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
