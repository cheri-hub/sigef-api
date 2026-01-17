"""
Schemas Pydantic para validação de requests/responses da API.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class TipoExportacaoEnum(str, Enum):
    """Tipos de exportação disponíveis."""
    
    PARCELA = "parcela"
    VERTICE = "vertice"
    LIMITE = "limite"


class LayerType(str, Enum):
    """Tipos de camadas WFS disponíveis."""
    
    SIGEF_PARTICULAR = "sigef_particular"
    SIGEF_PUBLICO = "sigef_publico"
    SNCI_PRIVADO = "snci_privado"
    SNCI_PUBLICO = "snci_publico"
    ASSENTAMENTOS = "assentamentos"
    QUILOMBOLAS = "quilombolas"
    PENDENTES_TITULACAO = "pendentes_titulacao"


class ServerType(str, Enum):
    """Tipos de servidores WFS disponíveis."""
    
    INCRA = "incra"
    GEOONE = "geoone"
    AUTO = "auto"


# ============== Auth Schemas ==============

class SessionInfoResponse(BaseModel):
    """Informações da sessão atual."""
    
    session_id: str
    cpf: str | None
    nome: str | None
    is_valid: bool
    is_govbr_authenticated: bool
    is_sigef_authenticated: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class AuthStatusResponse(BaseModel):
    """Status de autenticação."""
    
    authenticated: bool
    session: SessionInfoResponse | None = None
    message: str


class LoginResponse(BaseModel):
    """Resposta de login."""
    
    success: bool
    message: str
    session: SessionInfoResponse | None = None


class BrowserLoginResponse(BaseModel):
    """Resposta de login via navegador do cliente."""
    
    auth_token: str
    session_id: str
    login_url: str  # URL que o cliente deve abrir no navegador


class BrowserCallbackRequest(BaseModel):
    """Request para retornar dados da autenticação via navegador."""
    
    auth_token: str
    govbr_cookies: list[dict]  # Cookies capturados no navegador
    sigef_cookies: list[dict] | None = None
    jwt_payload: dict | None = None


# ============== SIGEF Schemas ==============

class ParcelaInfoResponse(BaseModel):
    """Informações de uma parcela."""
    
    codigo: str
    denominacao: str | None = None
    area_ha: float | None = None
    perimetro_m: float | None = None
    municipio: str | None = None
    uf: str | None = None
    situacao: str | None = None
    url: str


class ParcelaDetalhesResponse(BaseModel):
    """Detalhes completos de uma parcela extraídos da página HTML."""
    
    codigo: str
    url: str
    informacoes_parcela: dict
    historico: dict
    area_georreferenciada: dict
    detentores: list[dict]
    registro: dict


class DownloadRequest(BaseModel):
    """Request para download de CSV."""
    
    codigo: str = Field(
        ...,
        description="Código SIGEF da parcela (UUID)",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    tipo: TipoExportacaoEnum = Field(
        ...,
        description="Tipo de exportação",
    )
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        """Valida formato do código."""
        import re
        
        v = v.strip().lower()
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        
        if not re.match(pattern, v):
            raise ValueError("Código de parcela inválido. Deve ser um UUID.")
        
        return v


class DownloadAllRequest(BaseModel):
    """Request para download de todos os CSVs."""
    
    codigo: str = Field(
        ...,
        description="Código SIGEF da parcela (UUID)",
    )
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        """Valida formato do código."""
        import re
        
        v = v.strip().lower()
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        
        if not re.match(pattern, v):
            raise ValueError("Código de parcela inválido. Deve ser um UUID.")
        
        return v


class BatchDownloadRequest(BaseModel):
    """Request para download em lote."""
    
    codigos: list[str] = Field(
        ...,
        description="Lista de códigos SIGEF",
        min_length=1,
        max_length=100,
    )
    tipos: list[TipoExportacaoEnum] | None = Field(
        default=None,
        description="Tipos a baixar (default: todos)",
    )


class DownloadResponse(BaseModel):
    """Resposta de download."""
    
    success: bool
    message: str
    arquivo: str | None = None
    tamanho_bytes: int | None = None


class DownloadAllResponse(BaseModel):
    """Resposta de download de todos os CSVs."""
    
    success: bool
    message: str
    arquivos: dict[str, str] = Field(
        default_factory=dict,
        description="Mapeamento tipo -> caminho do arquivo",
    )


class BatchDownloadResponse(BaseModel):
    """Resposta de download em lote."""
    
    success: bool
    message: str
    total: int
    sucesso: int
    falhas: int
    resultados: dict[str, dict[str, str]]


# ============== Health Schemas ==============

class HealthResponse(BaseModel):
    """Resposta de health check."""
    
    status: str
    version: str
    environment: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Resposta de erro padrão."""
    
    error: str
    detail: str | None = None
    code: str | None = None


# ============== Consulta WFS Schemas ==============

class BoundingBox(BaseModel):
    """Retângulo de coordenadas geográficas WGS84."""
    
    x_min: float = Field(..., ge=-180, le=180, description="Longitude mínima (Oeste)")
    y_min: float = Field(..., ge=-90, le=90, description="Latitude mínima (Sul)")
    x_max: float = Field(..., ge=-180, le=180, description="Longitude máxima (Leste)")
    y_max: float = Field(..., ge=-90, le=90, description="Latitude máxima (Norte)")
    
    @field_validator("x_max")
    @classmethod
    def validate_x_max(cls, v: float, info) -> float:
        """Valida que x_max > x_min."""
        if "x_min" in info.data and v <= info.data["x_min"]:
            raise ValueError("x_max deve ser maior que x_min")
        return v
    
    @field_validator("y_max")
    @classmethod
    def validate_y_max(cls, v: float, info) -> float:
        """Valida que y_max > y_min."""
        if "y_min" in info.data and v <= info.data["y_min"]:
            raise ValueError("y_max deve ser maior que y_min")
        return v
    
    def to_wfs_bbox(self) -> str:
        """Converte para formato WFS: 'x_min,y_min,x_max,y_max'."""
        return f"{self.x_min},{self.y_min},{self.x_max},{self.y_max}"


class ConsultaRequest(BaseModel):
    """Requisição de consulta de imóveis."""
    
    bbox: BoundingBox
    camada: LayerType = Field(default=LayerType.SIGEF_PARTICULAR)
    servidor: ServerType = Field(default=ServerType.AUTO)
    limite: int = Field(default=1000, ge=1, le=10000, description="Limite de resultados")


class DownloadLinks(BaseModel):
    """Links de download para uma parcela."""
    
    vertices_csv: str
    limites_shp: str
    parcela_shp: str
    detalhes: str


class ImovelResponse(BaseModel):
    """Representa um imóvel encontrado."""
    
    id: str
    parcela_codigo: str
    denominacao: str | None = None
    municipio: str | None = None
    uf: str | None = None
    area_ha: float | None = None
    situacao: str | None = None
    data_certificacao: str | None = None
    geometry: dict = Field(..., description="GeoJSON Geometry")
    download_links: DownloadLinks | None = None
    propriedades: dict = Field(default_factory=dict, description="Todas propriedades originais")


class ConsultaResponse(BaseModel):
    """Resposta da consulta - É um GeoJSON FeatureCollection."""
    
    sucesso: bool
    mensagem: str
    total: int
    servidor_utilizado: str
    camada: str
    bbox_consultado: BoundingBox
    tempo_resposta_ms: float
    imoveis: list[ImovelResponse]
    
    # GeoJSON FeatureCollection
    type: str = Field(default="FeatureCollection")
    features: list[dict] = Field(default_factory=list)
