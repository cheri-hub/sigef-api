"""
Script de Debug da API Gov.br Auth

Permite testar todos os endpoints da API de forma interativa.
Útil para desenvolvimento e troubleshooting.

Uso:
    python debug_api.py
"""

import asyncio
import json
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.syntax import Syntax

console = Console()

# Configuração da API
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"


class APIDebugger:
    """Debugger interativo para a API."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.session_data = None
    
    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()
    
    def print_response(self, response: httpx.Response):
        """Imprime resposta HTTP de forma formatada."""
        # Status
        status_color = "green" if response.status_code < 300 else "yellow" if response.status_code < 400 else "red"
        console.print(f"\n[{status_color}]Status: {response.status_code}[/{status_color}]")
        
        # Headers importantes
        console.print("\n[bold]Headers:[/bold]")
        important_headers = ["content-type", "content-length", "set-cookie"]
        for header in important_headers:
            if header in response.headers:
                console.print(f"  {header}: {response.headers[header]}")
        
        # Body
        try:
            if "application/json" in response.headers.get("content-type", ""):
                data = response.json()
                syntax = Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json", theme="monokai")
                console.print("\n[bold]Body:[/bold]")
                console.print(syntax)
            elif "text" in response.headers.get("content-type", ""):
                console.print("\n[bold]Body:[/bold]")
                console.print(response.text[:500])
            else:
                console.print(f"\n[bold]Body:[/bold] Binary data ({len(response.content)} bytes)")
        except Exception as e:
            console.print(f"\n[red]Erro ao decodificar resposta: {e}[/red]")
    
    async def test_health(self):
        """Testa endpoint de health check."""
        console.print(Panel("[bold cyan]Health Check[/bold cyan]"))
        
        try:
            response = await self.client.get(f"{API_BASE_URL}/health")
            self.print_response(response)
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_auth_status(self):
        """Testa endpoint de status de autenticação."""
        console.print(Panel("[bold cyan]Auth Status[/bold cyan]"))
        
        try:
            response = await self.client.get(f"{API_V1_URL}/auth/status")
            self.print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("session"):
                    self.session_data = data["session"]
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_auth_login(self):
        """Testa endpoint de login."""
        console.print(Panel("[bold cyan]Auth Login[/bold cyan]"))
        console.print("[yellow]⚠️  Isso abrirá o navegador para autenticação![/yellow]")
        
        if not Confirm.ask("Deseja continuar?"):
            return
        
        headless = Confirm.ask("Usar modo headless?", default=False)
        
        try:
            payload = {"headless": headless}
            response = await self.client.post(
                f"{API_V1_URL}/auth/login",
                json=payload,
            )
            self.print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("session"):
                    self.session_data = data["session"]
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_auth_logout(self):
        """Testa endpoint de logout."""
        console.print(Panel("[bold cyan]Auth Logout[/bold cyan]"))
        
        try:
            response = await self.client.post(f"{API_V1_URL}/auth/logout")
            self.print_response(response)
            self.session_data = None
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_parcela_info(self):
        """Testa endpoint de informações da parcela."""
        console.print(Panel("[bold cyan]Parcela Info[/bold cyan]"))
        
        codigo = Prompt.ask(
            "Código da parcela",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        
        try:
            response = await self.client.get(f"{API_V1_URL}/sigef/parcela/{codigo}")
            self.print_response(response)
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_download_csv(self):
        """Testa endpoint de download de CSV."""
        console.print(Panel("[bold cyan]Download CSV[/bold cyan]"))
        
        codigo = Prompt.ask(
            "Código da parcela",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        tipo = Prompt.ask(
            "Tipo",
            choices=["parcela", "vertice", "limite"],
            default="parcela"
        )
        
        try:
            payload = {"codigo": codigo, "tipo": tipo}
            response = await self.client.post(
                f"{API_V1_URL}/sigef/download",
                json=payload,
            )
            self.print_response(response)
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_download_all(self):
        """Testa endpoint de download de todos os CSVs."""
        console.print(Panel("[bold cyan]Download All CSVs[/bold cyan]"))
        
        codigo = Prompt.ask(
            "Código da parcela",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        
        try:
            payload = {"codigo": codigo}
            response = await self.client.post(
                f"{API_V1_URL}/sigef/download/all",
                json=payload,
            )
            self.print_response(response)
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_download_memorial(self):
        """Testa endpoint de download do memorial."""
        console.print(Panel("[bold cyan]Download Memorial (PDF)[/bold cyan]"))
        
        codigo = Prompt.ask(
            "Código da parcela",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        
        try:
            response = await self.client.get(f"{API_V1_URL}/sigef/memorial/{codigo}")
            self.print_response(response)
            
            if response.status_code == 200:
                save = Confirm.ask("Salvar PDF?", default=True)
                if save:
                    filename = f"{codigo}_memorial.pdf"
                    Path(filename).write_bytes(response.content)
                    console.print(f"[green]✓ Salvo: {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_download_file(self):
        """Testa endpoint de download direto de arquivo."""
        console.print(Panel("[bold cyan]Download File (Direct)[/bold cyan]"))
        
        codigo = Prompt.ask(
            "Código da parcela",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        tipo = Prompt.ask(
            "Tipo",
            choices=["parcela", "vertice", "limite"],
            default="parcela"
        )
        
        try:
            response = await self.client.get(
                f"{API_V1_URL}/sigef/download/{codigo}/{tipo}"
            )
            self.print_response(response)
            
            if response.status_code == 200:
                save = Confirm.ask("Salvar CSV?", default=True)
                if save:
                    filename = f"{codigo}_{tipo}.csv"
                    Path(filename).write_bytes(response.content)
                    console.print(f"[green]✓ Salvo: {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def test_batch_download(self):
        """Testa endpoint de download em lote."""
        console.print(Panel("[bold cyan]Batch Download[/bold cyan]"))
        
        codigos_input = Prompt.ask(
            "Códigos (separados por vírgula)",
            default="999a354b-0c33-46a2-bfb3-28213892d541"
        )
        codigos = [c.strip() for c in codigos_input.split(",")]
        
        tipos_input = Prompt.ask(
            "Tipos (separados por vírgula, ou vazio para todos)",
            default=""
        )
        tipos = [t.strip() for t in tipos_input.split(",") if t.strip()] if tipos_input else None
        
        try:
            payload = {"codigos": codigos}
            if tipos:
                payload["tipos"] = tipos
            
            response = await self.client.post(
                f"{API_V1_URL}/sigef/download/batch",
                json=payload,
            )
            self.print_response(response)
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    
    async def show_session_info(self):
        """Mostra informações da sessão atual."""
        if not self.session_data:
            console.print("[yellow]Nenhuma sessão ativa[/yellow]")
            return
        
        table = Table(title="Sessão Atual")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor", style="white")
        
        table.add_row("Session ID", self.session_data.get("session_id", "N/A"))
        table.add_row("CPF", self.session_data.get("cpf", "N/A"))
        table.add_row("Nome", self.session_data.get("nome", "N/A"))
        table.add_row("Gov.br Auth", "✓" if self.session_data.get("is_govbr_authenticated") else "✗")
        table.add_row("SIGEF Auth", "✓" if self.session_data.get("is_sigef_authenticated") else "✗")
        table.add_row("Válida", "✓" if self.session_data.get("is_valid") else "✗")
        table.add_row("Criada em", self.session_data.get("created_at", "N/A"))
        table.add_row("Expira em", self.session_data.get("expires_at", "N/A"))
        
        console.print(table)
    
    def show_menu(self):
        """Mostra menu principal."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]🐍 Gov.br Auth API - Debug Tool[/bold cyan]\n"
            f"API Base URL: [yellow]{API_BASE_URL}[/yellow]",
            border_style="cyan"
        ))
        
        table = Table(show_header=False, box=None)
        table.add_column("Opção", style="cyan", width=4)
        table.add_column("Descrição", style="white")
        
        # Health & Auth
        table.add_row("", "[bold]HEALTH & AUTH[/bold]")
        table.add_row("1", "Health Check")
        table.add_row("2", "Auth Status")
        table.add_row("3", "Login (Gov.br)")
        table.add_row("4", "Logout")
        table.add_row("5", "Ver Sessão Atual")
        
        # SIGEF
        table.add_row("", "")
        table.add_row("", "[bold]SIGEF[/bold]")
        table.add_row("6", "Buscar Parcela")
        table.add_row("7", "Download CSV (Individual)")
        table.add_row("8", "Download All CSVs")
        table.add_row("9", "Download Memorial (PDF)")
        table.add_row("10", "Download File (Direto)")
        table.add_row("11", "Batch Download")
        
        # Outros
        table.add_row("", "")
        table.add_row("0", "Sair")
        
        console.print(table)
        console.print()


async def main():
    """Loop principal do debugger."""
    debugger = APIDebugger()
    
    try:
        while True:
            debugger.show_menu()
            
            choice = Prompt.ask(
                "Escolha uma opção",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
            )
            
            console.print()
            
            if choice == "0":
                console.print("[cyan]👋 Até logo![/cyan]")
                break
            elif choice == "1":
                await debugger.test_health()
            elif choice == "2":
                await debugger.test_auth_status()
            elif choice == "3":
                await debugger.test_auth_login()
            elif choice == "4":
                await debugger.test_auth_logout()
            elif choice == "5":
                await debugger.show_session_info()
            elif choice == "6":
                await debugger.test_parcela_info()
            elif choice == "7":
                await debugger.test_download_csv()
            elif choice == "8":
                await debugger.test_download_all()
            elif choice == "9":
                await debugger.test_download_memorial()
            elif choice == "10":
                await debugger.test_download_file()
            elif choice == "11":
                await debugger.test_batch_download()
            
            console.print()
            input("Pressione ENTER para continuar...")
    
    finally:
        await debugger.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[cyan]Interrompido pelo usuário[/cyan]")
