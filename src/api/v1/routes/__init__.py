"""
Rotas v1 da API.
"""

from fastapi import APIRouter

from src.api.v1.routes.auth import router as auth_router
from src.api.v1.routes.consulta import router as consulta_router
from src.api.v1.routes.sigef import router as sigef_router

router = APIRouter(prefix="/v1")  # Nginx remove /api, então recebemos /v1/...

# Inclui rotas
router.include_router(auth_router)
router.include_router(sigef_router)
router.include_router(consulta_router)


@router.get("/", tags=["Info"])
async def api_info():
    """Informações da API v1."""
    return {
        "version": "1.0.0",
        "endpoints": {
            "auth": "/v1/auth",
            "sigef": "/v1/sigef",
            "consulta": "/v1/consultar",
        },
    }
