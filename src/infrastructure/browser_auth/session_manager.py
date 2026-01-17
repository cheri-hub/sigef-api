"""
Gerenciador de sessões para autenticação remota via browser.

Este módulo permite que a autenticação aconteça no navegador do cliente
enquanto a API roda em Docker ou servidor remoto.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class BrowserAuthSession:
    """
    Gerencia sessões de autenticação remota.
    
    Permite que o cliente autentique via navegador e retorne os tokens
    para a API sem precisar que o servidor tenha acesso a interface gráfica.
    """
    
    def __init__(self, sessions_dir: Path | None = None):
        self.sessions_dir = sessions_dir or get_settings().data_dir / "browser_auth"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.session_timeout = 600  # 10 minutos
    
    def create_browser_session(self) -> dict[str, str]:
        """
        Cria uma nova sessão de autenticação para uso no navegador.
        
        Retorna um token que o cliente deve usar para retornar os cookies.
        """
        token = secrets.token_urlsafe(32)
        session_id = str(uuid.uuid4())
        
        session_data = {
            "token": token,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=self.session_timeout)).isoformat(),
            "status": "pending",  # pending, completed, expired
        }
        
        # Salva em arquivo
        session_file = self.sessions_dir / f"{token}.json"
        import json
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        
        logger.info(f"Sessão de browser criada: {session_id}")
        
        return {
            "auth_token": token,
            "session_id": session_id,
        }
    
    def get_browser_session(self, token: str) -> dict[str, Any] | None:
        """Retrieves session data for browser auth token."""
        session_file = self.sessions_dir / f"{token}.json"
        
        if not session_file.exists():
            return None
        
        import json
        with open(session_file, "r") as f:
            session_data = json.load(f)
        
        # Valida expiração
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.now() > expires_at:
            session_file.unlink()
            return None
        
        return session_data
    
    def save_browser_cookies(self, token: str, cookies_data: dict) -> bool:
        """
        Salva os cookies retornados pelo navegador do cliente.
        
        Args:
            token: Token de autenticação do browser
            cookies_data: Dicionário com govbr_cookies, sigef_cookies, etc.
        
        Returns:
            True se salvo com sucesso
        """
        session_data = self.get_browser_session(token)
        
        if not session_data:
            logger.warning(f"Token de browser inválido ou expirado: {token}")
            return False
        
        # Atualiza com os dados de cookies
        session_data["status"] = "completed"
        session_data["cookies_data"] = cookies_data
        
        # Salva de volta
        session_file = self.sessions_dir / f"{token}.json"
        import json
        with open(session_file, "w") as f:
            json.dump(session_data, f)
        
        logger.info(f"Cookies salvos para sessão: {session_data['session_id']}")
        return True
    
    def cleanup_expired(self) -> int:
        """Remove sessões expiradas. Retorna quantidade removida."""
        import json
        
        count = 0
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now() > expires_at:
                    session_file.unlink()
                    count += 1
            except Exception:
                pass
        
        if count > 0:
            logger.info(f"Limpas {count} sessões de browser expiradas")
        
        return count
