"""
Rotas da API para consulta de imóveis INCRA/SIGEF via WFS.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.api.v1.schemas import (
    BoundingBox,
    ConsultaRequest,
    ConsultaResponse,
    LayerType,
    ServerType,
)
from src.infrastructure.wfs.client import WFSService
from src.services.incra_service import IncraService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consultar", tags=["Consulta WFS"])


# Dependency para obter serviços
async def get_wfs_service() -> WFSService:
    """Dependency para obter WFSService."""
    service = WFSService()
    try:
        yield service
    finally:
        await service.close()


async def get_incra_service(
    wfs_service: Annotated[WFSService, Depends(get_wfs_service)]
) -> IncraService:
    """Dependency para obter IncraService."""
    return IncraService(wfs_service)


@router.post("", response_model=ConsultaResponse, summary="Consultar imóveis por bbox")
async def consultar_imoveis_post(
    request: ConsultaRequest,
    service: Annotated[IncraService, Depends(get_incra_service)]
) -> ConsultaResponse:
    """
    Consulta imóveis certificados dentro de um bounding box.
    
    ## Descrição
    
    Esta rota permite consultar imóveis certificados do INCRA/SIGEF dentro de uma
    área geográfica específica (bounding box).
    
    ## Parâmetros
    
    - **bbox**: Bounding box da consulta (coordenadas WGS84)
        - x_min: Longitude mínima (Oeste)
        - y_min: Latitude mínima (Sul)
        - x_max: Longitude máxima (Leste)
        - y_max: Latitude máxima (Norte)
    - **camada**: Tipo de camada (sigef_particular, sigef_publico, etc.)
    - **servidor**: Servidor WFS (incra, geoone, auto)
    - **limite**: Número máximo de resultados (1-10000)
    
    ## Exemplo de Requisição
    
    ```json
    {
        "bbox": {
            "x_min": -47.5,
            "y_min": -15.9,
            "x_max": -47.3,
            "y_max": -15.7
        },
        "camada": "sigef_particular",
        "servidor": "auto",
        "limite": 100
    }
    ```
    
    ## Resposta
    
    Retorna um GeoJSON FeatureCollection com os imóveis encontrados,
    incluindo links de download para cada imóvel.
    """
    logger.info(
        f"Consulta POST recebida: bbox={request.bbox.to_wfs_bbox()}, "
        f"camada={request.camada.value}, servidor={request.servidor.value}"
    )
    
    result = await service.consultar_imoveis(
        bbox=request.bbox,
        layer_type=request.camada,
        server_type=request.servidor,
        limite=request.limite
    )
    
    return result


@router.get("", response_model=ConsultaResponse, summary="Consultar imóveis (GET)")
async def consultar_imoveis_get(
    x_min: Annotated[float, Query(ge=-180, le=180, description="Longitude mínima")],
    y_min: Annotated[float, Query(ge=-90, le=90, description="Latitude mínima")],
    x_max: Annotated[float, Query(ge=-180, le=180, description="Longitude máxima")],
    y_max: Annotated[float, Query(ge=-90, le=90, description="Latitude máxima")],
    camada: Annotated[LayerType, Query(description="Tipo de camada")] = LayerType.SIGEF_PARTICULAR,
    servidor: Annotated[ServerType, Query(description="Servidor WFS")] = ServerType.AUTO,
    limite: Annotated[int, Query(ge=1, le=10000, description="Limite de resultados")] = 1000,
    service: IncraService = Depends(get_incra_service)
) -> ConsultaResponse:
    """
    Consulta imóveis via GET (útil para testes e integrações simples).
    
    ## Exemplo
    
    ```
    GET /api/v1/consultar?x_min=-47.5&y_min=-15.9&x_max=-47.3&y_max=-15.7&camada=sigef_particular
    ```
    """
    bbox = BoundingBox(
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max
    )
    
    logger.info(
        f"Consulta GET recebida: bbox={bbox.to_wfs_bbox()}, "
        f"camada={camada.value}, servidor={servidor.value}"
    )
    
    result = await service.consultar_imoveis(
        bbox=bbox,
        layer_type=camada,
        server_type=servidor,
        limite=limite
    )
    
    return result


@router.get(
    "/bbox/{coords}",
    response_model=ConsultaResponse,
    summary="Consultar por bbox compacto"
)
async def consultar_por_bbox_path(
    coords: str,
    camada: LayerType = Query(default=LayerType.SIGEF_PARTICULAR),
    servidor: ServerType = Query(default=ServerType.AUTO),
    limite: int = Query(default=1000, ge=1, le=10000),
    service: IncraService = Depends(get_incra_service)
) -> ConsultaResponse:
    """
    Consulta com bbox no path (formato: x_min,y_min,x_max,y_max).
    
    ## Exemplo
    
    ```
    GET /api/v1/consultar/bbox/-47.5,-15.9,-47.3,-15.7?camada=sigef_particular
    ```
    """
    try:
        parts = coords.split(",")
        if len(parts) != 4:
            raise ValueError("Bbox deve ter 4 coordenadas separadas por vírgula")
        
        bbox = BoundingBox(
            x_min=float(parts[0]),
            y_min=float(parts[1]),
            x_max=float(parts[2]),
            y_max=float(parts[3])
        )
    except (ValueError, IndexError) as e:
        return ConsultaResponse(
            sucesso=False,
            mensagem=f"Bbox inválido: {str(e)}",
            total=0,
            servidor_utilizado="erro",
            camada=camada.value,
            bbox_consultado=BoundingBox(x_min=0, y_min=0, x_max=0, y_max=0),
            tempo_resposta_ms=0,
            imoveis=[],
            features=[]
        )
    
    result = await service.consultar_imoveis(
        bbox=bbox,
        layer_type=camada,
        server_type=servidor,
        limite=limite
    )
    
    return result


@router.get("/download", summary="Download GeoJSON")
async def download_geojson(
    x_min: float = Query(..., ge=-180, le=180),
    y_min: float = Query(..., ge=-90, le=90),
    x_max: float = Query(..., ge=-180, le=180),
    y_max: float = Query(..., ge=-90, le=90),
    camada: LayerType = Query(default=LayerType.SIGEF_PARTICULAR),
    servidor: ServerType = Query(default=ServerType.AUTO),
    limite: int = Query(default=1000, ge=1, le=10000),
    service: IncraService = Depends(get_incra_service)
) -> StreamingResponse:
    """
    Retorna GeoJSON como arquivo para download.
    
    ## Exemplo
    
    ```
    GET /api/v1/consultar/download?x_min=-47.5&y_min=-15.9&x_max=-47.3&y_max=-15.7
    ```
    
    Retorna arquivo: consulta_YYYYMMDD_HHMMSS.geojson
    """
    import json
    from datetime import datetime
    from io import BytesIO
    
    bbox = BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
    
    result = await service.consultar_imoveis(
        bbox=bbox,
        layer_type=camada,
        server_type=servidor,
        limite=limite
    )
    
    # Converte para GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": result.features,
        "metadata": {
            "total": result.total,
            "camada": result.camada,
            "servidor": result.servidor_utilizado,
            "bbox": {
                "x_min": bbox.x_min,
                "y_min": bbox.y_min,
                "x_max": bbox.x_max,
                "y_max": bbox.y_max
            }
        }
    }
    
    # Cria arquivo em memória
    buffer = BytesIO()
    buffer.write(json.dumps(geojson, ensure_ascii=False, indent=2).encode("utf-8"))
    buffer.seek(0)
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"consulta_{timestamp}.geojson"
    
    return StreamingResponse(
        buffer,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
