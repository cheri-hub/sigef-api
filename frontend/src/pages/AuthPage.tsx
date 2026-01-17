import { AuthStatus } from '../components';

export function AuthPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Autenticação Gov.br</h1>
      
      <div className="max-w-2xl">
        <AuthStatus />
        
        <div className="mt-6 card bg-yellow-50 border border-yellow-200">
          <h3 className="font-medium text-yellow-800">⚠️ Requisitos</h3>
          <ul className="text-yellow-700 text-sm mt-2 space-y-1">
            <li>• Certificado digital A1 instalado no Windows</li>
            <li>• Google Chrome instalado</li>
            <li>• Conexão com a API</li>
          </ul>
        </div>

        <div className="mt-4 card">
          <h3 className="font-medium mb-3">📋 Como funciona</h3>
          <ol className="text-gray-600 text-sm space-y-2">
            <li><strong>1.</strong> Clique em "Login Gov.br"</li>
            <li><strong>2.</strong> Uma janela do Chrome será aberta automaticamente</li>
            <li><strong>3.</strong> Selecione seu certificado digital quando solicitado</li>
            <li><strong>4.</strong> Aguarde a autenticação ser concluída</li>
            <li><strong>5.</strong> A sessão será salva e você poderá acessar o SIGEF</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
