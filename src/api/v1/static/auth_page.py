"""
Página HTML de autenticação que roda no navegador do cliente.

Este arquivo é servido para que o usuário faça login via Gov.br
enquanto a API roda em Docker ou servidor remoto.
"""

HTML_AUTH_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autenticação Gov.br - API Gov-Auth</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            max-width: 500px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .status {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .status.info {
            background: #e3f2fd;
            color: #1976d2;
            border-left: 4px solid #1976d2;
        }
        
        .status.success {
            background: #e8f5e9;
            color: #388e3c;
            border-left: 4px solid #388e3c;
        }
        
        .status.error {
            background: #ffebee;
            color: #d32f2f;
            border-left: 4px solid #d32f2f;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        
        button {
            flex: 1;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5568d3;
        }
        
        .btn-secondary {
            background: #e0e0e0;
            color: #333;
        }
        
        .btn-secondary:hover {
            background: #d0d0d0;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .timer {
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 20px;
        }
        
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Autenticação Gov.br</h1>
        <p class="subtitle">API Gov-Auth - Autenticação Remota</p>
        
        <div id="status" class="status info" style="display: none;"></div>
        
        <div id="loading">
            <div class="spinner"></div>
            <p style="text-align: center; color: #666; margin-top: 15px;">
                Carregando página de autenticação...
            </p>
        </div>
        
        <div id="authenticated" style="display: none;">
            <div class="status success">
                <strong>✓ Autenticado com sucesso!</strong>
                <p style="margin-top: 10px;">Seus dados foram enviados para a API.</p>
            </div>
            <p style="text-align: center; color: #666; margin-top: 20px;">
                Você pode fechar esta janela.
            </p>
        </div>
        
        <div id="error" style="display: none;">
            <div class="status error">
                <strong>✗ Erro na Autenticação</strong>
                <p id="error-message" style="margin-top: 10px;"></p>
            </div>
            <div class="button-group">
                <button class="btn-secondary" onclick="location.reload()">Tentar Novamente</button>
                <button class="btn-secondary" onclick="window.close()">Fechar</button>
            </div>
        </div>
        
        <div class="timer">
            <p id="timer">Timeout: <span id="timeout-count">10</span>s</p>
        </div>
    </div>
    
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const authToken = urlParams.get('token');
        const apiBase = window.location.origin;
        
        if (!authToken) {
            showError('Token de autenticação não fornecido');
        } else {
            initializeAuth();
        }
        
        function showStatus(message, type = 'info') {
            const elem = document.getElementById('status');
            elem.textContent = message;
            elem.className = `status ${type}`;
            elem.style.display = 'block';
        }
        
        function showError(message) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'block';
            document.getElementById('error-message').textContent = message;
        }
        
        function showSuccess() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('authenticated').style.display = 'block';
        }
        
        async function initializeAuth() {
            showStatus('Estabelecendo conexão com Gov.br...', 'info');
            
            try {
                // Aguarda um pouco para que a página de login do Gov.br carregue
                // Em produção, isso seria feito via iframe ou popup
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                showStatus('Redirecionando para Gov.br...', 'info');
                
                // Redireciona para Gov.br
                // Em uma implementação real, isso seria feito via OAuth2 flow
                window.location.href = 'https://sso.acesso.gov.br/';
                
            } catch (error) {
                showError(`Erro: ${error.message}`);
            }
        }
        
        // Contador de timeout
        let timeout = 600; // 10 minutos em segundos
        setInterval(() => {
            timeout--;
            document.getElementById('timeout-count').textContent = Math.max(0, Math.floor(timeout / 60));
            
            if (timeout <= 0) {
                showError('Sessão expirada. Tente fazer login novamente.');
            }
        }, 1000);
    </script>
</body>
</html>
"""
