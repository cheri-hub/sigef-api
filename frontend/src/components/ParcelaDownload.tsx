import { useState } from 'react';
import { Search, Download, Loader2, FileSpreadsheet, FileText, AlertCircle } from 'lucide-react';
import { sigefService } from '../services';
import type { ParcelaInfo, DownloadAllResponse } from '../types';

export function ParcelaDownload() {
  const [codigo, setCodigo] = useState('');
  const [parcela, setParcela] = useState<ParcelaInfo | null>(null);
  const [downloadResult, setDownloadResult] = useState<DownloadAllResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!codigo.trim()) return;
    
    try {
      setLoading(true);
      setError(null);
      setParcela(null);
      setDownloadResult(null);
      const data = await sigefService.getParcelaInfo(codigo.trim());
      setParcela(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar parcela');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadAll = async () => {
    if (!codigo.trim()) return;
    
    try {
      setDownloading(true);
      setError(null);
      setDownloadResult(null);
      const result = await sigefService.downloadAll(codigo.trim());
      setDownloadResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao fazer download');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadFile = async (tipo: 'parcela' | 'vertice' | 'limite') => {
    if (!codigo.trim()) return;
    
    try {
      await sigefService.downloadAndSave(codigo.trim(), tipo);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Erro ao baixar ${tipo}`);
    }
  };

  const handleDownloadMemorial = async () => {
    if (!codigo.trim()) return;
    
    try {
      await sigefService.downloadAndSaveMemorial(codigo.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao baixar memorial descritivo');
    }
  };

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Buscar Parcela</h2>
        
        <div className="flex gap-3">
          <input
            type="text"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Código da parcela (ex: 00000000-0000-0000-0000-000000000000)"
            className="input flex-1 font-mono"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !codigo.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Buscar
          </button>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}
      </div>

      {/* Parcela Info */}
      {parcela && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-govbr-primary" />
            Informações da Parcela
          </h3>
          
          <dl className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <dt className="text-sm text-gray-500">Código</dt>
              <dd className="font-mono text-sm">{parcela.codigo}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Denominação</dt>
              <dd className="font-medium">{parcela.denominacao || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Área (ha)</dt>
              <dd className="font-medium">{parcela.area?.toLocaleString('pt-BR') ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Município</dt>
              <dd className="font-medium">{parcela.municipio || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">UF</dt>
              <dd className="font-medium">{parcela.uf || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Situação</dt>
              <dd>
                <span className={`badge ${
                  parcela.situacao === 'Certificada' ? 'badge-success' : 'badge-warning'
                }`}>
                  {parcela.situacao || '-'}
                </span>
              </dd>
            </div>
          </dl>

          <div className="mt-6 pt-6 border-t">
            <h4 className="font-medium mb-3">Download de CSVs</h4>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleDownloadAll}
                disabled={downloading}
                className="btn-success flex items-center gap-2"
              >
                {downloading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Baixar Todos (Servidor)
              </button>
              
              <button
                onClick={() => handleDownloadFile('parcela')}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Parcela
              </button>
              
              <button
                onClick={() => handleDownloadFile('vertice')}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Vértice
              </button>
              
              <button
                onClick={() => handleDownloadFile('limite')}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Limite
              </button>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t">
            <h4 className="font-medium mb-3">Memorial Descritivo</h4>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleDownloadMemorial}
                className="btn-primary flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                Baixar Memorial (PDF)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Download Result */}
      {downloadResult && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Resultado do Download</h3>
          
          <div className={`p-4 rounded-lg ${
            downloadResult.success ? 'bg-green-50' : 'bg-yellow-50'
          }`}>
            <p className={`font-medium ${
              downloadResult.success ? 'text-green-700' : 'text-yellow-700'
            }`}>
              {downloadResult.success ? '✅ Download concluído!' : '⚠️ Download parcial'}
            </p>
            <p className="text-sm text-gray-600 mt-1">{downloadResult.message}</p>
          </div>

          {downloadResult.arquivos && Object.keys(downloadResult.arquivos).length > 0 && (
            <div className="mt-4">
              <h4 className="font-medium mb-2">Arquivos baixados:</h4>
              <ul className="space-y-2">
                {Object.entries(downloadResult.arquivos).map(([tipo, caminho]) => (
                  <li key={tipo} className="flex items-center gap-2 text-sm">
                    <FileSpreadsheet className="w-4 h-4 text-govbr-primary" />
                    <span className="font-medium capitalize">{tipo}:</span>
                    <span className="font-mono text-gray-600">{caminho}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
