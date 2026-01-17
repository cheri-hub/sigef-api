"""
Gov-Auth Enterprise API
Configurações por ambiente
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Base path calculado uma vez
_BASE_PATH = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Configurações da aplicação com validação via Pydantic."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Gov-Auth API"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    
    # API
    api_prefix: str = "/api/v1"
    api_key: str = "dev-api-key-change-in-production"
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 4
    
    # Security
    secret_key: str = "change-this-secret-key-in-production"
    access_token_expire_minutes: int = 60
    
    # Gov.br
    govbr_login_url: str = "https://sso.acesso.gov.br"
    govbr_session_timeout_hours: int = 4
    
    # SIGEF
    sigef_base_url: str = "https://sigef.incra.gov.br"
    sigef_session_timeout_hours: int = 4
    
    # WFS (Web Feature Service)
    wfs_incra_base_url: str = "https://acervofundiario.incra.gov.br/i3geo/ogc.php"
    wfs_geoone_base_url: str = "https://geoonecloud.com/geoserver/GeoINCRA/wfs"
    wfs_request_timeout: int = 60
    wfs_max_features: int = 10000
    
    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"
    
    # Browser
    browser_headless: bool = False
    browser_timeout_ms: int = 30000
    
    @property
    def base_path(self) -> Path:
        """Caminho base do projeto."""
        return _BASE_PATH
    
    @property
    def data_path(self) -> Path:
        """Diretório de dados."""
        return self.base_path / "data"
    
    @property
    def sessions_path(self) -> Path:
        """Diretório de sessões."""
        return self.data_path / "sessions"
    
    @property
    def downloads_path(self) -> Path:
        """Diretório de downloads."""
        return self.data_path / "downloads"
    
    @property
    def logs_path(self) -> Path:
        """Diretório de logs."""
        return self.base_path / "logs"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    # Aliases para compatibilidade
    @property
    def data_dir(self) -> Path:
        return self.data_path
    
    @property
    def sessions_dir(self) -> Path:
        return self.sessions_path
    
    @property
    def downloads_dir(self) -> Path:
        return self.downloads_path
    
    @property
    def logs_dir(self) -> Path:
        return self.logs_path
    
    @property
    def cors_origins(self) -> list[str]:
        """Retorna lista de origens CORS."""
        if self.is_production:
            # Em produção, lê de variável de ambiente
            origins_str = os.environ.get("CORS_ORIGINS", "")
            if origins_str:
                return [origin.strip() for origin in origins_str.split(",")]
            return ["https://govauth.cherihub.cloud", "https://cherihub.cloud"]
        return ["http://localhost:3000", "http://localhost:8080"]


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


# ============== Mapeamentos WFS ==============

# Mapeamento de camadas WFS
LAYER_MAPPING = {
    "sigef_particular": {
        "name": "Imóveis Certificados SIGEF - Particular",
        "incra_layer": "ms:certificada_sigef_particular_{uf}",
        "geoone_layer": "GeoINCRA:certificado_sigef_privado",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=certificada_sigef_particular_{uf}"
    },
    "sigef_publico": {
        "name": "Imóveis Certificados SIGEF - Público",
        "incra_layer": "ms:certificada_sigef_publico_{uf}",
        "geoone_layer": "GeoINCRA:certificado_sigef_publico",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=certificada_sigef_publico_{uf}"
    },
    "snci_privado": {
        "name": "SNCI Privado",
        "incra_layer": "ms:snci_privado_{uf}",
        "geoone_layer": "GeoINCRA:snci_privado",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=snci_privado_{uf}"
    },
    "snci_publico": {
        "name": "SNCI Público",
        "incra_layer": "ms:snci_publico_{uf}",
        "geoone_layer": "GeoINCRA:snci_publico",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=snci_publico_{uf}"
    },
    "assentamentos": {
        "name": "Assentamentos",
        "incra_layer": "ms:assentamentos_{uf}",
        "geoone_layer": "GeoINCRA:assentamentos",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=assentamentos_{uf}"
    },
    "quilombolas": {
        "name": "Quilombolas",
        "incra_layer": "ms:quilombolas_{uf}",
        "geoone_layer": "GeoINCRA:quilombolas",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=quilombolas_{uf}"
    },
    "pendentes_titulacao": {
        "name": "Pendentes de Titulação",
        "incra_layer": "ms:pendentes_titulacao_{uf}",
        "geoone_layer": "GeoINCRA:pendentes_titulacao",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=pendentes_titulacao_{uf}"
    }
}

# Mapeamento de UFs com bounding box aproximado
UF_MAPPING = {
    "AC": {"name": "Acre", "bbox": [-73.98, -11.15, -66.64, -7.07]},
    "AL": {"name": "Alagoas", "bbox": [-38.23, -10.49, -35.15, -8.82]},
    "AP": {"name": "Amapá", "bbox": [-54.88, 4.45, -49.85, -0.04]},
    "AM": {"name": "Amazonas", "bbox": [-73.79, -9.82, -56.08, 2.24]},
    "BA": {"name": "Bahia", "bbox": [-46.62, -18.35, -37.34, -8.54]},
    "CE": {"name": "Ceará", "bbox": [-41.42, -7.87, -37.24, -2.79]},
    "DF": {"name": "Distrito Federal", "bbox": [-48.28, -16.04, -47.31, -15.50]},
    "ES": {"name": "Espírito Santo", "bbox": [-41.88, -21.30, -39.67, -17.89]},
    "GO": {"name": "Goiás", "bbox": [-53.24, -19.48, -45.91, -12.39]},
    "MA": {"name": "Maranhão", "bbox": [-48.61, -10.27, -41.84, -1.02]},
    "MT": {"name": "Mato Grosso", "bbox": [-61.63, -18.04, -50.22, -7.35]},
    "MS": {"name": "Mato Grosso do Sul", "bbox": [-58.16, -24.07, -50.93, -17.16]},
    "MG": {"name": "Minas Gerais", "bbox": [-51.05, -22.92, -39.86, -14.24]},
    "PA": {"name": "Pará", "bbox": [-58.88, -9.82, -46.04, 2.61]},
    "PB": {"name": "Paraíba", "bbox": [-38.79, -8.20, -34.79, -6.02]},
    "PR": {"name": "Paraná", "bbox": [-54.62, -26.72, -48.02, -22.51]},
    "PE": {"name": "Pernambuco", "bbox": [-41.35, -9.48, -34.80, -7.16]},
    "PI": {"name": "Piauí", "bbox": [-45.98, -10.91, -40.38, -2.74]},
    "RJ": {"name": "Rio de Janeiro", "bbox": [-44.89, -23.37, -40.96, -20.76]},
    "RN": {"name": "Rio Grande do Norte", "bbox": [-38.60, -6.98, -34.96, -4.83]},
    "RS": {"name": "Rio Grande do Sul", "bbox": [-57.65, -33.75, -49.69, -27.08]},
    "RO": {"name": "Rondônia", "bbox": [-66.74, -13.70, -59.78, -7.97]},
    "RR": {"name": "Roraima", "bbox": [-64.82, 5.27, -58.99, 1.16]},
    "SC": {"name": "Santa Catarina", "bbox": [-53.84, -29.35, -48.30, -25.96]},
    "SP": {"name": "São Paulo", "bbox": [-53.11, -25.31, -44.19, -19.79]},
    "SE": {"name": "Sergipe", "bbox": [-38.22, -11.57, -36.42, -9.49]},
    "TO": {"name": "Tocantins", "bbox": [-50.74, -13.47, -45.70, -5.17]}
}

# URLs de download do SIGEF
SIGEF_DOWNLOAD_URLS = {
    "vertices_csv": "https://sigef.incra.gov.br/geo/exportar/vertice/csv/{parcela_codigo}/",
    "limites_shp": "https://sigef.incra.gov.br/geo/exportar/limite/shp/{parcela_codigo}/",
    "parcela_shp": "https://sigef.incra.gov.br/geo/exportar/parcela/shp/{parcela_codigo}/",
    "detalhes": "https://sigef.incra.gov.br/geo/parcela/detalhe/{parcela_codigo}/"
}
