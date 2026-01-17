import api from './api';
import type {
  BoundingBox,
  ConsultaRequest,
  ConsultaResponse,
  LayerType,
  ServerType,
} from '../types';

export const consultaService = {
  /**
   * Consulta imóveis por bounding box (POST)
   */
  async consultarImoveis(request: ConsultaRequest): Promise<ConsultaResponse> {
    const response = await api.post<ConsultaResponse>('/consultar', request);
    return response.data;
  },

  /**
   * Consulta imóveis por bounding box (GET)
   */
  async consultarImoveisGet(
    bbox: BoundingBox,
    camada: LayerType = 'sigef_particular',
    servidor: ServerType = 'auto',
    limite: number = 1000
  ): Promise<ConsultaResponse> {
    const response = await api.get<ConsultaResponse>('/consultar', {
      params: {
        x_min: bbox.x_min,
        y_min: bbox.y_min,
        x_max: bbox.x_max,
        y_max: bbox.y_max,
        camada,
        servidor,
        limite,
      },
    });
    return response.data;
  },

  /**
   * Consulta por bbox compacto no path
   */
  async consultarPorBboxPath(
    coords: string,
    camada: LayerType = 'sigef_particular',
    servidor: ServerType = 'auto',
    limite: number = 1000
  ): Promise<ConsultaResponse> {
    const response = await api.get<ConsultaResponse>(`/consultar/bbox/${coords}`, {
      params: { camada, servidor, limite },
    });
    return response.data;
  },

  /**
   * Gera URL de download do GeoJSON
   */
  getDownloadUrl(
    bbox: BoundingBox,
    camada: LayerType = 'sigef_particular',
    servidor: ServerType = 'auto',
    limite: number = 1000
  ): string {
    const params = new URLSearchParams({
      x_min: bbox.x_min.toString(),
      y_min: bbox.y_min.toString(),
      x_max: bbox.x_max.toString(),
      y_max: bbox.y_max.toString(),
      camada,
      servidor,
      limite: limite.toString(),
    });

    return `/api/v1/consultar/download?${params.toString()}`;
  },

  /**
   * Download do GeoJSON (abre em nova aba)
   */
  downloadGeoJSON(
    bbox: BoundingBox,
    camada: LayerType = 'sigef_particular',
    servidor: ServerType = 'auto',
    limite: number = 1000
  ): void {
    const url = this.getDownloadUrl(bbox, camada, servidor, limite);
    window.open(url, '_blank');
  },
};

export default consultaService;
