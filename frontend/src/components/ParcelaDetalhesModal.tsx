import { X } from 'lucide-react';
import type { ParcelaDetalhesResponse } from '../types';

interface ParcelaDetalhesModalProps {
  detalhes: ParcelaDetalhesResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ParcelaDetalhesModal({ detalhes, isOpen, onClose }: ParcelaDetalhesModalProps) {
  if (!isOpen || !detalhes) return null;

  const InfoSection = ({ title, data }: { title: string; data: Record<string, string | null> }) => {
    const entries = Object.entries(data).filter(([_, value]) => value);
    if (entries.length === 0) return null;

    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 border-b border-gray-200 pb-2">
          {title}
        </h3>
        <div className="grid grid-cols-1 gap-3">
          {entries.map(([key, value]) => (
            <div key={key} className="bg-gray-50 rounded-lg p-3">
              <dt className="text-sm font-medium text-gray-500 capitalize mb-1">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="text-sm text-gray-900 font-medium break-words">{value}</dd>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-green-600 to-green-700 px-6 py-4 flex items-center justify-between z-10">
            <h2 className="text-xl font-bold text-white">
              Detalhes da Parcela SIGEF
            </h2>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {/* Código da Parcela */}
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-900">Código SIGEF</p>
                  <p className="text-lg font-mono font-bold text-blue-700 mt-1">
                    {detalhes.codigo}
                  </p>
                </div>
                <a
                  href={detalhes.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  Abrir no SIGEF
                </a>
              </div>
            </div>

            {/* Informações da Parcela */}
            <InfoSection title="📋 Informações da Parcela" data={detalhes.informacoes_parcela} />

            {/* Histórico */}
            {detalhes.historico && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 border-b border-gray-200 pb-2">
                  📅 Histórico ({detalhes.historico.quantidade} Requerimento{detalhes.historico.quantidade !== 1 ? 's' : ''})
                </h3>
                {detalhes.historico.quantidade === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
                    Nenhum requerimento
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-gray-100">
                          <th className="text-left p-3 text-sm font-semibold text-gray-700">Requerimento</th>
                          <th className="text-left p-3 text-sm font-semibold text-gray-700">Status</th>
                          <th className="text-left p-3 text-sm font-semibold text-gray-700">Data</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalhes.historico.requerimentos.map((req, idx) => (
                          <tr key={idx} className="border-t border-gray-200">
                            <td className="p-3 text-sm">{req.requerimento}</td>
                            <td className="p-3 text-sm">{req.status}</td>
                            <td className="p-3 text-sm">{req.data}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Área Georreferenciada */}
            {detalhes.area_georreferenciada && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 border-b border-gray-200 pb-2">
                  🗺️ Informações da Área Georreferenciada
                </h3>
                <div className="grid grid-cols-1 gap-3">
                  {Object.entries(detalhes.area_georreferenciada)
                    .filter(([key, value]) => key !== 'municipios' && value)
                    .map(([key, value]) => (
                      <div key={key} className="bg-gray-50 rounded-lg p-3">
                        <dt className="text-sm font-medium text-gray-500 capitalize mb-1">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd className="text-sm text-gray-900 font-medium">{String(value)}</dd>
                      </div>
                    ))}
                  
                  {detalhes.area_georreferenciada.municipios?.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <dt className="text-sm font-medium text-gray-500 mb-2">Municípios</dt>
                      <dd className="space-y-1">
                        {detalhes.area_georreferenciada.municipios.map((mun: string, idx: number) => (
                          <div key={idx} className="flex items-center text-sm text-gray-900">
                            <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                            {mun}
                          </div>
                        ))}
                      </dd>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Detentores */}
            {detalhes.detentores && detalhes.detentores.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 border-b border-gray-200 pb-2">
                  👤 Identificação do(a) Detentor(a)
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="text-left p-3 text-sm font-semibold text-gray-700">Nome</th>
                        <th className="text-left p-3 text-sm font-semibold text-gray-700">CPF/CNPJ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalhes.detentores.map((det, idx) => (
                        <tr key={idx} className="border-t border-gray-200">
                          <td className="p-3 text-sm">{det.nome}</td>
                          <td className="p-3 text-sm font-mono">{det.cpf_cnpj}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Informações de Registro */}
            <InfoSection title="📝 Informações de Registro" data={detalhes.registro} />
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 px-6 py-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
