import { useEffect, useState } from 'react';
import { Activity, Server, Clock, CheckCircle, XCircle } from 'lucide-react';
import { authService } from '../services';
import type { SessionStatus } from '../types';

// URL da API - usa variável de ambiente ou caminho relativo
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export function DashboardPage() {
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [apiHealth, setApiHealth] = useState<'loading' | 'online' | 'offline'>('loading');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await authService.getStatus();
        setStatus(data);
        setApiHealth('online');
      } catch {
        setApiHealth('offline');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* API Status */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-full ${
              apiHealth === 'online' ? 'bg-green-100' : 
              apiHealth === 'offline' ? 'bg-red-100' : 'bg-gray-100'
            }`}>
              <Server className={`w-6 h-6 ${
                apiHealth === 'online' ? 'text-govbr-success' : 
                apiHealth === 'offline' ? 'text-govbr-error' : 'text-gray-500'
              }`} />
            </div>
            <div>
              <p className="text-sm text-gray-500">API Backend</p>
              <p className={`font-semibold ${
                apiHealth === 'online' ? 'text-govbr-success' : 
                apiHealth === 'offline' ? 'text-govbr-error' : 'text-gray-500'
              }`}>
                {apiHealth === 'loading' ? 'Verificando...' : 
                 apiHealth === 'online' ? 'Online' : 'Offline'}
              </p>
            </div>
          </div>
        </div>

        {/* Auth Status */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-full ${
              status?.authenticated ? 'bg-green-100' : 'bg-gray-100'
            }`}>
              {status?.authenticated ? (
                <CheckCircle className="w-6 h-6 text-govbr-success" />
              ) : (
                <XCircle className="w-6 h-6 text-gray-400" />
              )}
            </div>
            <div>
              <p className="text-sm text-gray-500">Autenticação</p>
              <p className={`font-semibold ${
                status?.authenticated ? 'text-govbr-success' : 'text-gray-600'
              }`}>
                {status?.authenticated ? 'Autenticado' : 'Não autenticado'}
              </p>
            </div>
          </div>
        </div>

        {/* Session Expiry */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-blue-100">
              <Clock className="w-6 h-6 text-govbr-primary" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Sessão Expira</p>
              <p className="font-semibold text-gray-800">
                {status?.session?.expires_at 
                  ? new Date(status.session.expires_at).toLocaleString('pt-BR')
                  : '-'
                }
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* User Info */}
      {status?.session && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold mb-4">👤 Usuário Logado</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Nome</p>
              <p className="font-medium">{status.session.nome || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">CPF</p>
              <p className="font-medium font-mono">{status.session.cpf || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Gov.br</p>
              <p className="font-medium">
                {status.session.is_govbr_authenticated ? '✅ OK' : '❌'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">SIGEF</p>
              <p className="font-medium">
                {status.session.is_sigef_authenticated ? '✅ OK' : '❌'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Ações Rápidas
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <a 
            href="/auth"
            className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium">🔐 Autenticação</h3>
            <p className="text-sm text-gray-500 mt-1">
              Login/logout via Gov.br com certificado digital
            </p>
          </a>
          
          <a 
            href="/download"
            className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium">📥 Download Individual</h3>
            <p className="text-sm text-gray-500 mt-1">
              Baixar CSVs de uma parcela específica
            </p>
          </a>
          
          <a 
            href="/batch"
            className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium">📦 Download em Lote</h3>
            <p className="text-sm text-gray-500 mt-1">
              Processar múltiplas parcelas de uma vez
            </p>
          </a>
        </div>
      </div>

      {/* Info */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-medium text-blue-800">ℹ️ Sobre o Sistema</h3>
        <p className="text-blue-700 text-sm mt-2">
          Este frontend permite testar a API de autenticação Gov.br e integração com o SIGEF INCRA.
          O login é realizado via certificado digital A1, que abre uma janela do Chrome para autenticação.
        </p>
        <div className="mt-3 flex gap-4 text-sm">
          <a 
            href={`${API_BASE_URL}/docs`}
            target="_blank" 
            rel="noopener noreferrer"
            className="text-govbr-primary hover:underline"
          >
            📖 Swagger API
          </a>
          <a 
            href={`${API_BASE_URL}/redoc`}
            target="_blank" 
            rel="noopener noreferrer"
            className="text-govbr-primary hover:underline"
          >
            📚 ReDoc
          </a>
        </div>
      </div>
    </div>
  );
}
