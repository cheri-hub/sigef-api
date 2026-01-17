"""
Serviço SIGEF.

Operações de negócio relacionadas ao SIGEF INCRA,
como download de dados de parcelas.
"""

from pathlib import Path

from src.core.exceptions import SessionExpiredError
from src.core.logging import get_logger
from src.domain.entities import Parcela, Session, TipoExportacao
from src.domain.interfaces import ISessionRepository, ISigefClient
from src.services.auth_service import AuthService

logger = get_logger(__name__)


class SigefService:
    """
    Serviço para operações SIGEF.
    
    Encapsula lógica de negócio para download de dados
    de parcelas, com gerenciamento automático de sessão.
    """
    
    def __init__(
        self,
        sigef_client: ISigefClient,
        session_repository: ISessionRepository,
        auth_service: AuthService | None = None,
    ):
        """
        Inicializa serviço.
        
        Args:
            sigef_client: Cliente SIGEF
            session_repository: Repositório de sessões
            auth_service: Serviço de autenticação (para refresh automático)
        """
        self.sigef = sigef_client
        self.sessions = session_repository
        self.auth = auth_service
    
    async def _get_valid_session(self, force_reauth: bool = False) -> Session:
        """Obtém sessão válida ou lança exceção."""
        session = await self.sessions.load_latest()
        
        if not session or not session.is_valid():
            if self.auth:
                # Tenta criar nova sessão
                logger.info("Sessão inválida, criando nova")
                return await self.auth.get_or_create_session(force_new=True)
            
            raise SessionExpiredError(
                "Sessão expirada e auto-refresh não está habilitado."
            )
        
        # Garante autenticação no SIGEF (ou re-autentica se solicitado)
        if not session.is_sigef_authenticated or force_reauth:
            logger.info("Re-autenticando no SIGEF")
            session = await self.sigef.authenticate(session)
            await self.sessions.save(session)
        
        return session
    
    async def _execute_with_reauth(self, operation, *args, **kwargs):
        """Executa operação e re-autentica se sessão expirou."""
        try:
            session = await self._get_valid_session()
            return await operation(session, *args, **kwargs)
        except SessionExpiredError as e:
            # Primeira tentativa: re-autenticar no SIGEF
            logger.warning("Sessão SIGEF expirada, re-autenticando...")
            try:
                session = await self._get_valid_session(force_reauth=True)
                return await operation(session, *args, **kwargs)
            except SessionExpiredError:
                # Segunda tentativa: fazer login Gov.br completo novamente
                if self.auth:
                    logger.warning("Re-autenticação SIGEF falhou, fazendo novo login Gov.br...")
                    # Novo login Gov.br
                    session = await self.auth.get_or_create_session(force_new=True)
                    # Também precisa autenticar no SIGEF após novo login Gov.br
                    session = await self.sigef.authenticate(session)
                    await self.sessions.save(session)
                    return await operation(session, *args, **kwargs)
                raise
    
    async def get_parcela_info(self, codigo: str) -> Parcela:
        """
        Obtém informações de uma parcela.
        
        Args:
            codigo: Código SIGEF da parcela.
        
        Returns:
            Dados da parcela.
        """
        async def _get(session):
            return await self.sigef.get_parcela(codigo, session)
        
        return await self._execute_with_reauth(_get)
    
    async def download_csv(
        self,
        codigo: str,
        tipo: TipoExportacao | str,
        destino: Path | str | None = None,
    ) -> Path:
        """
        Baixa CSV de uma parcela.
        
        Args:
            codigo: Código SIGEF da parcela.
            tipo: Tipo de exportação (parcela, vertice, limite).
            destino: Caminho de destino (opcional).
        
        Returns:
            Caminho do arquivo baixado.
        """
        # Converte tipo se string
        if isinstance(tipo, str):
            tipo = TipoExportacao(tipo.lower())
        
        # Converte destino se string
        destino_path = Path(destino) if destino else None
        
        async def _download(session):
            return await self.sigef.download_csv(
                codigo=codigo,
                tipo=tipo,
                session=session,
                destino=destino_path,
            )
        
        return await self._execute_with_reauth(_download)
    
    async def download_all_csvs(
        self,
        codigo: str,
        destino_dir: Path | str | None = None,
    ) -> dict[str, Path]:
        """
        Baixa todos os CSVs de uma parcela.
        
        Args:
            codigo: Código SIGEF da parcela.
            destino_dir: Diretório de destino (opcional).
        
        Returns:
            Dicionário tipo -> caminho do arquivo.
        """
        destino_path = Path(destino_dir) if destino_dir else None
        
        async def _download_all(session):
            results = await self.sigef.download_all_csvs(
                codigo=codigo,
                session=session,
                destino_dir=destino_path,
            )
            # Converte enum keys para strings
            return {tipo.value: path for tipo, path in results.items()}
        
        return await self._execute_with_reauth(_download_all)
    
    async def download_batch(
        self,
        codigos: list[str],
        tipos: list[TipoExportacao] | None = None,
        destino_dir: Path | str | None = None,
    ) -> dict[str, dict[str, Path]]:
        """
        Baixa CSVs de múltiplas parcelas.
        
        Args:
            codigos: Lista de códigos SIGEF.
            tipos: Tipos a baixar (default: todos).
            destino_dir: Diretório de destino.
        
        Returns:
            Dicionário codigo -> {tipo -> path}.
        """
        tipos = tipos or list(TipoExportacao)
        destino_path = Path(destino_dir) if destino_dir else None
        
        results: dict[str, dict[str, Path]] = {}
        
        for codigo in codigos:
            logger.info(
                "Processando parcela",
                codigo=codigo,
                total=len(codigos),
                atual=len(results) + 1,
            )
            
            try:
                parcela_results = {}
                
                for tipo in tipos:
                    path = await self.download_csv(
                        codigo=codigo,
                        tipo=tipo,
                        destino=destino_path / f"{codigo}_{tipo.value}.csv" if destino_path else None,
                    )
                    parcela_results[tipo.value] = path
                
                results[codigo] = parcela_results
                
            except Exception as e:
                logger.error(
                    "Erro ao processar parcela",
                    codigo=codigo,
                    error=str(e),
                )
                # Continua com próximas parcelas
                results[codigo] = {"error": str(e)}  # type: ignore
        
        logger.info(
            "Batch concluído",
            total=len(codigos),
            sucesso=sum(1 for r in results.values() if "error" not in r),
            falhas=sum(1 for r in results.values() if "error" in r),
        )
        
        return results
    
    async def download_memorial(
        self,
        codigo: str,
        destino: Path | str | None = None,
    ) -> Path:
        """
        Baixa memorial descritivo (PDF) de uma parcela.
        
        Args:
            codigo: Código SIGEF da parcela.
            destino: Caminho de destino (opcional).
        
        Returns:
            Caminho do arquivo PDF baixado.
        """
        destino_path = Path(destino) if destino else None
        
        async def _download(session):
            return await self.sigef.download_memorial(
                codigo=codigo,
                session=session,
                destino=destino_path,
            )
        
        return await self._execute_with_reauth(_download)
    
    async def open_parcela_browser(self, codigo: str) -> None:
        """
        Abre a página da parcela no navegador autenticado.
        
        Args:
            codigo: Código SIGEF da parcela.
        """
        async def _open(session):
            return await self.sigef.open_parcela_browser(codigo, session)
        
        return await self._execute_with_reauth(_open)
    
    async def get_parcela_detalhes(self, codigo: str) -> dict:
        """
        Obtém todos os detalhes da parcela.
        
        Args:
            codigo: Código SIGEF da parcela.
            
        Returns:
            Dicionário com todos os detalhes extraídos da página.
        """
        async def _get(session):
            return await self.sigef.get_parcela_detalhes(codigo, session)
        
        return await self._execute_with_reauth(_get)
