using System;
using System.IO;
using System.Threading.Tasks;

namespace GovAuthClient
{
    class Program
    {
        // Configuração
        private const string API_BASE_URL = "https://govauth.cherihub.cloud/api";
        private const string API_KEY = "554a8a59e662237b25231bba27e659a0dae67d8224e66ccb34ee9381e13aee5f";

        static async Task Main(string[] args)
        {
            Console.WriteLine("===========================================");
            Console.WriteLine("     Gov-Auth API - Cliente de Teste C#    ");
            Console.WriteLine("===========================================\n");

            using var client = new GovAuthApiClient(API_BASE_URL, API_KEY);

            try
            {
                // 1. Verificar status atual
                Console.WriteLine("[1] Verificando status da sessão...");
                var status = await client.GetAuthStatusAsync();
                Console.WriteLine($"    Autenticado: {status.Authenticated}");
                Console.WriteLine($"    Mensagem: {status.Message}\n");

                // 2. Se não autenticado, iniciar browser-login
                if (!status.Authenticated)
                {
                    Console.WriteLine("[2] Iniciando autenticação via browser...");
                    var loginResponse = await client.StartBrowserLoginAsync();
                    
                    Console.WriteLine($"    Session ID: {loginResponse.SessionId}");
                    Console.WriteLine($"    Auth Token: {loginResponse.AuthToken?.Substring(0, 20)}...\n");

                    // 3. Abrir navegador
                    client.OpenBrowserForLogin(loginResponse.LoginUrl);

                    // 4. Aguardar autenticação
                    Console.WriteLine("[3] Aguardando conclusão da autenticação...");
                    var authenticated = await client.WaitForAuthenticationAsync(timeoutSeconds: 300);

                    if (!authenticated)
                    {
                        Console.WriteLine("\n❌ Falha na autenticação. Encerrando.");
                        return;
                    }
                }

                // 5. Testar download
                Console.WriteLine("\n[4] Testando download de arquivos...");
                
                // Código de exemplo - substitua por um código real de parcela
                var codigoParcela = "f7fd7a57-4858-4453-b132-74e74dee2101";
                
                Console.Write($"    Código da parcela [{codigoParcela}]: ");
                var input = Console.ReadLine();
                if (!string.IsNullOrWhiteSpace(input))
                {
                    codigoParcela = input.Trim();
                }

                try
                {
                    var zipBytes = await client.DownloadAllFilesAsync(codigoParcela);
                    
                    // Salvar arquivo
                    var fileName = $"parcela_{codigoParcela}.zip";
                    await File.WriteAllBytesAsync(fileName, zipBytes);
                    Console.WriteLine($"    ✓ Arquivo salvo: {fileName}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"    ❌ Erro no download: {ex.Message}");
                }

                // 6. Testar consulta WFS (não requer auth)
                Console.WriteLine("\n[5] Testando consulta WFS (pública)...");
                try
                {
                    // Coordenadas de exemplo (região no Brasil)
                    var resultado = await client.ConsultarPorBboxAsync(-47.5, -23.5, -47.0, -23.0);
                    Console.WriteLine($"    Resultado: {resultado.Substring(0, Math.Min(200, resultado.Length))}...");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"    ❌ Erro na consulta: {ex.Message}");
                }

                Console.WriteLine("\n===========================================");
                Console.WriteLine("              Teste Concluído!             ");
                Console.WriteLine("===========================================");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n❌ Erro: {ex.Message}");
                Console.WriteLine(ex.StackTrace);
            }

            Console.WriteLine("\nPressione qualquer tecla para sair...");
            Console.ReadKey();
        }
    }
}
