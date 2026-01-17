"""
Testes rápidos da API Gov.br Auth

Script simples para testar endpoints sem interface interativa.
Útil para CI/CD e testes automatizados.

Uso:
    python test_api_quick.py
"""

import asyncio
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Configuração
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

# Código de parcela de exemplo
EXEMPLO_CODIGO = "999a354b-0c33-46a2-bfb3-28213892d541"


async def test_health():
    """Testa health check."""
    console.print("🏥 [cyan]Health Check[/cyan]")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                console.print(f"   ✓ Status: [green]{data.get('status')}[/green]")
                console.print(f"   ✓ Version: {data.get('version')}")
                return True
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def test_auth_status():
    """Testa status de autenticação."""
    console.print("🔐 [cyan]Auth Status[/cyan]")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_V1_URL}/auth/status")
            if response.status_code == 200:
                data = response.json()
                is_auth = data.get("authenticated", False)
                
                if is_auth:
                    session = data.get("session", {})
                    console.print(f"   ✓ Autenticado: [green]Sim[/green]")
                    console.print(f"   ✓ CPF: {session.get('cpf')}")
                    console.print(f"   ✓ Nome: {session.get('nome')}")
                    console.print(f"   ✓ Gov.br: {'✓' if session.get('is_govbr_authenticated') else '✗'}")
                    console.print(f"   ✓ SIGEF: {'✓' if session.get('is_sigef_authenticated') else '✗'}")
                else:
                    console.print(f"   ⚠ Não autenticado")
                
                return is_auth
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def test_parcela_info(codigo: str = EXEMPLO_CODIGO):
    """Testa busca de parcela."""
    console.print(f"📍 [cyan]Parcela Info[/cyan] ({codigo[:8]}...)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_V1_URL}/sigef/parcela/{codigo}")
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"   ✓ Código: {data.get('codigo')}")
                console.print(f"   ✓ Denominação: {data.get('denominacao')}")
                console.print(f"   ✓ Área: {data.get('area_ha')} ha")
                console.print(f"   ✓ Município: {data.get('municipio')}/{data.get('uf')}")
                console.print(f"   ✓ Situação: {data.get('situacao')}")
                return True
            elif response.status_code == 401:
                console.print(f"   ⚠ [yellow]Não autenticado - faça login primeiro[/yellow]")
                return False
            elif response.status_code == 404:
                console.print(f"   ✗ [red]Parcela não encontrada[/red]")
                return False
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def test_download_csv(codigo: str = EXEMPLO_CODIGO, tipo: str = "parcela"):
    """Testa download de CSV."""
    console.print(f"📥 [cyan]Download CSV[/cyan] ({tipo})")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            payload = {"codigo": codigo, "tipo": tipo}
            response = await client.post(f"{API_V1_URL}/sigef/download", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    console.print(f"   ✓ Arquivo: {data.get('arquivo')}")
                    console.print(f"   ✓ Tamanho: {data.get('tamanho_bytes')} bytes")
                    return True
                else:
                    console.print(f"   ✗ [red]Falha: {data.get('message')}[/red]")
                    return False
            elif response.status_code == 401:
                console.print(f"   ⚠ [yellow]Não autenticado[/yellow]")
                return False
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def test_download_memorial(codigo: str = EXEMPLO_CODIGO):
    """Testa download de memorial."""
    console.print(f"📄 [cyan]Download Memorial[/cyan]")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(f"{API_V1_URL}/sigef/memorial/{codigo}")
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                size = len(response.content)
                
                if "pdf" in content_type:
                    console.print(f"   ✓ PDF recebido: {size} bytes")
                    
                    # Salva para verificação
                    filename = f"test_{codigo[:8]}_memorial.pdf"
                    Path(filename).write_bytes(response.content)
                    console.print(f"   ✓ Salvo: {filename}")
                    return True
                else:
                    console.print(f"   ✗ [red]Content-Type inválido: {content_type}[/red]")
                    return False
            elif response.status_code == 401:
                console.print(f"   ⚠ [yellow]Não autenticado[/yellow]")
                return False
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def test_download_all(codigo: str = EXEMPLO_CODIGO):
    """Testa download de todos os CSVs."""
    console.print(f"📦 [cyan]Download All[/cyan]")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            payload = {"codigo": codigo}
            response = await client.post(f"{API_V1_URL}/sigef/download/all", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    arquivos = data.get("arquivos", {})
                    console.print(f"   ✓ {len(arquivos)} arquivos baixados")
                    for tipo, path in arquivos.items():
                        console.print(f"      • {tipo}: {Path(path).name}")
                    return True
                else:
                    console.print(f"   ✗ [red]Falha: {data.get('message')}[/red]")
                    return False
            elif response.status_code == 401:
                console.print(f"   ⚠ [yellow]Não autenticado[/yellow]")
                return False
            else:
                console.print(f"   ✗ [red]HTTP {response.status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"   ✗ [red]Erro: {e}[/red]")
            return False


async def run_all_tests():
    """Executa todos os testes."""
    console.print(Panel.fit(
        "[bold cyan]🧪 Testes Rápidos - Gov.br Auth API[/bold cyan]\n"
        f"Base URL: [yellow]{API_BASE_URL}[/yellow]",
        border_style="cyan"
    ))
    console.print()
    
    results = {
        "health": await test_health(),
        "auth_status": await test_auth_status(),
    }
    
    console.print()
    
    # Se não estiver autenticado, pula testes que precisam de auth
    if not results["auth_status"]:
        console.print("[yellow]⚠️  Sessão não autenticada - alguns testes serão pulados[/yellow]")
        console.print("[yellow]   Execute: python debug_api.py (opção 3) para fazer login[/yellow]")
    else:
        results["parcela_info"] = await test_parcela_info()
        console.print()
        
        results["download_csv"] = await test_download_csv()
        console.print()
        
        results["download_memorial"] = await test_download_memorial()
        console.print()
        
        results["download_all"] = await test_download_all()
    
    console.print()
    
    # Resumo
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        console.print(f"[bold green]✓ Todos os testes passaram ({passed}/{total})[/bold green]")
        return 0
    else:
        console.print(f"[bold yellow]⚠ {passed}/{total} testes passaram[/bold yellow]")
        return 1


async def run_single_test(test_name: str):
    """Executa um teste específico."""
    tests = {
        "health": test_health,
        "auth": test_auth_status,
        "parcela": test_parcela_info,
        "csv": test_download_csv,
        "memorial": test_download_memorial,
        "all": test_download_all,
    }
    
    if test_name not in tests:
        console.print(f"[red]Teste desconhecido: {test_name}[/red]")
        console.print(f"Disponíveis: {', '.join(tests.keys())}")
        return 1
    
    result = await tests[test_name]()
    return 0 if result else 1


async def main():
    """Função principal."""
    if len(sys.argv) > 1:
        # Teste específico
        test_name = sys.argv[1]
        return await run_single_test(test_name)
    else:
        # Todos os testes
        return await run_all_tests()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[cyan]Interrompido pelo usuário[/cyan]")
        sys.exit(130)
