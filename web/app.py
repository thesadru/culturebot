import os

import fastapi
import genshin
import starlette.staticfiles

from . import api

os.system("")  # fix windows cause idk

app = fastapi.FastAPI(openapi_url=f"/api/openapi.json")

app.include_router(api.api_router)
app.mount("/", starlette.staticfiles.StaticFiles(directory="./web/static", html=True))


app.add_exception_handler(genshin.GenshinException, api.router.mihoyo.handle_genshin_exception)
