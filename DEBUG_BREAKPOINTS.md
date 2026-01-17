# 🔍 Guia de Debug - Pontos de Breakpoint

## Fluxo Completo de uma Consulta/Download

```
Cliente (Frontend/Postman)
    ↓
[1] API Route (src/api/v1/routes/sigef.py)
    ↓
[2] Service (src/services/sigef_service.py)
    ↓
[3] Autenticação/Validação (src/services/auth_service.py)
    ↓
[4] Cliente SIGEF (src/infrastructure/sigef/client.py)
    ↓
[5] Requisição HTTP (httpx)
    ↓
SIGEF INCRA
```

---

## 📍 Breakpoints Recomendados

### [1] API Route - Entrada da Requisição

**Arquivo:** `src/api/v1/routes/sigef.py`

#### Para Busca de Parcela:
```python
@router.get("/parcela/{codigo}")
async def get_parcela(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> ParcelaInfoResponse:
    """Obtém informações de uma parcela."""
    try:
        # 🔴 BREAKPOINT 1: Entrada da requisição
        # Inspecione: codigo, sigef_service
        parcela = await sigef_service.get_parcela_info(codigo)
        
        # 🔴 BREAKPOINT 2: Após buscar parcela
        # Inspecione: parcela (dados retornados)
        return ParcelaInfoResponse(...)
```

**Linha sugerida:** Logo após `try:` (linha ~38)

#### Para Download de CSV:
```python
@router.post("/download")
async def download_csv(
    request: DownloadRequest,
    sigef_service: SigefService = Depends(get_sigef_service),
) -> DownloadResponse:
    """Baixa CSV de uma parcela."""
    try:
        # 🔴 BREAKPOINT 3: Entrada do download
        # Inspecione: request.codigo, request.tipo
        tipo = TipoExportacao(request.tipo.value)
        
        path = await sigef_service.download_csv(
            codigo=request.codigo,
            tipo=tipo,
        )
        
        # 🔴 BREAKPOINT 4: Após download
        # Inspecione: path (caminho do arquivo salvo)
        return DownloadResponse(...)
```

**Linha sugerida:** Logo após `try:` (linha ~73)

#### Para Download de Memorial:
```python
@router.get("/memorial/{codigo}")
async def download_memorial(
    codigo: str,
    sigef_service: SigefService = Depends(get_sigef_service),
):
    """Retorna memorial descritivo (PDF) para download direto."""
    try:
        # 🔴 BREAKPOINT 5: Entrada do memorial
        # Inspecione: codigo
        path = await sigef_service.download_memorial(codigo=codigo)
        
        # 🔴 BREAKPOINT 6: Após download do PDF
        # Inspecione: path, path.exists(), path.stat().st_size
        return FileResponse(...)
```

**Linha sugerida:** Logo após `try:` (linha ~199)

---

### [2] Service - Lógica de Negócio

**Arquivo:** `src/services/sigef_service.py`

#### Método `get_parcela_info`:
```python
async def get_parcela_info(self, codigo: str) -> Parcela:
    """Obtém informações de uma parcela."""
    # 🔴 BREAKPOINT 7: Entrada no service
    # Inspecione: codigo, self.sigef, self.sessions
    
    async def _get(session):
        # 🔴 BREAKPOINT 8: Dentro da função de execução
        # Inspecione: session (dados da sessão)
        return await self.sigef.get_parcela(codigo, session)
    
    # 🔴 BREAKPOINT 9: Antes de executar com reauth
    return await self._execute_with_reauth(_get)
```

**Linhas sugeridas:** 100, 103, 108

#### Método `download_csv`:
```python
async def download_csv(
    self,
    codigo: str,
    tipo: TipoExportacao | str,
    destino: Path | str | None = None,
) -> Path:
    """Baixa CSV de uma parcela."""
    # 🔴 BREAKPOINT 10: Entrada no download
    # Inspecione: codigo, tipo, destino
    
    if isinstance(tipo, str):
        tipo = TipoExportacao(tipo.lower())
    
    destino_path = Path(destino) if destino else None
    
    async def _download(session):
        # 🔴 BREAKPOINT 11: Dentro da função de download
        # Inspecione: session, destino_path
        return await self.sigef.download_csv(
            codigo=codigo,
            tipo=tipo,
            session=session,
            destino=destino_path,
        )
    
    # 🔴 BREAKPOINT 12: Antes de executar
    return await self._execute_with_reauth(_download)
```

**Linhas sugeridas:** 116, 126, 135

#### Método `_execute_with_reauth` (IMPORTANTE!):
```python
async def _execute_with_reauth(self, operation, *args, **kwargs):
    """Executa operação e re-autentica se sessão expirou."""
    try:
        # 🔴 BREAKPOINT 13: Tentativa inicial
        # Inspecione: operation, args, kwargs
        session = await self._get_valid_session()
        
        # 🔴 BREAKPOINT 14: Sessão obtida
        # Inspecione: session.is_valid(), session.is_sigef_authenticated
        return await operation(session, *args, **kwargs)
        
    except SessionExpiredError as e:
        # 🔴 BREAKPOINT 15: Sessão expirada (RE-AUTH)
        # Inspecione: e, str(e)
        logger.warning("Sessão SIGEF expirada, re-autenticando...")
        
        try:
            session = await self._get_valid_session(force_reauth=True)
            # 🔴 BREAKPOINT 16: Após re-auth
            return await operation(session, *args, **kwargs)
```

**Linhas sugeridas:** 73, 77, 82, 87, 91

---

### [3] Validação de Sessão

**Arquivo:** `src/services/sigef_service.py`

```python
async def _get_valid_session(self, force_reauth: bool = False) -> Session:
    """Obtém sessão válida ou lança exceção."""
    # 🔴 BREAKPOINT 17: Início da validação
    session = await self.sessions.load_latest()
    
    # 🔴 BREAKPOINT 18: Sessão carregada
    # Inspecione: session, session.is_valid() se session existe
    
    if not session or not session.is_valid():
        # 🔴 BREAKPOINT 19: Sessão inválida
        if self.auth:
            logger.info("Sessão inválida, criando nova")
            return await self.auth.get_or_create_session(force_new=True)
        raise SessionExpiredError(...)
    
    # 🔴 BREAKPOINT 20: Verificando SIGEF auth
    if not session.is_sigef_authenticated or force_reauth:
        # 🔴 BREAKPOINT 21: Precisa autenticar no SIGEF
        logger.info("Re-autenticando no SIGEF")
        session = await self.sigef.authenticate(session)
```

**Linhas sugeridas:** 44, 47, 50, 58, 61

---

### [4] Cliente SIGEF - Requisição HTTP

**Arquivo:** `src/infrastructure/sigef/client.py`

#### Método `download_csv`:
```python
async def download_csv(
    self,
    codigo: str,
    tipo: TipoExportacao,
    session: Session,
    destino: Path | None = None,
) -> Path:
    """Baixa CSV de uma parcela."""
    # 🔴 BREAKPOINT 22: Entrada no cliente
    # Inspecione: codigo, tipo, session
    
    codigo = self._validate_parcela_code(codigo)
    
    # 🔴 BREAKPOINT 23: Código validado
    url = f"{self.base_url}/geo/exportar/{tipo.value}/csv/{codigo}/"
    
    # 🔴 BREAKPOINT 24: Antes da requisição HTTP
    # Inspecione: url, cookies (self._build_cookies_dict(session))
    
    logger.info("Baixando CSV", tipo=tipo.value, codigo=codigo)
    
    cookies = self._build_cookies_dict(session)
    headers = self._get_headers()
    headers["Referer"] = f"{self.base_url}/geo/parcela/detalhe/{codigo}/"
    
    async with httpx.AsyncClient(...) as client:
        # 🔴 BREAKPOINT 25: Antes do GET
        response = await client.get(url)
        
        # 🔴 BREAKPOINT 26: Resposta recebida
        # Inspecione: response.status_code, response.headers, len(response.content)
        
        if response.status_code == 404:
            raise ParcelaNotFoundError(codigo)
        
        if response.status_code == 401:
            # 🔴 BREAKPOINT 27: Não autorizado
            raise SessionExpiredError(...)
        
        if response.status_code != 200:
            # 🔴 BREAKPOINT 28: Erro HTTP
            raise SigefError(...)
        
        # Verifica se é realmente um CSV
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            # 🔴 BREAKPOINT 29: Recebeu HTML (sessão expirou)
            raise SessionExpiredError(...)
        
        # 🔴 BREAKPOINT 30: Salvando arquivo
        destino.write_bytes(response.content)
        
        # 🔴 BREAKPOINT 31: Arquivo salvo com sucesso
        logger.info("CSV baixado com sucesso", destino=str(destino))
        return destino
```

**Linhas sugeridas:** 360, 365, 375, 390, 395, 402, 407, 414, 419, 430, 438

#### Método `download_memorial`:
```python
async def download_memorial(
    self,
    codigo: str,
    session: Session,
    destino: Path | None = None,
) -> Path:
    """Baixa memorial descritivo (PDF)."""
    # 🔴 BREAKPOINT 32: Entrada
    codigo = self._validate_parcela_code(codigo)
    
    url = f"{self.base_url}/geo/parcela/memorial/{codigo}/"
    
    # 🔴 BREAKPOINT 33: URL montada
    # Inspecione: url
    
    cookies = self._build_cookies_dict(session)
    headers = self._get_headers()
    headers["Accept"] = "...application/pdf..."
    
    async with httpx.AsyncClient(...) as client:
        # 🔴 BREAKPOINT 34: Antes do GET
        response = await client.get(url)
        
        # 🔴 BREAKPOINT 35: PDF recebido
        # Inspecione: response.status_code, content_type, len(response.content)
        
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            # 🔴 BREAKPOINT 36: Recebeu HTML ao invés de PDF
            raise SessionExpiredError(...)
```

**Linhas sugeridas:** 452, 458, 470, 475, 483

---

### [5] Autenticação SIGEF (via Playwright)

**Arquivo:** `src/infrastructure/sigef/client.py`

```python
def _authenticate_sigef_sync(self, govbr_session: Session) -> Session:
    """Autenticação síncrona no SIGEF via Playwright."""
    # 🔴 BREAKPOINT 37: Início da autenticação
    # Inspecione: govbr_session
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, ...)
        
        try:
            # 🔴 BREAKPOINT 38: Browser aberto
            if govbr_session.storage_state_path:
                # 🔴 BREAKPOINT 39: Carregando storage_state
                context = browser.new_context(
                    storage_state=govbr_session.storage_state_path
                )
            
            page = context.new_page()
            
            # 🔴 BREAKPOINT 40: Acessando SIGEF
            page.goto(f"{self.base_url}/", wait_until="networkidle")
            
            # 🔴 BREAKPOINT 41: Página carregada
            current_url = page.url
            
            # 🔴 BREAKPOINT 42: Procurando botão de login
            login_clicked = False
            for selector in login_selectors:
                # 🔴 BREAKPOINT 43: Tentando seletor
                # Inspecione: selector
                ...
            
            # 🔴 BREAKPOINT 44: Aguardando OAuth
            page.wait_for_load_state("networkidle")
            
            # 🔴 BREAKPOINT 45: Capturando cookies
            all_cookies = context.cookies()
            
            # 🔴 BREAKPOINT 46: Cookies capturados
            # Inspecione: len(all_cookies), sigef_cookies, govbr_cookies
```

**Linhas sugeridas:** 112, 120, 128, 168, 179, 191, 210, 265, 293

---

## 🎯 Cenários Comuns de Debug

### Cenário 1: "Parcela não encontrada"
**Breakpoints:** 1, 7, 22, 24, 26
- Verifique se o código está correto
- Veja a URL montada
- Inspecione o status_code (404?)

### Cenário 2: "Sessão expirada"
**Breakpoints:** 15, 17, 18, 27, 29, 37
- Veja quando a sessão expira
- Acompanhe o processo de re-auth
- Verifique se storage_state está correto

### Cenário 3: "Download falha"
**Breakpoints:** 10, 22, 25, 26, 30
- Verifique cookies
- Inspecione headers
- Veja content-type da resposta

### Cenário 4: "Memorial retorna HTML"
**Breakpoints:** 32, 34, 35, 36
- Verifique se sessão SIGEF está ativa
- Inspecione content-type
- Veja se precisa re-auth

---

## 🔥 Atalhos no VS Code

1. **Colocar/Remover Breakpoint:** `F9`
2. **Iniciar Debug:** `F5`
3. **Continuar:** `F5`
4. **Step Over:** `F10`
5. **Step Into:** `F11`
6. **Step Out:** `Shift+F11`
7. **Parar Debug:** `Shift+F5`

---

## 📊 Variáveis para Inspecionar

### Na API Route:
- `codigo` - Código da parcela
- `request` - Payload completo
- `sigef_service` - Instância do serviço

### No Service:
- `session` - Dados da sessão
- `session.is_valid()` - Validade
- `session.is_sigef_authenticated` - Auth SIGEF
- `session.govbr_cookies` - Cookies Gov.br
- `session.sigef_cookies` - Cookies SIGEF

### No Client:
- `url` - URL completa da requisição
- `cookies` - Dict de cookies
- `headers` - Headers enviados
- `response.status_code` - Status HTTP
- `response.headers` - Headers da resposta
- `response.content` - Conteúdo (bytes)
- `content_type` - Tipo de conteúdo

### Na Autenticação:
- `page.url` - URL atual do navegador
- `all_cookies` - Todos os cookies capturados
- `sigef_cookies` - Apenas cookies SIGEF
- `storage_state_path` - Caminho do arquivo de estado

---

## 💡 Dicas Pro

1. **Use Conditional Breakpoints:**
   - Clique direito no breakpoint → Add Conditional Breakpoint
   - Exemplo: `codigo == "999a354b-0c33-46a2-bfb3-28213892d541"`

2. **Use Logpoints:**
   - Clique direito → Add Logpoint
   - Exemplo: `"Baixando {tipo.value} da parcela {codigo}"`

3. **Watch Expressions:**
   - Debug sidebar → Watch
   - Adicione: `session.is_valid()`, `len(cookies)`, etc.

4. **Debug Console:**
   - Execute código durante o debug
   - Exemplo: `await self.sessions.load_latest()`

---

## 🚨 Breakpoints Essenciais (Top 5)

Para debug rápido, coloque apenas estes:

1. **src/api/v1/routes/sigef.py:73** - Entrada do download
2. **src/services/sigef_service.py:77** - Validação de sessão
3. **src/services/sigef_service.py:82** - Detecta sessão expirada
4. **src/infrastructure/sigef/client.py:390** - Resposta HTTP recebida
5. **src/infrastructure/sigef/client.py:419** - Verifica content-type

---

*Guia atualizado em 30/12/2024*
