import { useState } from 'react';
import { Download, Loader2, FileText, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { sigefService } from '../services';
import type { BatchDownloadResponse } from '../types';

export function BatchDownload() {
  const [codigosText, setCodigosText] = useState('');
  const [codigos, setCodigos] = useState<string[]>([]);
  const [result, setResult] = useState<BatchDownloadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseAndAddCodigos = () => {
    const parsed = codigosText
      .split(/[\n,;]+/)
      .map(c => c.trim())
      .filter(c => c.length > 0 && !codigos.includes(c));
    
    if (parsed.length > 0) {
      setCodigos([...codigos, ...parsed]);
      setCodigosText('');
    }
  };

  const removeCodigo = (codigo: string) => {
    setCodigos(codigos.filter(c => c !== codigo));
  };

  const clearAll = () => {
    setCodigos([]);
    setResult(null);
    setError(null);
  };

  const handleDownload = async () => {
    if (codigos.length === 0) return;

    try {
      setLoading(true);
      setError(null);
      setResult(null);
      const response = await sigefService.downloadBatch({ codigos });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao fazer download em lote');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Input */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Download em Lote</h2>
        <p className="text-gray-600 mb-4">
          Adicione múltiplos códigos de parcela para download simultâneo.
          Separe por vírgula, ponto e vírgula ou nova linha.
        </p>

        <div className="flex gap-3">
          <textarea
            value={codigosText}
            onChange={(e) => setCodigosText(e.target.value)}
            placeholder="Cole os códigos aqui..."
            className="input flex-1 h-24 font-mono text-sm"
          />
          <button
            onClick={parseAndAddCodigos}
            disabled={!codigosText.trim()}
            className="btn-primary self-start"
          >
            Adicionar
          </button>
        </div>
      </div>

      {/* Lista de códigos */}
      {codigos.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">
              Parcelas Selecionadas ({codigos.length})
            </h3>
            <button
              onClick={clearAll}
              className="text-red-600 hover:text-red-800 flex items-center gap-1 text-sm"
            >
              <Trash2 className="w-4 h-4" />
              Limpar tudo
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left p-2">#</th>
                  <th className="text-left p-2">Código</th>
                  <th className="text-right p-2">Ação</th>
                </tr>
              </thead>
              <tbody>
                {codigos.map((codigo, idx) => (
                  <tr key={codigo} className="border-t hover:bg-gray-50">
                    <td className="p-2 text-gray-500">{idx + 1}</td>
                    <td className="p-2 font-mono">{codigo}</td>
                    <td className="p-2 text-right">
                      <button
                        onClick={() => removeCodigo(codigo)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 pt-4 border-t">
            <button
              onClick={handleDownload}
              disabled={loading || codigos.length === 0}
              className="btn-success flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {loading ? 'Processando...' : `Baixar ${codigos.length} parcela(s)`}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Resultado */}
      {result && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Resultado do Processamento</h3>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-blue-600">{result.total}</p>
              <p className="text-sm text-blue-600">Total</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-govbr-success">{result.sucesso}</p>
              <p className="text-sm text-govbr-success">Sucesso</p>
            </div>
            <div className="bg-red-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-govbr-error">{result.falhas}</p>
              <p className="text-sm text-govbr-error">Falhas</p>
            </div>
          </div>

          <div className="space-y-2">
            {Object.entries(result.resultados).map(([codigo, arquivos]) => {
              const hasError = 'error' in arquivos;
              const fileCount = Object.keys(arquivos).filter(k => k !== 'error').length;
              
              return (
                <div
                  key={codigo}
                  className={`flex items-center gap-3 p-3 rounded-lg ${
                    hasError ? 'bg-red-50' : 'bg-green-50'
                  }`}
                >
                  {hasError ? (
                    <XCircle className="w-5 h-5 text-govbr-error" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-govbr-success" />
                  )}
                  <span className="font-mono text-sm flex-1">{codigo}</span>
                  {!hasError && (
                    <span className="text-sm text-gray-500">
                      {fileCount} arquivo(s)
                    </span>
                  )}
                  {hasError && (
                    <span className="text-sm text-red-600">
                      {arquivos.error}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Info */}
      {codigos.length === 0 && !result && (
        <div className="card bg-blue-50 border border-blue-200">
          <div className="flex items-start gap-3">
            <FileText className="w-6 h-6 text-blue-600 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-blue-800">Dica</h4>
              <p className="text-blue-700 text-sm mt-1">
                Você pode copiar códigos diretamente de uma planilha Excel.
                O sistema aceita separação por vírgula, ponto e vírgula ou quebra de linha.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
