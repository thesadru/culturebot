import fastapi

from . import mihoyo, oauth

__all__ = ["api_router"]


api_router = fastapi.APIRouter(prefix="/api")
api_router.include_router(mihoyo.router)
api_router.include_router(oauth.router)
