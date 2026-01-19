"""
Entidade de Sessão - representa uma sessão autenticada.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Cookie:
    """Representa um cookie HTTP."""
    
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário compatível com requests/httpx."""
        return {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
        }


@dataclass
class JWTPayload:
    """Payload decodificado do JWT do Gov.br."""
    
    cpf: str
    nome: str
    email: str | None = None
    access_token: str | None = None
    id_token: str | None = None
    cnpjs: list[str] = field(default_factory=list)
    nivel_acesso: str = "bronze"  # bronze, prata, ouro
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """
    Representa uma sessão autenticada no Gov.br e/ou SIGEF.
    
    Seguindo o princípio de Single Responsibility, esta classe
    apenas armazena dados da sessão, sem lógica de negócio.
    """
    
    # Identificação
    session_id: str
    
    # Dados do usuário (do JWT)
    cpf: str | None = None
    nome: str | None = None
    jwt_payload: JWTPayload | None = None
    
    # Cookies das plataformas
    govbr_cookies: list[Cookie] = field(default_factory=list)
    sigef_cookies: list[Cookie] = field(default_factory=list)
    sicar_cookies: list[Cookie] = field(default_factory=list)  # Futuro: SICAR
    
    # LocalStorage (contém o JWT)
    local_storage: dict[str, str] = field(default_factory=dict)
    
    # Caminho do storage_state do Playwright (cookies + localStorage completo)
    storage_state_path: str | None = None
    
    # Metadados
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    
    # Estado de autenticação por plataforma
    is_govbr_authenticated: bool = False
    is_sigef_authenticated: bool = False
    is_sicar_authenticated: bool = False  # Futuro: SICAR
    
    def is_expired(self) -> bool:
        """Verifica se a sessão expirou."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Verifica se a sessão é válida para uso."""
        return self.is_govbr_authenticated and not self.is_expired()
    
    def get_cookies_dict(self, platform: str = "all") -> dict[str, str]:
        """
        Retorna cookies como dicionário nome: valor.
        
        Args:
            platform: "govbr", "sigef", "sicar" ou "all"
        """
        cookies: dict[str, str] = {}
        
        if platform in ("govbr", "all"):
            for c in self.govbr_cookies:
                cookies[c.name] = c.value
                
        if platform in ("sigef", "all"):
            for c in self.sigef_cookies:
                cookies[c.name] = c.value
        
        if platform in ("sicar", "all"):
            for c in self.sicar_cookies:
                cookies[c.name] = c.value
                
        return cookies
    
    def touch(self) -> None:
        """Atualiza timestamp de último uso."""
        self.last_used_at = datetime.now()
