"""
Cliente de autenticação Gov.br usando Playwright.

Implementação que usa o Chrome do sistema para acessar
certificados digitais da Windows Certificate Store.

NOTA: Usa API síncrona do Playwright executada em thread separada
para compatibilidade com uvicorn no Windows (SelectorEventLoop).
"""

import asyncio
import base64
import concurrent.futures
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from src.core.config import get_settings
from src.core.exceptions import CertificateError, GovBrError, SessionExpiredError
from src.core.logging import get_logger
from src.domain.entities import Cookie, JWTPayload, Session
from src.domain.interfaces import IGovBrAuthenticator

logger = get_logger(__name__)

# ThreadPoolExecutor global para execução do Playwright
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="playwright")


class PlaywrightGovBrAuthenticator(IGovBrAuthenticator):
    """
    Autenticador Gov.br usando Playwright com Chrome do sistema.
    
    Usa channel="chrome" para acessar o Chrome instalado no sistema,
    que tem acesso à Windows Certificate Store para certificados A1.
    
    NOTA: Executa Playwright em thread separada para evitar problemas
    com event loop no Windows.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.timeout = 120000  # 2 minutos para interação do usuário
    
    async def authenticate(self, headless: bool = False) -> Session:
        """
        Realiza autenticação interativa no Gov.br.
        
        O processo:
        1. Abre navegador Chrome do sistema
        2. Navega para sso.acesso.gov.br
        3. Usuário seleciona certificado digital
        4. Usuário completa autenticação
        5. Captura cookies e JWT do localStorage
        
        Args:
            headless: Não suportado para autenticação inicial
                     (requer seleção de certificado).
        
        Returns:
            Session com tokens e cookies do Gov.br.
        """
        if headless:
            logger.warning(
                "Autenticação headless não suportada para Gov.br com certificado. "
                "Abrindo navegador visível."
            )
        
        logger.info("Iniciando autenticação Gov.br")
        
        # Executa Playwright em thread separada para evitar problemas
        # com SelectorEventLoop no Windows
        loop = asyncio.get_event_loop()
        session = await loop.run_in_executor(
            _executor,
            self._authenticate_sync,
        )
        
        return session
    
    def _authenticate_sync(self) -> Session:
        """Execução síncrona da autenticação (roda em thread separada)."""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                )
                
                page = context.new_page()
                
                # Navega para Gov.br
                logger.info("Navegando para Gov.br SSO")
                page.goto(
                    self.settings.govbr_login_url,
                    wait_until="networkidle",
                    timeout=60000,
                )
                
                # Clica em "Entrar com certificado digital" se disponível
                self._select_certificate_login_sync(page)
                
                # Aguarda autenticação completa
                session = self._wait_for_auth_complete_sync(page, context)
                
                # Salva storage_state completo em arquivo para uso posterior
                # Isso é crucial para o fluxo SIGEF funcionar!
                storage_state_path = self.settings.data_dir / "govbr_storage_state.json"
                storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_state_path))
                session.storage_state_path = str(storage_state_path)
                logger.info(f"Storage state salvo em: {storage_state_path}")
                
                logger.info(
                    "Autenticação Gov.br concluída",
                    cpf=session.cpf,
                    nome=session.nome,
                )
                
                return session
                
            finally:
                browser.close()
    
    def _select_certificate_login_sync(self, page: Page) -> None:
        """Seleciona opção de login com certificado digital."""
        try:
            # Procura botão de certificado digital
            cert_button = page.locator(
                "text=Certificado digital, "
                "text=Certificado Digital, "
                "text=certificado em nuvem"
            ).first
            
            if cert_button.is_visible(timeout=5000):
                cert_button.click()
                logger.info("Selecionada opção de certificado digital")
                page.wait_for_load_state("networkidle")
        except Exception:
            # Pode já estar na página de certificado
            logger.debug("Botão de certificado não encontrado (pode já estar na página)")
    
    def _wait_for_auth_complete_sync(
        self,
        page: Page,
        context: BrowserContext,
    ) -> Session:
        """
        Aguarda conclusão da autenticação e captura sessão.
        
        Detecta autenticação completa verificando:
        1. Redirecionamento para página logada
        2. Presença de dados no localStorage
        """
        logger.info(
            "Aguardando autenticação... "
            "Por favor, selecione o certificado e complete o login."
        )
        
        # Aguarda URL indicar login completo ou dados no localStorage
        max_wait = 180  # 3 minutos
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait:
            # Verifica localStorage
            local_storage = page.evaluate("""
                () => {
                    const items = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        items[key] = localStorage.getItem(key);
                    }
                    return items;
                }
            """)
            
            # Procura JWT no localStorage
            jwt_data = self._extract_jwt_from_storage(local_storage)
            
            if jwt_data:
                # Autenticação completa!
                cookies = context.cookies()
                return self._create_session(cookies, local_storage, jwt_data)
            
            # Aguarda um pouco antes de verificar novamente
            page.wait_for_timeout(2000)
        
        raise GovBrError(
            "Timeout aguardando autenticação. "
            "Por favor, complete o login dentro do tempo limite."
        )
    
    def _extract_jwt_from_storage(self, local_storage: dict[str, str]) -> dict | None:
        """Extrai e decodifica JWT do localStorage."""
        for key, value in local_storage.items():
            if not value:
                continue
                
            # Tenta encontrar JWT (começa com eyJ)
            if value.startswith("eyJ"):
                return self._decode_jwt(value)
            
            # Tenta parsear como JSON e procurar tokens dentro
            try:
                data = json.loads(value)
                if isinstance(data, dict):
                    for field in ["access_token", "id_token", "token"]:
                        if field in data and str(data[field]).startswith("eyJ"):
                            jwt_data = self._decode_jwt(data[field])
                            if jwt_data:
                                # Adiciona tokens brutos
                                jwt_data["access_token"] = data.get("access_token")
                                jwt_data["id_token"] = data.get("id_token")
                                return jwt_data
            except (json.JSONDecodeError, TypeError):
                continue
        
        return None
    
    def _decode_jwt(self, token: str) -> dict | None:
        """Decodifica payload de um JWT (sem verificação de assinatura)."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            # Decodifica payload (segunda parte)
            payload = parts[1]
            # Adiciona padding se necessário
            payload += "=" * (4 - len(payload) % 4)
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None
    
    def _create_session(
        self,
        cookies: list[dict],
        local_storage: dict[str, str],
        jwt_data: dict,
    ) -> Session:
        """Cria objeto Session a partir dos dados capturados."""
        session = Session(
            session_id=str(uuid.uuid4()),
            cpf=jwt_data.get("sub", jwt_data.get("cpf")),
            nome=jwt_data.get("name", jwt_data.get("nome")),
            jwt_payload=JWTPayload(
                cpf=jwt_data.get("sub", jwt_data.get("cpf", "")),
                nome=jwt_data.get("name", jwt_data.get("nome", "")),
                email=jwt_data.get("email"),
                access_token=jwt_data.get("access_token"),
                id_token=jwt_data.get("id_token"),
                cnpjs=jwt_data.get("cnpjs", []),
                nivel_acesso=jwt_data.get("amr", [""])[0] if jwt_data.get("amr") else "bronze",
                raw=jwt_data,
            ),
            govbr_cookies=[
                Cookie(
                    name=c["name"],
                    value=c["value"],
                    domain=c["domain"],
                    path=c.get("path", "/"),
                    expires=c.get("expires"),
                    http_only=c.get("httpOnly", False),
                    secure=c.get("secure", False),
                    same_site=c.get("sameSite", "Lax"),
                )
                for c in cookies
            ],
            local_storage=local_storage,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=12),  # Sessão válida por 12h
            is_govbr_authenticated=True,
        )
        
        return session
    
    async def validate_session(self, session: Session) -> bool:
        """
        Valida se uma sessão ainda está ativa.
        
        Faz uma requisição leve para verificar se os cookies
        ainda são aceitos pelo Gov.br.
        """
        if session.is_expired():
            return False
        
        if not session.is_govbr_authenticated:
            return False
        
        # TODO: Implementar validação real via requisição HTTP
        # Por ora, confia na data de expiração
        return True
    
    async def refresh_session(self, session: Session) -> Session:
        """
        Tenta renovar uma sessão existente.
        
        Para Gov.br com certificado, geralmente requer
        nova autenticação interativa.
        """
        if not session.is_expired():
            session.touch()
            return session
        
        raise SessionExpiredError(
            "Sessão expirada. Nova autenticação com certificado é necessária."
        )
