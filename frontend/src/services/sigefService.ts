import api from './api';
import type {
  ParcelaInfo,
  DownloadRequest,
  DownloadResponse,
  DownloadAllResponse,
  BatchDownloadRequest,
  BatchDownloadResponse,
} from '../types';

export const sigefService = {
  /**
   * Busca informações de uma parcela pelo código
   */
  async getParcelaInfo(codigo: string): Promise<ParcelaInfo> {
    const response = await api.get<ParcelaInfo>(`/sigef/parcela/${codigo}`);
    return response.data;
  },

  /**
   * Download de CSVs de uma parcela
   */
  async download(request: DownloadRequest): Promise<DownloadResponse> {
    const response = await api.post<DownloadResponse>('/sigef/download', request);
    return response.data;
  },

  /**
   * Download de todos os CSVs de uma parcela
   */
  async downloadAll(codigo: string): Promise<DownloadAllResponse> {
    const response = await api.post<DownloadAllResponse>('/sigef/download/all', { codigo });
    return response.data;
  },

  /**
   * Download em lote de múltiplas parcelas
   */
  async downloadBatch(request: BatchDownloadRequest): Promise<BatchDownloadResponse> {
    const response = await api.post<BatchDownloadResponse>('/sigef/download/batch', request);
    return response.data;
  },

  /**
   * Download direto de um arquivo específico
   */
  async downloadFile(codigo: string, tipo: 'parcela' | 'vertice' | 'limite'): Promise<Blob> {
    const response = await api.get(`/sigef/download/${codigo}/${tipo}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Faz download e salva arquivo localmente no navegador
   */
  async downloadAndSave(codigo: string, tipo: 'parcela' | 'vertice' | 'limite'): Promise<void> {
    const blob = await this.downloadFile(codigo, tipo);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${codigo}_${tipo}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Download do memorial descritivo (PDF)
   */
  async downloadMemorial(codigo: string): Promise<Blob> {
    const response = await api.get(`/sigef/memorial/${codigo}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Faz download e salva memorial localmente no navegador
   */
  async downloadAndSaveMemorial(codigo: string): Promise<void> {
    const blob = await this.downloadMemorial(codigo);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${codigo}_memorial.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Abre a página da parcela no navegador autenticado (Playwright)
   */
  async openBrowser(codigo: string): Promise<void> {
    await api.post(`/sigef/open-browser/${codigo}`);
  },

  async getDetalhes(codigo: string): Promise<any> {
    const response = await api.get(`/sigef/detalhes/${codigo}`);
    return response.data;
  },
};

export default sigefService;
