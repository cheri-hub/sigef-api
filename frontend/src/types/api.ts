// Auth Types
export interface SessionInfo {
  session_id: string;
  cpf: string | null;
  nome: string | null;
  is_valid: boolean;
  is_govbr_authenticated: boolean;
  is_sigef_authenticated: boolean;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

export interface SessionStatus {
  authenticated: boolean;
  session: SessionInfo | null;
  message: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  session: SessionInfo | null;
}

export interface LogoutResponse {
  success: boolean;
  message: string;
}

// SIGEF Types
export interface ParcelaInfo {
  codigo: string;
  denominacao?: string | null;
  area?: number | null;
  area_ha?: number | null;
  perimetro_m?: number | null;
  municipio?: string | null;
  uf?: string | null;
  situacao?: string | null;
  url?: string;
}

export interface HistoricoRequerimento {
  requerimento: string;
  status: string;
  data: string;
}

export interface ParcelaHistorico {
  quantidade: number;
  requerimentos: HistoricoRequerimento[];
}

export interface ParcelaDetalhesResponse {
  codigo: string;
  url: string;
  informacoes_parcela: Record<string, any>;
  historico: ParcelaHistorico;
  area_georreferenciada: Record<string, any>;
  detentores: Record<string, any>[];
  registro: Record<string, any>;
}

export interface DownloadRequest {
  codigo: string;
  tipos?: ('parcela' | 'vertice' | 'limite')[];
}

export interface BatchDownloadRequest {
  codigos: string[];
  tipos?: ('parcela' | 'vertice' | 'limite')[];
}

export interface DownloadResponse {
  success: boolean;
  message: string;
  arquivo?: string | null;
  tamanho_bytes?: number | null;
}

export interface DownloadAllResponse {
  success: boolean;
  message: string;
  arquivos?: Record<string, string>;
}

export interface BatchDownloadResponse {
  success: boolean;
  message: string;
  total: number;
  sucesso: number;
  falhas: number;
  resultados: Record<string, Record<string, string>>;
}

// API Error
export interface ApiError {
  detail: string;
  status_code?: number;
}

// Consulta WFS Types
export type LayerType = 
  | 'sigef_particular'
  | 'sigef_publico'
  | 'snci_privado'
  | 'snci_publico'
  | 'assentamentos'
  | 'quilombolas'
  | 'pendentes_titulacao';

export type ServerType = 'incra' | 'geoone' | 'auto';

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface ConsultaRequest {
  bbox: BoundingBox;
  camada: LayerType;
  servidor: ServerType;
  limite?: number;
}

export interface DownloadLinks {
  vertices_csv: string;
  limites_shp: string;
  parcela_shp: string;
  detalhes: string;
}

export interface ImovelResponse {
  id: string;
  parcela_codigo: string;
  denominacao?: string | null;
  municipio?: string | null;
  uf?: string | null;
  area_ha?: number | null;
  situacao?: string | null;
  data_certificacao?: string | null;
  geometry: any; // GeoJSON Geometry
  download_links?: DownloadLinks | null;
  propriedades: Record<string, any>;
}

export interface ConsultaResponse {
  sucesso: boolean;
  mensagem: string;
  total: number;
  servidor_utilizado: string;
  camada: string;
  bbox_consultado: BoundingBox;
  tempo_resposta_ms: number;
  imoveis: ImovelResponse[];
  type: 'FeatureCollection';
  features: any[];
}
