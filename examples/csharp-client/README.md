# Cliente C# para Gov-Auth API

Cliente simples em C# para testar a API Gov-Auth.

## Requisitos

- .NET 8.0 SDK ou superior

## Executar

```bash
cd examples/csharp-client
dotnet run
```

## Fluxo de Autenticação

1. O programa verifica se há sessão ativa
2. Se não houver, inicia `POST /v1/auth/browser-login`
3. Abre o navegador na URL de autenticação
4. Aguarda o usuário fazer login no Gov.br com certificado digital
5. Após autenticação, faz download dos arquivos da parcela

## Arquivos

- `GovAuthClient.cs` - Classe cliente para a API
- `Program.cs` - Programa de teste
- `GovAuthClient.csproj` - Projeto .NET

## Configuração

Edite as constantes em `Program.cs`:

```csharp
private const string API_BASE_URL = "https://govauth.cherihub.cloud/api";
private const string API_KEY = "sua-api-key-aqui";
```

## Uso como Biblioteca

```csharp
using var client = new GovAuthApiClient(baseUrl, apiKey);

// Verificar status
var status = await client.GetAuthStatusAsync();

// Iniciar login via browser
var login = await client.StartBrowserLoginAsync();
client.OpenBrowserForLogin(login.LoginUrl);

// Aguardar autenticação
await client.WaitForAuthenticationAsync();

// Download de arquivos
var zipBytes = await client.DownloadAllFilesAsync("codigo-parcela");
File.WriteAllBytes("parcela.zip", zipBytes);

// Consulta WFS (não requer auth)
var resultado = await client.ConsultarPorBboxAsync(-47.5, -23.5, -47.0, -23.0);
```
