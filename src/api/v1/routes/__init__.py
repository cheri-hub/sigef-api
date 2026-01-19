"""
Rotas v1 da API - Versão Mínima.
"""

from fastapi import APIRouter

from src.api.v1.routes.auth import router as auth_router
from src.api.v1.routes.sigef import router as sigef_router

router = APIRouter(prefix="/v1")

# Inclui rotas
router.include_router(auth_router)
router.include_router(sigef_router)


@router.get("/", tags=["Info"])
async def api_info():
    """Informações da API v1."""
    return {
        "version": "1.0.0-min",
        "description": "API para integração com sistemas Gov.br",
        "platforms": {
            "sigef": {
                "name": "SIGEF - Sistema de Gestão Fundiária",
                "status": "active",
                "endpoints": "/v1/sigef",
            },
            "sicar": {
                "name": "SICAR - Sistema de Cadastro Ambiental Rural",
                "status": "planned",
                "endpoints": "/v1/sicar",
            },
        },
        "auth": "/v1/auth",
    }
