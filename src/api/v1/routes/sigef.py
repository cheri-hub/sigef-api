"""
Rotas SIGEF.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.api.v1.dependencies import get_sigef_service
from src.api.v1.schemas import (
    BatchDownloadRequest,
    BatchDownloadResponse,
    DownloadAllRequest,
    DownloadAllResponse,
    DownloadRequest,
    DownloadResponse,
    ParcelaDetalhesResponse,
    ParcelaInfoResponse,
    TipoExportacaoEnum,
)
from src.core.exceptions import (
    InvalidParcelaCodeError,
    ParcelaNotFoundError,
    SessionExpiredError,
    SigefError,
)
from src.core.logging import get_logger
from src.domain.entities import TipoExportacao
from src.services.sigef_service import SigefService

logger = get_logger(__name__)

router = APIRouter(prefix="/sigef", tags=["SIGEF"])


@router.get(
    "/parcela/{codigo}",
    response_model=ParcelaInfoResponse,
    summary="Obtém informações de uma parcela",
    description="Retorna dados básicos de uma parcela do SIGEF.",
)
async def get_parcela(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> ParcelaInfoResponse:
    """Obtém informações de uma parcela."""
    try:
        parcela = await sigef_service.get_parcela_info(codigo)
        
        return ParcelaInfoResponse(
            codigo=parcela.codigo,
            denominacao=parcela.denominacao,
            area_ha=parcela.area_ha,
            perimetro_m=parcela.perimetro_m,
            municipio=parcela.municipio,
            uf=parcela.uf,
            situacao=parcela.situacao.value if parcela.situacao else None,
            url=parcela.get_url_sigef(),
        )
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ParcelaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/download",
    response_model=DownloadResponse,
    summary="Baixa CSV de uma parcela",
    description="Faz download de um arquivo CSV (parcela, vértice ou limite).",
)
async def download_csv(
    request: DownloadRequest,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> DownloadResponse:
    """Baixa CSV de uma parcela."""
    try:
        # Converte enum da API para enum do domínio
        tipo = TipoExportacao(request.tipo.value)
        
        path = await sigef_service.download_csv(
            codigo=request.codigo,
            tipo=tipo,
        )
        
        return DownloadResponse(
            success=True,
            message=f"CSV de {request.tipo.value} baixado com sucesso",
            arquivo=str(path),
            tamanho_bytes=path.stat().st_size,
        )
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ParcelaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/download/all",
    response_model=DownloadAllResponse,
    summary="Baixa todos os CSVs de uma parcela",
    description="Faz download dos três arquivos: parcela, vértice e limite.",
)
async def download_all_csvs(
    request: DownloadAllRequest,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> DownloadAllResponse:
    """Baixa todos os CSVs de uma parcela."""
    try:
        results = await sigef_service.download_all_csvs(codigo=request.codigo)
        
        return DownloadAllResponse(
            success=True,
            message="Todos os CSVs baixados com sucesso",
            arquivos={k: str(v) for k, v in results.items()},
        )
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ParcelaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/download/batch",
    response_model=BatchDownloadResponse,
    summary="Baixa CSVs de múltiplas parcelas",
    description="Faz download em lote para várias parcelas.",
)
async def download_batch(
    request: BatchDownloadRequest,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> BatchDownloadResponse:
    """Baixa CSVs de múltiplas parcelas."""
    try:
        # Converte enums
        tipos = None
        if request.tipos:
            tipos = [TipoExportacao(t.value) for t in request.tipos]
        
        results = await sigef_service.download_batch(
            codigos=request.codigos,
            tipos=tipos,
        )
        
        # Conta sucessos e falhas
        sucesso = sum(1 for r in results.values() if "error" not in r)
        falhas = sum(1 for r in results.values() if "error" in r)
        
        return BatchDownloadResponse(
            success=falhas == 0,
            message=f"Download concluído: {sucesso} sucesso, {falhas} falhas",
            total=len(request.codigos),
            sucesso=sucesso,
            falhas=falhas,
            resultados={k: {kk: str(vv) for kk, vv in v.items()} for k, v in results.items()},
        )
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except Exception as e:
        logger.exception("Erro no download batch")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/download/{codigo}/{tipo}",
    summary="Download direto do arquivo CSV",
    description="Retorna o arquivo CSV diretamente para download.",
    response_class=FileResponse,
)
async def download_file(
    codigo: str,
    tipo: TipoExportacaoEnum,
    sigef_service: SigefService = Depends(get_sigef_service),
):
    """Retorna arquivo CSV para download direto."""
    try:
        tipo_domain = TipoExportacao(tipo.value)
        
        path = await sigef_service.download_csv(
            codigo=codigo,
            tipo=tipo_domain,
        )
        
        return FileResponse(
            path=path,
            filename=path.name,
            media_type="text/csv",
        )
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ParcelaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/memorial/{codigo}",
    summary="Download do memorial descritivo (PDF)",
    description="Retorna o memorial descritivo da parcela em formato PDF.",
    response_class=FileResponse,
)
async def download_memorial(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
):
    """Retorna memorial descritivo (PDF) para download direto."""
    try:
        path = await sigef_service.download_memorial(codigo=codigo)
        
        return FileResponse(
            path=path,
            filename=path.name,
            media_type="application/pdf",
        )
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ParcelaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/open-browser/{codigo}",
    summary="Abre página da parcela no navegador autenticado",
    description="Abre a página de detalhes da parcela usando o navegador Playwright já autenticado.",
)
async def open_browser(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> dict:
    """Abre página da parcela no navegador autenticado."""
    try:
        await sigef_service.open_parcela_browser(codigo)
        
        return {
            "success": True,
            "message": f"Página da parcela {codigo} aberta no navegador autenticado",
        }
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/detalhes/{codigo}",
    response_model=ParcelaDetalhesResponse,
    summary="Obtém detalhes completos de uma parcela",
    description="Extrai todas as informações da página HTML da parcela.",
)
async def get_detalhes(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> ParcelaDetalhesResponse:
    """Obtém detalhes completos da parcela."""
    try:
        detalhes = await sigef_service.get_parcela_detalhes(codigo)
        return ParcelaDetalhesResponse(**detalhes)
        
    except InvalidParcelaCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except SessionExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except SigefError as e:
        raise HTTPException(status_code=502, detail=str(e))
