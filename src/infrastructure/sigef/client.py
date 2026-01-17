"""
Cliente SIGEF INCRA usando requisições HTTP diretas.

Implementação de alta performance que usa httpx para
fazer download de CSVs diretamente via API, sem browser.

NOTA: A autenticação inicial requer Playwright para
completar o fluxo OAuth Gov.br -> SIGEF.
"""

import asyncio
import concurrent.futures
import re
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import get_settings
from src.core.exceptions import (
    InvalidParcelaCodeError,
    ParcelaNotFoundError,
    SessionExpiredError,
    SigefError,
)
from src.core.logging import get_logger
from src.domain.entities import Cookie, Parcela, Session, TipoExportacao
from src.domain.interfaces import ISigefClient

logger = get_logger(__name__)

# Regex para validar código de parcela SIGEF
PARCELA_CODE_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ThreadPoolExecutor para Playwright
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="sigef-playwright")


class HttpSigefClient(ISigefClient):
    """
    Cliente SIGEF que usa requisições HTTP diretas.
    
    Mais eficiente que usar browser para downloads,
    permite execução em modo headless e paralelo.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = str(self.settings.sigef_base_url).rstrip("/")
    
    def _validate_parcela_code(self, codigo: str) -> str:
        """Valida e normaliza código de parcela."""
        codigo = codigo.strip().lower()
        
        if not PARCELA_CODE_PATTERN.match(codigo):
            raise InvalidParcelaCodeError(codigo)
        
        return codigo
    
    def _build_cookies_dict(self, session: Session) -> dict[str, str]:
        """Constrói dicionário de cookies para requisições."""
        cookies = session.get_cookies_dict("all")
        
        if not cookies:
            raise SessionExpiredError("Sessão não possui cookies válidos.")
        
        return cookies
    
    def _get_headers(self) -> dict[str, str]:
        """Retorna headers padrão para requisições."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/csv,text/plain,*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": f"{self.base_url}/",
        }
    
    async def authenticate(self, govbr_session: Session) -> Session:
        """
        Autentica no SIGEF usando sessão do Gov.br via Playwright.
        
        Usa browser para completar fluxo OAuth Gov.br -> SIGEF,
        capturando todos os cookies necessários.
        """
        if not govbr_session.is_govbr_authenticated:
            raise SigefError("Sessão Gov.br não está autenticada.")
        
        logger.info("Autenticando no SIGEF com sessão Gov.br (via browser)")
        
        # Executa em thread separada para evitar problemas com event loop
        loop = asyncio.get_event_loop()
        updated_session = await loop.run_in_executor(
            _executor,
            self._authenticate_sigef_sync,
            govbr_session,
        )
        
        return updated_session
    
    def _authenticate_sigef_sync(self, govbr_session: Session) -> Session:
        """
        Autenticação síncrona no SIGEF via Playwright.
        
        Fluxo igual ao legacy:
        1. Carrega contexto com storage_state do Gov.br (cookies + localStorage completo)
        2. Acessa página inicial do SIGEF
        3. Clica no botão "Entrar com Gov.br"
        4. Gov.br reconhece automaticamente e redireciona de volta
        5. SIGEF cria sessão e define cookies
        """
        import os
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,  # Precisa ser visível para OAuth
                args=["--disable-blink-features=AutomationControlled"],
            )
            
            try:
                # Usa storage_state se disponível (igual ao legacy!)
                if govbr_session.storage_state_path and os.path.exists(govbr_session.storage_state_path):
                    logger.info(f"Carregando storage_state de: {govbr_session.storage_state_path}")
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        storage_state=govbr_session.storage_state_path,
                    )
                else:
                    # Fallback: cria contexto e adiciona cookies manualmente
                    logger.warning("storage_state não disponível, usando cookies manualmente")
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                    )
                    
                    # Adiciona cookies do Gov.br ao contexto
                    playwright_cookies = []
                    for cookie in govbr_session.govbr_cookies:
                        playwright_cookies.append({
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain,
                            "path": cookie.path or "/",
                            "secure": cookie.secure,
                            "httpOnly": cookie.http_only,
                        })
                    
                    if playwright_cookies:
                        context.add_cookies(playwright_cookies)
                        logger.info(f"Adicionados {len(playwright_cookies)} cookies do Gov.br ao contexto")
                
                page = context.new_page()
                
                # PASSO 1: Acessa página inicial do SIGEF
                logger.info("Acessando página inicial do SIGEF")
                page.goto(f"{self.base_url}/", wait_until="networkidle", timeout=60000)
                
                current_url = page.url
                logger.info(f"URL após carregar SIGEF: {current_url}")
                
                # PASSO 2: Procura e clica no botão de login Gov.br
                logger.info("Procurando botão de login...")
                login_clicked = False
                
                # Seletores para o botão Entrar
                # O botão é: <button class="br-button sign-in small">Entrar</button>
                login_selectors = [
                    "button.sign-in",
                    "button:has-text('Entrar')",
                    "text=Entrar",
                    "a[href*='oauth']",
                ]
                
                for selector in login_selectors:
                    try:
                        btn = page.locator(selector).first
                        if btn.is_visible(timeout=2000):
                            logger.info(f"Encontrado botão: {selector}")
                            btn.click()
                            login_clicked = True
                            break
                    except Exception:
                        continue
                
                if not login_clicked:
                    # Se não encontrou botão, pode ser que já está logado
                    # ou o layout mudou - tenta acessar uma página autenticada
                    logger.warning("Botão de login não encontrado, verificando se já está logado...")
                    if page.locator("text=Sair").count() > 0:
                        logger.info("Já está logado no SIGEF!")
                    else:
                        logger.warning("Não encontrou botão de login nem indicação de estar logado")
                
                # PASSO 3: Aguarda fluxo OAuth completar
                # O fluxo vai: SIGEF -> Gov.br -> (autorização) -> SIGEF (callback)
                logger.info("Aguardando fluxo OAuth...")
                
                # Aguarda até não estar mais no Gov.br
                max_wait = 45  # segundos
                waited = 0
                while waited < max_wait:
                    page.wait_for_timeout(1000)
                    waited += 1
                    current_url = page.url
                    
                    # Se voltou para o SIGEF, o fluxo completou
                    if "sigef.incra.gov.br" in current_url and "oauth2" not in current_url:
                        logger.info(f"Redirecionado de volta ao SIGEF: {current_url}")
                        break
                    
                    # Se está em servicos.acesso.gov.br - página de autorização OAuth
                    # Precisa clicar em "Autorizar" ou similar
                    if "servicos.acesso.gov.br" in current_url:
                        logger.info(f"Página de autorização Gov.br detectada: {current_url}")
                        
                        # Tenta encontrar e clicar no botão de autorizar
                        auth_selectors = [
                            "button:has-text('Autorizar')",
                            "button:has-text('Permitir')",
                            "button:has-text('Continuar')",
                            "button:has-text('Confirmar')",
                            "input[type='submit']",
                            "button[type='submit']",
                            ".btn-primary",
                            "a:has-text('Autorizar')",
                            "a:has-text('Continuar')",
                        ]
                        
                        for selector in auth_selectors:
                            try:
                                btn = page.locator(selector).first
                                if btn.is_visible(timeout=1000):
                                    logger.info(f"Clicando em botão de autorização: {selector}")
                                    btn.click()
                                    page.wait_for_timeout(2000)
                                    break
                            except Exception:
                                continue
                    
                    # Se está em página de login Gov.br, sessão expirou
                    if any(x in current_url for x in ["sso.acesso.gov.br/login", "/authorize"]):
                        if page.locator("text=Certificado Digital").count() > 0 or \
                           page.locator("input[type='password']").count() > 0:
                            logger.warning("Sessão Gov.br expirada - página de login detectada")
                            raise SessionExpiredError("Sessão Gov.br expirada. Necessário novo login.")
                    
                    logger.debug(f"Aguardando... URL atual: {current_url}")
                
                # Aguarda página final carregar
                page.wait_for_load_state("networkidle", timeout=10000)
                
                final_url = page.url
                logger.info(f"URL final: {final_url}")
                
                # Captura todos os cookies
                all_cookies = context.cookies()
                
                logger.info(f"Total de cookies capturados: {len(all_cookies)}")
                for c in all_cookies:
                    logger.debug(f"Cookie: {c['name']} @ {c.get('domain', '')}")
                
                sigef_cookies = []
                govbr_updated_cookies = []
                
                for c in all_cookies:
                    domain = c.get("domain", "")
                    cookie_obj = Cookie(
                        name=c["name"],
                        value=c["value"],
                        domain=domain,
                        path=c.get("path", "/"),
                        expires=c.get("expires"),
                        http_only=c.get("httpOnly", False),
                        secure=c.get("secure", False),
                        same_site=c.get("sameSite", "Lax"),
                    )
                    
                    if "sigef" in domain or "incra" in domain:
                        sigef_cookies.append(cookie_obj)
                    elif "gov.br" in domain or "acesso" in domain:
                        govbr_updated_cookies.append(cookie_obj)
                
                logger.info(f"Cookies SIGEF: {len(sigef_cookies)}, Gov.br: {len(govbr_updated_cookies)}")
                
                # Atualiza cookies do Gov.br também (podem ter sido renovados)
                if govbr_updated_cookies:
                    govbr_session.govbr_cookies = govbr_updated_cookies
                
                # Atualiza sessão
                govbr_session.sigef_cookies = sigef_cookies
                govbr_session.is_sigef_authenticated = len(sigef_cookies) > 0
                govbr_session.touch()
                
                return govbr_session
                
            finally:
                browser.close()
    
    async def get_parcela(self, codigo: str, session: Session) -> Parcela:
        """
        Obtém dados básicos de uma parcela extraindo do HTML.
        """
        codigo = self._validate_parcela_code(codigo)
        
        cookies = self._build_cookies_dict(session)
        
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            cookies=cookies,
            headers=self._get_headers(),
        ) as client:
            url = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
            response = await client.get(url)
            
            if response.status_code == 404:
                raise ParcelaNotFoundError(codigo)
            
            if response.status_code != 200:
                raise SigefError(
                    f"Erro ao buscar parcela: HTTP {response.status_code}"
                )
            
            # Parse do HTML para extrair dados
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Salva HTML completo para debug
            debug_path = Path("debug_parcela.html")
            debug_path.write_text(response.text, encoding='utf-8')
            logger.info(f"HTML salvo em: {debug_path.absolute()}")
            
            # Estratégia: buscar <th> e pegar <td> na mesma <tr>
            
            # Extrai denominação
            denominacao = None
            th_denom = soup.find('th', string=re.compile('Denominação', re.IGNORECASE))
            if th_denom:
                tr = th_denom.find_parent('tr')
                if tr:
                    td = tr.find('td')
                    if td:
                        denominacao = td.get_text(strip=True)
            logger.info(f"Denominação extraída: {denominacao}")
            
            # Extrai área
            area_ha = None
            th_area = soup.find('th', string=re.compile('Área', re.IGNORECASE))
            if th_area:
                tr = th_area.find_parent('tr')
                if tr:
                    td = tr.find('td')
                    if td:
                        area_text = td.get_text(strip=True)
                        # Extrai número (ex: "327,8232 ha")
                        match = re.search(r'([\d.,]+)\s*ha', area_text, re.IGNORECASE)
                        if match:
                            try:
                                area_ha = float(match.group(1).replace('.', '').replace(',', '.'))
                            except ValueError:
                                pass
            logger.info(f"Área extraída: {area_ha}")
            
            # Extrai município e UF da seção "Municípios"
            municipio = None
            uf = None
            th_municipios = soup.find('th', string=re.compile('Municípios', re.IGNORECASE))
            if th_municipios:
                # Pega próxima <tr> após o header
                tr_municipios = th_municipios.find_parent('tr')
                if tr_municipios:
                    next_tr = tr_municipios.find_next_sibling('tr')
                    if next_tr:
                        td = next_tr.find('td')
                        if td:
                            # Formato: "Bocaiúva do Sul - PR"
                            mun_uf_text = td.get_text(strip=True)
                            if ' - ' in mun_uf_text:
                                parts = mun_uf_text.rsplit(' - ', 1)
                                municipio = parts[0].strip()
                                uf = parts[1].strip()
            logger.info(f"Município extraído: {municipio}")
            logger.info(f"UF extraída: {uf}")
            
            # Extrai situação
            situacao = None
            th_situacao = soup.find('th', string=re.compile('Situação', re.IGNORECASE))
            if th_situacao:
                tr = th_situacao.find_parent('tr')
                if tr:
                    td = tr.find('td')
                    if td:
                        situacao_text = td.get_text(strip=True)
                        logger.info(f"Situação texto encontrado: {situacao_text}")
                        if 'certificada' in situacao_text.lower():
                            from src.domain.entities import ParcelaSituacao
                            situacao = ParcelaSituacao.CERTIFICADA
            logger.info(f"Situação final: {situacao}")
            
            return Parcela(
                codigo=codigo,
                denominacao=denominacao,
                area_ha=area_ha,
                municipio=municipio,
                uf=uf,
                situacao=situacao
            )
    
    async def get_parcela_detalhes(self, codigo: str, session: Session) -> dict:
        """Extrai TODOS os detalhes da página HTML da parcela para exibição."""
        codigo = self._validate_parcela_code(codigo)
        
        cookies = self._build_cookies_dict(session)
        
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            cookies=cookies,
            headers=self._get_headers(),
        ) as client:
            url = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
            logger.info(f"Buscando detalhes da parcela em: {url}")
            
            response = await client.get(url)
            
            logger.info(f"Status da resposta: {response.status_code}")
            
            if response.status_code == 404:
                raise ParcelaNotFoundError(codigo)
            
            if response.status_code != 200:
                raise SigefError(
                    f"Erro ao buscar detalhes da parcela: HTTP {response.status_code}"
                )
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            detalhes = {
                "codigo": codigo,
                "url": url,
                "informacoes_parcela": {},
                "historico": {"quantidade": 0, "requerimentos": []},
                "area_georreferenciada": {},
                "detentores": [],
                "registro": {}
            }
            
            # Função auxiliar para extrair valor de uma linha da tabela
            def extrair_campo_tabela(tabela, label: str) -> str | None:
                """Busca um <th> com o label e retorna o texto do <td> correspondente."""
                if not tabela:
                    return None
                th = tabela.find('th', string=re.compile(label, re.IGNORECASE))
                if th:
                    tr = th.find_parent('tr')
                    if tr:
                        td = tr.find('td')
                        if td:
                            return td.get_text(separator=' ', strip=True)
                return None
            
            # === 1. INFORMAÇÕES DA PARCELA ===
            # Busca pelo painel "Informações da parcela"
            paineis = soup.find_all('div', class_='panel')
            
            for painel in paineis:
                header = painel.find('div', class_='panel-header')
                if not header:
                    continue
                    
                header_text = header.get_text()
                
                # INFORMAÇÕES DA PARCELA
                if 'Informações da parcela' in header_text:
                    content = painel.find('div', class_='panel-content')
                    if content:
                        tabelas = content.find_all('table')
                        
                        # Primeira tabela: dados básicos
                        if len(tabelas) > 0:
                            tabela1 = tabelas[0]
                            detalhes["informacoes_parcela"]["codigo"] = extrair_campo_tabela(tabela1, "Código")
                            detalhes["informacoes_parcela"]["denominacao"] = extrair_campo_tabela(tabela1, "Denominação")
                            detalhes["informacoes_parcela"]["area"] = extrair_campo_tabela(tabela1, "Área")
                            detalhes["informacoes_parcela"]["data_entrada"] = extrair_campo_tabela(tabela1, "Data de Entrada")
                            detalhes["informacoes_parcela"]["situacao"] = extrair_campo_tabela(tabela1, "Situação")
                        
                        # Segunda tabela: responsável técnico
                        if len(tabelas) > 1:
                            tabela2 = tabelas[1]
                            detalhes["informacoes_parcela"]["responsavel_tecnico"] = extrair_campo_tabela(tabela2, "Responsável Técnico")
                            detalhes["informacoes_parcela"]["documento_rt"] = extrair_campo_tabela(tabela2, "Documento de RT")
                            
                            # Data do envio (está em uma <td> após "Envio")
                            th_envio = tabela2.find('th', string=re.compile('Envio', re.IGNORECASE))
                            if th_envio:
                                tr_envio = th_envio.find_parent('tr')
                                if tr_envio:
                                    tds = tr_envio.find_all('td')
                                    if len(tds) > 1:
                                        detalhes["informacoes_parcela"]["data_envio"] = tds[1].get_text(strip=True)
                
                # HISTÓRICO
                elif 'Histórico' in header_text:
                    # Extrai quantidade do título
                    match_qtd = re.search(r'Qtd\.\s*Requerimentos:\s*(\d+)', header_text)
                    if match_qtd:
                        detalhes["historico"]["quantidade"] = int(match_qtd.group(1))
                    
                    content = painel.find('div', class_='panel-content')
                    if content:
                        tabela = content.find('table')
                        if tabela:
                            tbody = tabela.find('tbody')
                            if tbody:
                                rows = tbody.find_all('tr')
                                for row in rows:
                                    tds = row.find_all('td')
                                    if len(tds) >= 3 and 'Nenhum requerimento' not in tds[0].get_text():
                                        detalhes["historico"]["requerimentos"].append({
                                            "requerimento": tds[0].get_text(strip=True),
                                            "status": tds[1].get_text(strip=True),
                                            "data": tds[2].get_text(strip=True)
                                        })
                
                # ÁREA GEORREFERENCIADA
                elif 'Área Georreferenciada' in header_text:
                    content = painel.find('div', class_='panel-content')
                    if content:
                        tabela = content.find('table')
                        if tabela:
                            detalhes["area_georreferenciada"]["denominacao"] = extrair_campo_tabela(tabela, "Denominação")
                            detalhes["area_georreferenciada"]["situacao"] = extrair_campo_tabela(tabela, "Situação")
                            detalhes["area_georreferenciada"]["natureza"] = extrair_campo_tabela(tabela, "Natureza")
                            detalhes["area_georreferenciada"]["codigo_incra"] = extrair_campo_tabela(tabela, "Código do Imóvel")
                            detalhes["area_georreferenciada"]["numero_parcelas"] = extrair_campo_tabela(tabela, "Número parcelas")
                            
                            # Municípios (várias linhas após th "Municípios")
                            municipios = []
                            th_mun = tabela.find('th', string=re.compile('Municípios', re.IGNORECASE))
                            if th_mun:
                                tr_mun = th_mun.find_parent('tr')
                                if tr_mun:
                                    next_tr = tr_mun.find_next_sibling('tr')
                                    while next_tr:
                                        td = next_tr.find('td')
                                        if td:
                                            texto = td.get_text(strip=True)
                                            # Para de buscar se encontrar outro <th> ou texto vazio
                                            if texto and ' - ' in texto and not td.find('th'):
                                                municipios.append(texto)
                                                next_tr = next_tr.find_next_sibling('tr')
                                            else:
                                                break
                                        else:
                                            break
                            detalhes["area_georreferenciada"]["municipios"] = municipios
                
                # IDENTIFICAÇÃO DO DETENTOR
                elif 'detentor' in header_text.lower():
                    content = painel.find('div', class_='panel-content')
                    if content:
                        tabela = content.find('table')
                        if tabela:
                            tbody = tabela.find('tbody')
                            if tbody:
                                rows = tbody.find_all('tr')
                                for row in rows:
                                    tds = row.find_all('td')
                                    if len(tds) >= 2:
                                        detalhes["detentores"].append({
                                            "nome": tds[0].get_text(strip=True),
                                            "cpf_cnpj": tds[1].get_text(strip=True)
                                        })
                
                # INFORMAÇÕES DE REGISTRO
                elif 'Registro' in header_text and 'Informações' in header_text:
                    content = painel.find('div', class_='panel-content')
                    if content:
                        tabela = content.find('table')
                        if tabela:
                            detalhes["registro"]["cartorio"] = extrair_campo_tabela(tabela, "Cartório")
                            detalhes["registro"]["municipio_uf"] = extrair_campo_tabela(tabela, "Município - UF")
                            detalhes["registro"]["cns"] = extrair_campo_tabela(tabela, "Código Nacional de Serventia")
                            detalhes["registro"]["matricula"] = extrair_campo_tabela(tabela, "Matrícula")
                            detalhes["registro"]["situacao_registro"] = extrair_campo_tabela(tabela, "Situação do Registro")
            
            logger.info(f"Detalhes extraídos: {len(detalhes['informacoes_parcela'])} campos em info_parcela")
            
            return detalhes
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def download_csv(
        self,
        codigo: str,
        tipo: TipoExportacao,
        session: Session,
        destino: Path | None = None,
    ) -> Path:
        """
        Baixa CSV de uma parcela.
        
        Usa retry automático com backoff exponencial
        para lidar com falhas temporárias.
        """
        codigo = self._validate_parcela_code(codigo)
        
        # Monta URL de download
        url = f"{self.base_url}/geo/exportar/{tipo.value}/csv/{codigo}/"
        
        logger.info(
            "Baixando CSV",
            tipo=tipo.value,
            codigo=codigo,
        )
        
        cookies = self._build_cookies_dict(session)
        
        # Headers com Referer específico da parcela (importante para SIGEF)
        headers = self._get_headers()
        headers["Referer"] = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
        
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0,
            cookies=cookies,
            headers=headers,
        ) as client:
            response = await client.get(url)
            
            if response.status_code == 404:
                raise ParcelaNotFoundError(codigo)
            
            if response.status_code == 401:
                raise SessionExpiredError(
                    "Sessão expirada. Faça login novamente."
                )
            
            if response.status_code != 200:
                raise SigefError(
                    f"Erro ao baixar CSV: HTTP {response.status_code}"
                )
            
            # Verifica se é realmente um CSV
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                # Provavelmente redirecionou para login
                raise SessionExpiredError(
                    "Sessão inválida. Recebido HTML ao invés de CSV."
                )
            
            # Define destino
            if destino is None:
                downloads_dir = self.settings.downloads_dir
                downloads_dir.mkdir(parents=True, exist_ok=True)
                
                # Nome: codigo_tipo.csv
                filename = f"{codigo}_{tipo.value}.csv"
                destino = downloads_dir / filename
            
            # Salva arquivo
            destino.write_bytes(response.content)
            
            logger.info(
                "CSV baixado com sucesso",
                tipo=tipo.value,
                destino=str(destino),
                tamanho_bytes=len(response.content),
            )
            
            return destino
    
    async def download_all_csvs(
        self,
        codigo: str,
        session: Session,
        destino_dir: Path | None = None,
    ) -> dict[TipoExportacao, Path]:
        """
        Baixa todos os CSVs de uma parcela.
        
        Faz downloads em sequência para evitar rate limiting.
        """
        codigo = self._validate_parcela_code(codigo)
        destino_dir = destino_dir or self.settings.downloads_dir
        destino_dir.mkdir(parents=True, exist_ok=True)
        
        results: dict[TipoExportacao, Path] = {}
        
        for tipo in TipoExportacao:
            destino = destino_dir / f"{codigo}_{tipo.value}.csv"
            
            try:
                path = await self.download_csv(
                    codigo=codigo,
                    tipo=tipo,
                    session=session,
                    destino=destino,
                )
                results[tipo] = path
            except Exception as e:
                logger.error(
                    "Falha ao baixar CSV",
                    tipo=tipo.value,
                    codigo=codigo,
                    error=str(e),
                )
                raise
        
        logger.info(
            "Todos os CSVs baixados",
            codigo=codigo,
            arquivos=len(results),
        )
        
        return results
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def download_memorial(
        self,
        codigo: str,
        session: Session,
        destino: Path | None = None,
    ) -> Path:
        """
        Baixa memorial descritivo (PDF) de uma parcela.
        
        URL: /geo/parcela/memorial/{codigo}/
        """
        codigo = self._validate_parcela_code(codigo)
        
        # Monta URL de download do memorial
        url = f"{self.base_url}/geo/parcela/memorial/{codigo}/"
        
        logger.info(
            "Baixando memorial descritivo",
            codigo=codigo,
        )
        
        cookies = self._build_cookies_dict(session)
        
        # Headers com Referer específico da parcela (importante para SIGEF)
        headers = self._get_headers()
        headers["Referer"] = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*"
        
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0,
            cookies=cookies,
            headers=headers,
        ) as client:
            response = await client.get(url)
            
            if response.status_code == 404:
                raise ParcelaNotFoundError(codigo)
            
            if response.status_code == 401:
                raise SessionExpiredError(
                    "Sessão expirada. Faça login novamente."
                )
            
            if response.status_code != 200:
                raise SigefError(
                    f"Erro ao baixar memorial: HTTP {response.status_code}"
                )
            
            # Verifica se é um PDF
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type and "application/pdf" not in content_type:
                # Provavelmente redirecionou para login
                raise SessionExpiredError(
                    "Sessão inválida. Recebido HTML ao invés de PDF."
                )
            
            # Define destino
            if destino is None:
                downloads_dir = self.settings.downloads_dir
                downloads_dir.mkdir(parents=True, exist_ok=True)
                
                # Nome: codigo_memorial.pdf
                filename = f"{codigo}_memorial.pdf"
                destino = downloads_dir / filename
            
            # Salva arquivo
            destino.write_bytes(response.content)
            
            logger.info(
                "Memorial descritivo baixado com sucesso",
                destino=str(destino),
                tamanho_bytes=len(response.content),
            )
            
            return destino
    
    async def open_parcela_browser(self, codigo: str, session: Session) -> None:
        """
        Abre a página de detalhes da parcela em um navegador Playwright autenticado.
        
        Args:
            codigo: Código SIGEF da parcela
            session: Sessão autenticada
        """
        codigo = self._validate_parcela_code(codigo)
        url = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
        
        logger.info(f"Abrindo página da parcela no navegador: {url}")
        
        def _open_browser():
            with sync_playwright() as p:
                # Abre navegador não-headless para o usuário ver
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                
                # Adiciona cookies da sessão autenticada (Gov.br + SIGEF)
                cookies_list = []
                for cookie in session.govbr_cookies + session.sigef_cookies:
                    cookies_list.append({
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain or ".incra.gov.br",
                        "path": cookie.path or "/",
                    })
                
                context.add_cookies(cookies_list)
                
                # Abre página
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                logger.info("Página aberta. Navegador permanecerá aberto para visualização.")
                # Não fecha o navegador automaticamente - deixa o usuário navegar
        
        # Executa no thread pool para não bloquear
        await asyncio.get_event_loop().run_in_executor(_executor, _open_browser)
