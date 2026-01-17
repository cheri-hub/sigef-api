import { useState } from 'react';
import { AlertCircle, Download, Loader2, Map, Search, FileText, Server } from 'lucide-react';
import { consultaService, sigefService } from '../services';
import ParcelaDetalhesModal from '../components/ParcelaDetalhesModal';
import type {
  BoundingBox,
  ConsultaResponse,
  ImovelResponse,
  LayerType,
  ServerType,
} from '../types';

const LAYER_OPTIONS: { value: LayerType; label: string }[] = [
  { value: 'sigef_particular', label: 'SIGEF Particular' },
  { value: 'sigef_publico', label: 'SIGEF Público' },
  { value: 'snci_privado', label: 'SNCI Privado' },
  { value: 'snci_publico', label: 'SNCI Público' },
  { value: 'assentamentos', label: 'Assentamentos' },
  { value: 'quilombolas', label: 'Quilombolas' },
  { value: 'pendentes_titulacao', label: 'Pendentes de Titulação' },
];

const SERVER_OPTIONS: { value: ServerType; label: string }[] = [
  { value: 'auto', label: 'Automático (INCRA → GeoOne)' },
  { value: 'incra', label: 'INCRA (por UF)' },
  { value: 'geoone', label: 'GeoOne (nacional)' },
];

export default function ConsultaPage() {
  // Estados do formulário
  const [bbox, setBbox] = useState<BoundingBox>({
    x_min: -49.17,
    y_min: -25.17,
    x_max: -49.15,
    y_max: -25.14,
  });
  // Fixo como 'auto' para sempre buscar em todas as camadas automaticamente
  const servidor: ServerType = 'auto';
  const camada: LayerType = 'sigef_particular'; // Ignorado quando servidor='auto'
  const [limite, setLimite] = useState(100);

  // Estados da consulta
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ConsultaResponse | null>(null);
  const [selectedImovel, setSelectedImovel] = useState<ImovelResponse | null>(null);
  
  // Estados do modal de detalhes
  const [detalhesModal, setDetalhesModal] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleConsultar = async () => {
    setIsLoading(true);
    setError(null);
    setResultado(null);
    setSelectedImovel(null);

    try {
      const result = await consultaService.consultarImoveis({
        bbox,
        camada,
        servidor,
        limite,
      });

      setResultado(result);

      if (!result.sucesso) {
        setError(result.mensagem);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao realizar consulta');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadGeoJSON = () => {
    consultaService.downloadGeoJSON(bbox, camada, servidor, limite);
  };

  const handleDownloadParcela = async (codigo: string, tipo: 'parcela' | 'vertice' | 'limite') => {
    try {
      await sigefService.downloadAndSave(codigo, tipo);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Erro ao baixar ${tipo}`);
    }
  };

  const handleDownloadMemorial = async (codigo: string) => {
    try {
      await sigefService.downloadAndSaveMemorial(codigo);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao baixar memorial descritivo');
    }
  };

  const handleDownloadAll = async (codigo: string) => {
    try {
      await sigefService.downloadAll(codigo);
      // Opcional: mostrar mensagem de sucesso
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao baixar todos os arquivos');
    }
  };
  
  const handleOpenDetalhes = async (codigo: string) => {
    try {
      const detalhes = await sigefService.getDetalhes(codigo);
      setDetalhesModal(detalhes);
      setIsModalOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar detalhes');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center">
            <Map className="h-8 w-8 text-green-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Consulta de Imóveis INCRA/SIGEF
              </h1>
              <p className="text-sm text-gray-600">
                Consulte imóveis certificados por área geográfica (bounding box)
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Painel de Consulta */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Parâmetros de Consulta
              </h2>

              {/* Bounding Box */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bounding Box (WGS84)
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-600">Long. Mín (Oeste)</label>
                      <input
                        type="number"
                        step="0.001"
                        value={bbox.x_min}
                        onChange={(e) => setBbox({ ...bbox, x_min: parseFloat(e.target.value) })}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-600">Lat. Mín (Sul)</label>
                      <input
                        type="number"
                        step="0.001"
                        value={bbox.y_min}
                        onChange={(e) => setBbox({ ...bbox, y_min: parseFloat(e.target.value) })}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-600">Long. Máx (Leste)</label>
                      <input
                        type="number"
                        step="0.001"
                        value={bbox.x_max}
                        onChange={(e) => setBbox({ ...bbox, x_max: parseFloat(e.target.value) })}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-600">Lat. Máx (Norte)</label>
                      <input
                        type="number"
                        step="0.001"
                        value={bbox.y_max}
                        onChange={(e) => setBbox({ ...bbox, y_max: parseFloat(e.target.value) })}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Informação sobre busca automática */}
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                  <div className="flex items-start">
                    <Map className="h-5 w-5 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-blue-900 mb-2">Busca Automática em Todas as Camadas</p>
                      <p className="text-xs text-blue-700 mb-1">
                        A consulta será realizada automaticamente nas seguintes camadas:
                      </p>
                      <ol className="text-xs text-blue-700 ml-4 space-y-0.5 list-decimal">
                        <li>SIGEF Particular</li>
                        <li>SIGEF Público</li>
                        <li>SNCI Privado</li>
                        <li>SNCI Público</li>
                        <li>Assentamentos</li>
                        <li>Quilombolas</li>
                        <li>Pendentes de Titulação</li>
                      </ol>
                    </div>
                  </div>
                </div>

                {/* Informação sobre servidores */}
                <div className="bg-green-50 border border-green-200 rounded-md p-3">
                  <div className="flex items-start">
                    <Server className="h-5 w-5 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-green-900 mb-2">Estratégia de Fallback entre Servidores</p>
                      <p className="text-xs text-green-700 mb-1">
                        Para cada camada, a busca segue a seguinte ordem:
                      </p>
                      <ol className="text-xs text-green-700 ml-4 space-y-0.5 list-decimal">
                        <li><span className="font-medium">INCRA/SIGEF</span> (por UF) - Tentativa inicial</li>
                        <li><span className="font-medium">GeoOne</span> (nacional) - Usado automaticamente se o INCRA falhar</li>
                      </ol>
                    </div>
                  </div>
                </div>

                {/* Limite */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Limite de Resultados
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    value={limite}
                    onChange={(e) => setLimite(parseInt(e.target.value))}
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
                  />
                </div>

                {/* Botões */}
                <div className="flex gap-2">
                  <button
                    onClick={handleConsultar}
                    disabled={isLoading}
                    className="flex-1 flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="animate-spin h-4 w-4 mr-2" />
                        Consultando...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4 mr-2" />
                        Consultar
                      </>
                    )}
                  </button>

                  {resultado && (
                    <button
                      onClick={handleDownloadGeoJSON}
                      className="px-4 py-3 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      title="Download GeoJSON"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Info da Consulta */}
              {resultado && (
                <div className="mt-4 p-3 bg-gray-50 rounded-md">
                  <p className="text-xs text-gray-600">
                    <strong>{resultado.total}</strong> imóveis encontrados
                  </p>
                  <p className="text-xs text-gray-500">
                    Servidor: {resultado.servidor_utilizado} | 
                    Tempo: {resultado.tempo_resposta_ms}ms
                  </p>
                </div>
              )}

              {/* Erro */}
              {error && (
                <div className="mt-4 rounded-md bg-red-50 p-4">
                  <div className="flex">
                    <AlertCircle className="h-5 w-5 text-red-400" />
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">Erro</h3>
                      <p className="mt-1 text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Painel de Resultados */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">
                  Resultados da Consulta
                </h2>
              </div>

              {!resultado && !isLoading && (
                <div className="p-12 text-center text-gray-500">
                  <Map className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p>Configure os parâmetros e clique em Consultar</p>
                </div>
              )}

              {resultado && resultado.imoveis.length === 0 && (
                <div className="p-12 text-center text-gray-500">
                  <AlertCircle className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p>Nenhum imóvel encontrado na área especificada</p>
                </div>
              )}

              {resultado && resultado.imoveis.length > 0 && (
                <div className="divide-y divide-gray-200 max-h-[calc(100vh-300px)] overflow-y-auto">
                  {resultado.imoveis.map((imovel) => (
                    <div
                      key={imovel.id}
                      className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                        selectedImovel?.id === imovel.id ? 'bg-green-50' : ''
                      }`}
                      onClick={() => setSelectedImovel(imovel)}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="text-sm font-medium text-gray-900">
                            {imovel.denominacao || 'Sem denominação'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {[imovel.municipio, imovel.uf].filter(Boolean).join('/')}
                            {imovel.area_ha && ` • ${imovel.area_ha.toFixed(2)} ha`}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Código: {imovel.parcela_codigo}
                          </p>
                          {imovel.situacao && (
                            <span className="inline-block mt-2 px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                              {imovel.situacao}
                            </span>
                          )}
                        </div>

                        {/* Botões de Download */}
                        {imovel.download_links && (
                          <div className="flex flex-wrap gap-1 ml-4">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadAll(imovel.parcela_codigo);
                              }}
                              className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 font-medium"
                              title="Baixar Todos (Servidor)"
                            >
                              Todos
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadParcela(imovel.parcela_codigo, 'parcela');
                              }}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                              title="CSV Parcela"
                            >
                              Parcela
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadParcela(imovel.parcela_codigo, 'vertice');
                              }}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                              title="CSV Vértices"
                            >
                              Vértice
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadParcela(imovel.parcela_codigo, 'limite');
                              }}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                              title="CSV Limites"
                            >
                              Limite
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadMemorial(imovel.parcela_codigo);
                              }}
                              className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                              title="Memorial Descritivo (PDF)"
                            >
                              Memorial
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenDetalhes(imovel.parcela_codigo);
                              }}
                              className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                              title="Ver detalhes completos da parcela"
                            >
                              Info
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Detalhes expandidos */}
                      {selectedImovel?.id === imovel.id && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <h4 className="text-xs font-medium text-gray-700 mb-2">
                            Propriedades:
                          </h4>
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(imovel.propriedades).slice(0, 10).map(([key, value]) => (
                              <div key={key} className="text-xs">
                                <span className="text-gray-600">{key}:</span>{' '}
                                <span className="text-gray-900">{String(value)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Modal de Detalhes */}
      <ParcelaDetalhesModal
        detalhes={detalhesModal}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
