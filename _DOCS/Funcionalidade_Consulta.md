# Funcionalidade de Consulta - INCRA API v2

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Para Que Serve](#para-que-serve)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Back-end - FastAPI](#back-end---fastapi)
5. [Front-end - React + TypeScript](#front-end---react--typescript)
6. [Fluxo de Dados Completo](#fluxo-de-dados-completo)
7. [Como Replicar em Outro Projeto](#como-replicar-em-outro-projeto)

---

## 🎯 Visão Geral

A funcionalidade **Consulta** é o core desta aplicação. Ela permite buscar imóveis certificados do INCRA/SIGEF dentro de uma área geográfica específica (bounding box), utilizando serviços WFS (Web Feature Service) de dois servidores diferentes: **INCRA** e **GeoOne**.

### Principais Características:

- ✅ Consulta espacial por bounding box (retângulo de coordenadas geográficas)
- ✅ Suporte a múltiplas camadas (SIGEF Particular, SIGEF Público, SNCI, Assentamentos, etc.)
- ✅ Fallback automático entre servidores (INCRA → GeoOne)
- ✅ Detecção automática de UFs intersectadas pela área de consulta
- ✅ Retorno em formato GeoJSON (FeatureCollection)
- ✅ Links de download automático para cada imóvel (vértices, limites, parcela)
- ✅ Interface web interativa com mapa para desenhar área de consulta
- ✅ Validação de parâmetros (coordenadas, limites, etc.)

---

## 📖 Para Que Serve

### Problema que Resolve

O INCRA e SIGEF disponibilizam dados fundiários através de serviços WFS, mas:

1. **Complexidade**: Os endpoints variam por UF, camada e servidor
2. **Instabilidade**: O servidor INCRA frequentemente fica indisponível
3. **Formato**: Os dados retornados precisam de processamento adicional
4. **Usabilidade**: Não há interface amigável para consultas espaciais

### Solução Implementada

Esta API resolve esses problemas oferecendo:

- **Abstração**: Unifica acesso a diferentes servidores e camadas
- **Resiliência**: Implementa fallback automático entre servidores
- **Processamento**: Enriquece os dados com links de download e metadados
- **Interface**: Fornece dashboard web com mapa interativo

### Casos de Uso

1. **Consulta de imóveis em área específica**: Pesquisador define um retângulo no mapa e obtém todos os imóveis certificados naquela região
2. **Download de dados georreferenciados**: Obter GeoJSON de imóveis para análise em GIS (QGIS, ArcGIS)
3. **Integração com outros sistemas**: Outras aplicações podem consumir esta API via REST
4. **Verificação de certificação**: Consultores verificam se um imóvel específico está certificado no SIGEF

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐          │
│  │ MapView    │  │ Consulta   │  │ Results      │          │
│  │ (Leaflet)  │  │ Panel      │  │ Panel        │          │
│  └────────────┘  └────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                     HTTP REST API
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routes: /api/v1/consultar                           │  │
│  │  - POST /consultar                                   │  │
│  │  - GET /consultar                                    │  │
│  │  - GET /consultar/bbox/{coords}                      │  │
│  │  - GET /consultar/download                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Service: IncraService                               │  │
│  │  - Orquestra consultas                               │  │
│  │  - Processa features                                 │  │
│  │  - Gera links de download                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Service: WFSService                                 │  │
│  │  - Conecta com servidores WFS                        │  │
│  │  - Implementa fallback                               │  │
│  │  - Detecta UFs no bbox                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                  ┌─────────┴─────────┐
                  │                   │
        ┌─────────▼────────┐  ┌──────▼──────────┐
        │ INCRA WFS Server │  │ GeoOne WFS      │
        │ (por UF)         │  │ (nacional)      │
        └──────────────────┘  └─────────────────┘
```

---

## 🔧 Back-end - FastAPI

### 1. Estrutura de Arquivos

```
api/
├── routes/
│   └── consulta.py          # Endpoints REST
├── services/
│   ├── incra_service.py     # Lógica de negócio
│   └── wfs_service.py       # Comunicação WFS
├── models/
│   └── schemas.py           # Modelos Pydantic
└── config.py                # Configurações e mapeamentos
```

### 2. Modelos de Dados (schemas.py)

#### BoundingBox
```python
class BoundingBox(BaseModel):
    """Retângulo de coordenadas geográficas WGS84"""
    x_min: float  # Longitude mínima (Oeste)
    y_min: float  # Latitude mínima (Sul)
    x_max: float  # Longitude máxima (Leste)
    y_max: float  # Latitude máxima (Norte)
    
    def to_wfs_bbox(self) -> str:
        """Converte para formato WFS: 'x_min,y_min,x_max,y_max'"""
        return f"{self.x_min},{self.y_min},{self.x_max},{self.y_max}"
```

#### ConsultaRequest
```python
class ConsultaRequest(BaseModel):
    """Requisição de consulta"""
    bbox: BoundingBox
    camada: LayerType = LayerType.SIGEF_PARTICULAR
    servidor: ServerType = ServerType.AUTO
    limite: Optional[int] = 1000
```

#### ConsultaResponse
```python
class ConsultaResponse(BaseModel):
    """Resposta da consulta - É um GeoJSON FeatureCollection"""
    sucesso: bool
    mensagem: str
    total: int
    servidor_utilizado: str
    camada: str
    bbox_consultado: BoundingBox
    tempo_resposta_ms: float
    imoveis: List[ImovelResponse]
    
    # GeoJSON FeatureCollection
    type: str = "FeatureCollection"
    features: List[Dict]
```

#### ImovelResponse
```python
class ImovelResponse(BaseModel):
    """Representa um imóvel encontrado"""
    id: str
    parcela_codigo: str
    denominacao: Optional[str]
    municipio: Optional[str]
    uf: Optional[str]
    area_ha: Optional[float]
    situacao: Optional[str]
    data_certificacao: Optional[str]
    geometry: Dict  # GeoJSON Geometry
    download_links: Optional[DownloadLinks]
    propriedades: Dict  # Todas propriedades originais
```

### 3. Rotas (routes/consulta.py)

#### POST /api/v1/consultar
```python
@router.post("", response_model=ConsultaResponse)
async def consultar_imoveis(
    request: ConsultaRequest,
    service: IncraService = Depends(get_incra_service)
) -> ConsultaResponse:
    """
    Consulta imóveis por bounding box
    
    Body (JSON):
    {
        "bbox": {
            "x_min": -47.5,
            "y_min": -15.9,
            "x_max": -47.3,
            "y_max": -15.7
        },
        "camada": "sigef_particular",
        "servidor": "auto",
        "limite": 1000
    }
    """
    result = await service.consultar_imoveis(
        bbox=request.bbox,
        layer_type=request.camada,
        server_type=request.servidor,
        limite=request.limite
    )
    return result
```

#### GET /api/v1/consultar
```python
@router.get("", response_model=ConsultaResponse)
async def consultar_imoveis_get(
    x_min: float = Query(..., ge=-180, le=180),
    y_min: float = Query(..., ge=-90, le=90),
    x_max: float = Query(..., ge=-180, le=180),
    y_max: float = Query(..., ge=-90, le=90),
    camada: LayerType = Query(default=LayerType.SIGEF_PARTICULAR),
    servidor: ServerType = Query(default=ServerType.AUTO),
    limite: int = Query(default=1000, ge=1, le=10000)
) -> ConsultaResponse:
    """
    Versão GET para testes e integrações
    
    Exemplo:
    GET /api/v1/consultar?x_min=-47.5&y_min=-15.9&x_max=-47.3&y_max=-15.7&camada=sigef_particular
    """
```

#### GET /api/v1/consultar/download
```python
@router.get("/download")
async def download_geojson(
    x_min: float, y_min: float, x_max: float, y_max: float,
    camada: LayerType = Query(default=LayerType.SIGEF_PARTICULAR),
    servidor: ServerType = Query(default=ServerType.GEOONE)
) -> StreamingResponse:
    """
    Retorna GeoJSON como arquivo para download
    Content-Disposition: attachment; filename="consulta_YYYYMMDD_HHMMSS.geojson"
    """
```

### 4. Serviço de Negócio (services/incra_service.py)

O `IncraService` é o orquestrador principal da consulta:

```python
class IncraService:
    async def consultar_imoveis(
        self,
        bbox: BoundingBox,
        layer_type: LayerType,
        server_type: ServerType,
        limite: int
    ) -> ConsultaResponse:
        """
        Fluxo:
        1. Decide qual servidor usar (INCRA, GeoOne ou AUTO)
        2. Chama WFSService para obter features
        3. Processa cada feature (extrai campos, gera links)
        4. Monta resposta GeoJSON com metadados
        """
        
        # Consulta no servidor apropriado
        if server_type == ServerType.INCRA:
            features, servidor = await self.wfs_service.get_features_incra(bbox, layer_type)
        elif server_type == ServerType.GEOONE:
            features, servidor = await self.wfs_service.get_features_geoone(bbox, layer_type)
        else:  # AUTO
            features, servidor = await self.wfs_service.get_features_auto(bbox, layer_type)
        
        # Limita resultados
        features = features[:limite]
        
        # Processa cada feature
        imoveis = [self._process_feature(f) for f in features]
        
        # Retorna GeoJSON FeatureCollection
        return ConsultaResponse(
            sucesso=True,
            total=len(imoveis),
            servidor_utilizado=servidor,
            imoveis=imoveis,
            type="FeatureCollection",
            features=self._build_geojson_features(features)
        )
```

#### Processamento de Features
```python
def _process_feature(self, feature: Dict) -> ImovelResponse:
    """
    Extrai dados da feature WFS e enriquece com links
    
    Importante:
    - Os campos podem variar entre INCRA e GeoOne
    - Usa fallbacks: parcela_codigo or parcela_co or codigo
    - Gera links de download do SIGEF automaticamente
    """
    props = feature.get("properties", {})
    
    # Extrai código da parcela (vários nomes possíveis)
    parcela_codigo = (
        props.get("parcela_codigo") or
        props.get("parcela_co") or
        props.get("codigo")
    )
    
    # Gera links de download SIGEF
    if parcela_codigo:
        download_links = DownloadLinks(
            vertices_csv=f"https://sigef.incra.gov.br/geo/exportar/vertice/csv/{parcela_codigo}/",
            limites_shp=f"https://sigef.incra.gov.br/geo/exportar/limite/shp/{parcela_codigo}/",
            parcela_shp=f"https://sigef.incra.gov.br/geo/exportar/parcela/shp/{parcela_codigo}/",
            detalhes=f"https://sigef.incra.gov.br/geo/parcela/detalhe/{parcela_codigo}/"
        )
    
    return ImovelResponse(
        id=str(feature.get("id")),
        parcela_codigo=parcela_codigo,
        denominacao=props.get("nome_imovel") or props.get("denominacao"),
        municipio=props.get("municipio"),
        uf=props.get("uf"),
        area_ha=self._parse_area(props),
        situacao=props.get("situacao"),
        geometry=feature.get("geometry"),
        download_links=download_links,
        propriedades=props
    )
```

### 5. Serviço WFS (services/wfs_service.py)

O `WFSService` é responsável pela comunicação com os servidores WFS:

```python
class WFSService:
    async def get_features_auto(
        self, bbox: BoundingBox, layer_type: LayerType
    ) -> Tuple[List[Dict], str]:
        """
        Estratégia AUTO: Tenta INCRA primeiro, fallback para GeoOne
        
        Razão: INCRA tem dados mais atualizados mas é instável
        """
        try:
            features, servidor = await self.get_features_incra(bbox, layer_type)
            if features:
                return features, servidor
        except Exception as e:
            logger.warning(f"INCRA falhou: {e}. Tentando GeoOne...")
        
        # Fallback para GeoOne
        return await self.get_features_geoone(bbox, layer_type)
```

#### Consulta no INCRA (por UF)
```python
async def get_features_incra(
    self, bbox: BoundingBox, layer_type: LayerType
) -> Tuple[List[Dict], str]:
    """
    INCRA separa dados por UF
    
    Estratégia:
    1. Detecta quais UFs intersectam o bbox
    2. Consulta cada UF separadamente
    3. Agrega resultados
    """
    # Detecta UFs no bbox
    uf_list = self._detect_ufs_in_bbox(bbox)
    
    all_features = []
    for uf in uf_list:
        # URL específica da UF
        url = f"https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=certificada_sigef_particular_{uf}"
        
        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typename": f"ms:certificada_sigef_particular_{uf}",
            "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
            "outputFormat": "application/json"
        }
        
        response = await client.get(url, params=params)
        features = response.json().get("features", [])
        all_features.extend(features)
    
    return all_features, "incra"
```

#### Consulta no GeoOne (Nacional)
```python
async def get_features_geoone(
    self, bbox: BoundingBox, layer_type: LayerType
) -> Tuple[List[Dict], str]:
    """
    GeoOne tem dados nacionais em camada única
    
    Vantagem: Uma única requisição
    Desvantagem: Limite de tamanho do bbox (1 grau)
    """
    layer_config = LAYER_MAPPING.get(layer_type.value)
    
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": layer_config["geoone_layer"],
        "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
    
    response = await client.get(
        "https://geoonecloud.com/geoserver/GeoINCRA/wfs",
        params=params
    )
    
    features = response.json().get("features", [])
    return features, "geoone"
```

#### Detecção de UFs no Bounding Box
```python
def _detect_ufs_in_bbox(self, bbox: BoundingBox) -> List[str]:
    """
    Verifica quais UFs intersectam o bbox consultado
    
    Usa dicionário UF_MAPPING com bbox aproximado de cada estado
    """
    uf_list = []
    for uf, config in UF_MAPPING.items():
        uf_bbox = config["bbox"]
        if self._bboxes_intersect(bbox, uf_bbox):
            uf_list.append(uf.lower())
    return uf_list

def _bboxes_intersect(self, bbox1: BoundingBox, bbox2: list) -> bool:
    """Verifica se dois bboxes se intersectam"""
    return not (
        bbox1.x_max < bbox2[0] or  # bbox1 à esquerda de bbox2
        bbox1.x_min > bbox2[2] or  # bbox1 à direita de bbox2
        bbox1.y_max < bbox2[1] or  # bbox1 abaixo de bbox2
        bbox1.y_min > bbox2[3]     # bbox1 acima de bbox2
    )
```

### 6. Configuração (config.py)

#### Mapeamento de Camadas
```python
LAYER_MAPPING = {
    "sigef_particular": {
        "name": "Imóveis Certificados SIGEF - Particular",
        "incra_layer": "ms:certificada_sigef_particular_xx",  # xx = UF
        "geoone_layer": "GeoINCRA:certificado_sigef_privado",
        "incra_url_template": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=certificada_sigef_particular_xx"
    },
    "sigef_publico": {...},
    "snci_privado": {...},
    # ... outras camadas
}
```

#### URLs de Download SIGEF
```python
SIGEF_DOWNLOAD_URLS = {
    "vertices_csv": "https://sigef.incra.gov.br/geo/exportar/vertice/csv/{parcela_codigo}/",
    "limites_shp": "https://sigef.incra.gov.br/geo/exportar/limite/shp/{parcela_codigo}/",
    "parcela_shp": "https://sigef.incra.gov.br/geo/exportar/parcela/shp/{parcela_codigo}/",
    "detalhes": "https://sigef.incra.gov.br/geo/parcela/detalhe/{parcela_codigo}/"
}
```

---

## 💻 Front-end - React + TypeScript

### 1. Estrutura de Componentes

```
frontend/src/
├── components/
│   ├── ConsultaPanel.tsx      # Formulário de consulta
│   ├── ResultsPanel.tsx       # Lista de resultados
│   ├── MapView.tsx            # Mapa Leaflet
│   └── Sidebar.tsx            # Navegação
├── services/
│   └── api.ts                 # Cliente HTTP Axios
├── types/
│   └── index.ts               # Definições TypeScript
└── App.tsx                    # Componente principal
```

### 2. Tipos TypeScript

```typescript
// types/index.ts

export type LayerType = 
  | 'sigef_particular'
  | 'sigef_publico'
  | 'snci_privado'
  | 'snci_publico'
  | 'assentamentos'
  | 'quilombolas'
  | 'pendentes_titulacao'

export type ServerType = 'incra' | 'geoone' | 'auto'

export interface BoundingBox {
  x_min: number
  y_min: number
  x_max: number
  y_max: number
}

export interface ConsultaRequest {
  bbox: BoundingBox
  camada: LayerType
  servidor: ServerType
  limite?: number
}

export interface ImovelResponse {
  id: string
  parcela_codigo: string
  denominacao?: string
  municipio?: string
  uf?: string
  area_ha?: number
  situacao?: string
  geometry: any  // GeoJSON Geometry
  download_links?: DownloadLinks
  propriedades: Record<string, any>
}

export interface ConsultaResponse {
  sucesso: boolean
  mensagem: string
  total: number
  servidor_utilizado: string
  camada: string
  tempo_resposta_ms: number
  imoveis: ImovelResponse[]
  type: 'FeatureCollection'
  features: any[]
}
```

### 3. Cliente API (services/api.ts)

```typescript
import axios from 'axios'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutos
})

// Consulta POST
export async function consultarImoveis(
  request: ConsultaRequest
): Promise<ConsultaResponse> {
  const response = await api.post<ConsultaResponse>('/consultar', request)
  return response.data
}

// Consulta GET
export async function consultarImoveisGet(
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
  })
  return response.data
}

// Download GeoJSON
export async function downloadGeoJSON(
  bbox: BoundingBox,
  camada: LayerType,
  servidor: ServerType
): Promise<void> {
  const params = new URLSearchParams({
    x_min: bbox.x_min.toString(),
    y_min: bbox.y_min.toString(),
    x_max: bbox.x_max.toString(),
    y_max: bbox.y_max.toString(),
    camada,
    servidor,
  })
  
  const url = `${API_BASE_URL}/consultar/download?${params.toString()}`
  
  // Trigger download
  const link = document.createElement('a')
  link.href = url
  link.download = `${camada}_${Date.now()}.geojson`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
```

### 4. Componente ConsultaPanel

```tsx
// components/ConsultaPanel.tsx

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { consultarImoveis } from '../services/api'

interface ConsultaPanelProps {
  selectedBbox: BoundingBox | null  // Bbox selecionado no mapa
  onResults: (data: ConsultaResponse) => void
  onLoading: (loading: boolean) => void
}

export function ConsultaPanel({
  selectedBbox,
  onResults,
  onLoading,
}: ConsultaPanelProps) {
  const [bbox, setBbox] = useState<BoundingBox>({
    x_min: -49.17,
    y_min: -25.17,
    x_max: -49.15,
    y_max: -25.14,
  })
  const [camada, setCamada] = useState<LayerType>('sigef_particular')
  const [servidor, setServidor] = useState<ServerType>('auto')
  const [limite, setLimite] = useState(100)

  // Atualiza bbox quando usuário desenha no mapa
  if (selectedBbox && selectedBbox !== bbox) {
    setBbox(selectedBbox)
  }

  // React Query mutation
  const mutation = useMutation({
    mutationFn: consultarImoveis,
    onMutate: () => onLoading(true),
    onSuccess: (data) => {
      onResults(data)
      onLoading(false)
    },
    onError: () => onLoading(false),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ bbox, camada, servidor, limite })
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-4">
      {/* Campos de coordenadas */}
      <div className="grid grid-cols-2 gap-2">
        <input
          type="number"
          step="0.001"
          value={bbox.x_min}
          onChange={(e) => setBbox({...bbox, x_min: parseFloat(e.target.value)})}
          placeholder="Long. Mín"
        />
        {/* ... outros campos ... */}
      </div>

      {/* Select de camada */}
      <select value={camada} onChange={(e) => setCamada(e.target.value as LayerType)}>
        <option value="sigef_particular">SIGEF Particular</option>
        <option value="sigef_publico">SIGEF Público</option>
        {/* ... outras opções ... */}
      </select>

      {/* Botão de consulta */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-incra-600 text-white py-3 rounded"
      >
        {mutation.isPending ? 'Consultando...' : 'Consultar Imóveis'}
      </button>

      {/* Exibe erros */}
      {mutation.isError && (
        <div className="bg-red-50 p-3 rounded">
          Erro: {(mutation.error as Error).message}
        </div>
      )}
    </form>
  )
}
```

### 5. Componente MapView (Leaflet)

```tsx
// components/MapView.tsx

import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'

interface MapViewProps {
  results: ConsultaResponse | null
  isLoading: boolean
  onBboxSelect: (bbox: BoundingBox) => void
}

export function MapView({ results, isLoading, onBboxSelect }: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null)
  const [featureGroup] = useState(() => L.featureGroup())

  useEffect(() => {
    // Inicializa mapa
    if (!mapRef.current) {
      const map = L.map('map').setView([-15.7942, -47.8822], 4)
      
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
      }).addTo(map)

      // Adiciona controle de desenho
      featureGroup.addTo(map)
      
      const drawControl = new L.Control.Draw({
        draw: {
          rectangle: true,  // Apenas retângulos
          polygon: false,
          circle: false,
          marker: false,
          polyline: false,
          circlemarker: false
        },
        edit: {
          featureGroup: featureGroup,
          remove: true
        }
      })
      
      map.addControl(drawControl)

      // Listener para retângulo desenhado
      map.on(L.Draw.Event.CREATED, (event: any) => {
        const layer = event.layer
        featureGroup.clearLayers()
        featureGroup.addLayer(layer)

        const bounds = layer.getBounds()
        const bbox: BoundingBox = {
          x_min: bounds.getWest(),
          y_min: bounds.getSouth(),
          x_max: bounds.getEast(),
          y_max: bounds.getNorth(),
        }
        
        onBboxSelect(bbox)
      })

      mapRef.current = map
    }
  }, [])

  // Renderiza resultados no mapa
  useEffect(() => {
    if (!mapRef.current || !results) return

    // Remove camada anterior
    mapRef.current.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON) {
        mapRef.current?.removeLayer(layer)
      }
    })

    // Adiciona nova camada GeoJSON
    const geojsonLayer = L.geoJSON(
      {
        type: 'FeatureCollection',
        features: results.features
      },
      {
        style: {
          color: '#2563eb',
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.3
        },
        onEachFeature: (feature, layer) => {
          // Popup com informações
          const props = feature.properties
          layer.bindPopup(`
            <strong>${props.nome_imovel || 'Sem nome'}</strong><br>
            Município: ${props.municipio || 'N/A'}<br>
            Área: ${props.area_ha || 'N/A'} ha<br>
            Código: ${props.parcela_codigo || 'N/A'}
          `)
        }
      }
    )

    geojsonLayer.addTo(mapRef.current)

    // Ajusta zoom para mostrar todos os resultados
    if (results.features.length > 0) {
      mapRef.current.fitBounds(geojsonLayer.getBounds(), { padding: [50, 50] })
    }
  }, [results])

  return <div id="map" className="w-full h-full" />
}
```

### 6. Componente ResultsPanel

```tsx
// components/ResultsPanel.tsx

interface ResultsPanelProps {
  results: ConsultaResponse | null
}

export function ResultsPanel({ results }: ResultsPanelProps) {
  if (!results) {
    return (
      <div className="p-4 text-center text-gray-500">
        Nenhuma consulta realizada ainda
      </div>
    )
  }

  if (!results.sucesso) {
    return (
      <div className="p-4 bg-red-50 text-red-700">
        Erro: {results.mensagem}
      </div>
    )
  }

  return (
    <div className="p-4">
      {/* Metadados */}
      <div className="mb-4 p-3 bg-gray-50 rounded">
        <p className="text-sm text-gray-600">
          <strong>{results.total}</strong> imóveis encontrados
        </p>
        <p className="text-xs text-gray-500">
          Servidor: {results.servidor_utilizado} | 
          Tempo: {results.tempo_resposta_ms}ms
        </p>
      </div>

      {/* Lista de imóveis */}
      <div className="space-y-2">
        {results.imoveis.map((imovel) => (
          <div key={imovel.id} className="p-3 border rounded hover:bg-gray-50">
            <h3 className="font-medium text-sm">
              {imovel.denominacao || 'Sem denominação'}
            </h3>
            <p className="text-xs text-gray-600">
              {imovel.municipio}/{imovel.uf} | {imovel.area_ha?.toFixed(2)} ha
            </p>
            <p className="text-xs text-gray-500">
              Código: {imovel.parcela_codigo}
            </p>

            {/* Links de download */}
            {imovel.download_links && (
              <div className="mt-2 flex gap-2 flex-wrap">
                <a
                  href={imovel.download_links.vertices_csv}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                >
                  CSV Vértices
                </a>
                <a
                  href={imovel.download_links.limites_shp}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded"
                >
                  SHP Limites
                </a>
                <a
                  href={imovel.download_links.detalhes}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded"
                >
                  Detalhes
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### 7. App Principal

```tsx
// App.tsx

import { useState } from 'react'
import { ConsultaPanel } from './components/ConsultaPanel'
import { ResultsPanel } from './components/ResultsPanel'
import { MapView } from './components/MapView'

function App() {
  const [results, setResults] = useState<ConsultaResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedBbox, setSelectedBbox] = useState<BoundingBox | null>(null)
  const [activeTab, setActiveTab] = useState<'consulta' | 'resultados'>('consulta')

  return (
    <div className="flex h-screen">
      {/* Painel lateral */}
      <div className="w-96 bg-white border-r">
        {/* Tabs */}
        <div className="flex border-b">
          <button onClick={() => setActiveTab('consulta')}>
            Consulta
          </button>
          <button onClick={() => setActiveTab('resultados')}>
            Resultados ({results?.total || 0})
          </button>
        </div>

        {/* Conteúdo do tab */}
        {activeTab === 'consulta' ? (
          <ConsultaPanel
            selectedBbox={selectedBbox}
            onResults={(data) => {
              setResults(data)
              setActiveTab('resultados')
            }}
            onLoading={setIsLoading}
          />
        ) : (
          <ResultsPanel results={results} />
        )}
      </div>

      {/* Mapa */}
      <div className="flex-1">
        <MapView
          results={results}
          isLoading={isLoading}
          onBboxSelect={setSelectedBbox}
        />
      </div>
    </div>
  )
}

export default App
```

---

## 🔄 Fluxo de Dados Completo

### Fluxo de Consulta Passo-a-Passo

```
1. Usuário desenha retângulo no mapa (MapView)
   ↓
2. MapView emite bbox para App.tsx via onBboxSelect
   ↓
3. App.tsx atualiza selectedBbox
   ↓
4. ConsultaPanel recebe selectedBbox e atualiza formulário
   ↓
5. Usuário clica em "Consultar"
   ↓
6. ConsultaPanel chama mutation.mutate() com dados
   ↓
7. api.ts faz POST /api/v1/consultar com axios
   ↓
8. FastAPI routes/consulta.py recebe request
   ↓
9. Valida dados com Pydantic (ConsultaRequest)
   ↓
10. Chama IncraService.consultar_imoveis()
    ↓
11. IncraService decide servidor (AUTO, INCRA, GEOONE)
    ↓
12. Chama WFSService.get_features_auto()
    ↓
13. WFSService tenta INCRA:
    a. Detecta UFs no bbox
    b. Consulta cada UF via WFS
    c. Se falhar, tenta GeoOne
    ↓
14. WFSService retorna lista de features GeoJSON
    ↓
15. IncraService processa cada feature:
    a. Extrai campos padronizados
    b. Gera links de download
    c. Monta ImovelResponse
    ↓
16. IncraService retorna ConsultaResponse
    ↓
17. FastAPI serializa para JSON
    ↓
18. Axios recebe resposta
    ↓
19. React Query atualiza cache
    ↓
20. ConsultaPanel chama onResults(data)
    ↓
21. App.tsx:
    a. Atualiza results state
    b. Muda tab para 'resultados'
    ↓
22. ResultsPanel renderiza lista de imóveis
    ↓
23. MapView adiciona features ao mapa como GeoJSON layer
    ↓
24. Usuário vê resultados no painel e no mapa
```

### Diagrama de Sequência

```
┌──────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐     ┌────────┐
│ User │     │ MapView  │     │ Consulta│     │ FastAPI  │     │ Incra  │     │ WFS    │
│      │     │ (Leaflet)│     │ Panel   │     │ Routes   │     │ Service│     │ Service│
└──┬───┘     └────┬─────┘     └────┬────┘     └────┬─────┘     └───┬────┘     └───┬────┘
   │              │                 │                │               │              │
   │ Desenha      │                 │                │               │              │
   │ retângulo    │                 │                │               │              │
   ├─────────────>│                 │                │               │              │
   │              │                 │                │               │              │
   │              │ onBboxSelect    │                │               │              │
   │              │ (bbox)          │                │               │              │
   │              ├────────────────>│                │               │              │
   │              │                 │                │               │              │
   │              │                 │ Atualiza form  │               │              │
   │              │                 │ com bbox       │               │              │
   │ Clica        │                 │                │               │              │
   │ Consultar    │                 │                │               │              │
   ├─────────────────────────────> │                │               │              │
   │              │                 │                │               │              │
   │              │                 │ POST /consultar│               │              │
   │              │                 ├───────────────>│               │              │
   │              │                 │                │               │              │
   │              │                 │                │ consultar_    │              │
   │              │                 │                │ imoveis()     │              │
   │              │                 │                ├──────────────>│              │
   │              │                 │                │               │              │
   │              │                 │                │               │get_features  │
   │              │                 │                │               │_auto()       │
   │              │                 │                │               ├─────────────>│
   │              │                 │                │               │              │
   │              │                 │                │               │ WFS Request  │
   │              │                 │                │               │ (INCRA/      │
   │              │                 │                │               │  GeoOne)     │
   │              │                 │                │               │<─────────────┤
   │              │                 │                │               │              │
   │              │                 │                │ Processa      │              │
   │              │                 │                │ features      │              │
   │              │                 │                │<──────────────┤              │
   │              │                 │                │               │              │
   │              │                 │ ConsultaResponse│              │              │
   │              │                 │<───────────────┤               │              │
   │              │                 │                │               │              │
   │              │ onResults(data) │                │               │              │
   │              │<────────────────┤                │               │              │
   │              │                 │                │               │              │
   │ Renderiza    │                 │                │               │              │
   │ features     │                 │                │               │              │
   │<─────────────┤                 │                │               │              │
   │ no mapa      │                 │                │               │              │
```

---

## 🚀 Como Replicar em Outro Projeto

### Passo 1: Setup do Back-end (FastAPI)

#### 1.1 Instalar dependências
```bash
pip install fastapi uvicorn httpx pydantic pydantic-settings
```

#### 1.2 Criar estrutura de pastas
```
seu-projeto/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── consulta.py
│   └── services/
│       ├── __init__.py
│       ├── wfs_service.py
│       └── incra_service.py
└── requirements.txt
```

#### 1.3 Copiar arquivos base

**config.py**: Adapte as URLs dos servidores WFS para seu caso
```python
class Settings(BaseSettings):
    INCRA_WFS_URL: str = "https://seu-servidor-wfs.com/wfs"
    REQUEST_TIMEOUT: int = 60
```

**schemas.py**: Adapte os modelos para seus dados
```python
# Mantenha BoundingBox, ConsultaRequest, ConsultaResponse
# Adapte ImovelResponse para os campos do seu WFS
```

**wfs_service.py**: Adapte para seus servidores WFS
```python
# Mantenha a estrutura de get_features
# Modifique os parâmetros WFS conforme seu servidor
```

**incra_service.py**: Adapte a lógica de negócio
```python
# Mantenha a estrutura geral
# Modifique _process_feature para seus campos
```

**routes/consulta.py**: Use como está, apenas adapte a documentação

#### 1.4 Criar main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import consulta

app = FastAPI(
    title="Sua API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(consulta.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "API ativa"}
```

#### 1.5 Executar
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Passo 2: Setup do Front-end (React + TypeScript)

#### 2.1 Criar projeto
```bash
npm create vite@latest meu-frontend -- --template react-ts
cd meu-frontend
npm install
```

#### 2.2 Instalar dependências
```bash
npm install axios @tanstack/react-query leaflet leaflet-draw
npm install -D @types/leaflet @types/leaflet-draw
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### 2.3 Copiar arquivos

**src/types/index.ts**: Copie todas as interfaces TypeScript

**src/services/api.ts**: Adapte apenas a `API_BASE_URL`

**src/components/**: Copie todos os componentes
- ConsultaPanel.tsx
- ResultsPanel.tsx
- MapView.tsx
- App.tsx

#### 2.4 Configurar Tailwind CSS

**tailwind.config.js**:
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'incra': {
          50: '#f0f9ff',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        }
      }
    },
  },
  plugins: [],
}
```

**src/index.css**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### 2.5 Configurar React Query

**src/main.tsx**:
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

#### 2.6 Executar
```bash
npm run dev
```

### Passo 3: Pontos de Atenção

#### 3.1 Adaptar URLs WFS

Se seu servidor WFS tem estrutura diferente, adapte em `wfs_service.py`:

```python
# Exemplo: Se seu WFS não separa por UF
async def get_features_custom(self, bbox, layer_type):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": f"seu_namespace:{layer_type}",
        "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
        "outputFormat": "application/json"
    }
    
    response = await client.get("https://seu-servidor/wfs", params=params)
    return response.json().get("features", [])
```

#### 3.2 Adaptar Campos de Dados

Se suas features têm campos diferentes, adapte `_process_feature`:

```python
def _process_feature(self, feature: Dict) -> ImovelResponse:
    props = feature.get("properties", {})
    
    return ImovelResponse(
        id=props.get("id_campo_seu"),
        # Mapeie campos conforme seu WFS
        denominacao=props.get("nome_do_campo_nome"),
        municipio=props.get("campo_municipio"),
        # ... adapte para seus campos
    )
```

#### 3.3 CORS

Se API e frontend estiverem em domínios diferentes, configure CORS corretamente:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "https://seu-dominio.com"  # Produção
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 3.4 Proxy de Desenvolvimento

Configure proxy no Vite para evitar CORS em dev:

**vite.config.ts**:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### Passo 4: Testes

#### 4.1 Teste a API isoladamente

```bash
# Teste endpoint GET
curl "http://localhost:8000/api/v1/consultar?x_min=-47.5&y_min=-15.9&x_max=-47.3&y_max=-15.7&camada=sigef_particular"

# Teste endpoint POST
curl -X POST http://localhost:8000/api/v1/consultar \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": {"x_min": -47.5, "y_min": -15.9, "x_max": -47.3, "y_max": -15.7},
    "camada": "sigef_particular",
    "servidor": "auto",
    "limite": 10
  }'
```

#### 4.2 Teste o Frontend

1. Abra http://localhost:5173
2. Desenhe um retângulo no mapa
3. Ajuste parâmetros se necessário
4. Clique em "Consultar"
5. Verifique resultados no painel e no mapa

### Passo 5: Deploy

#### 5.1 Back-end (Docker)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t minha-api .
docker run -p 8000:8000 minha-api
```

#### 5.2 Front-end (Build estático)

```bash
npm run build
# Resultado em dist/ pode ser servido por nginx, netlify, vercel, etc.
```

---

## 📚 Conceitos Importantes

### WFS (Web Feature Service)

WFS é um padrão OGC para consulta de dados geográficos vetoriais via HTTP. Principais operações:

- **GetCapabilities**: Lista camadas disponíveis
- **DescribeFeatureType**: Descreve estrutura de uma camada
- **GetFeature**: Consulta features (dados geográficos)

Parâmetros comuns:
```
service=WFS
version=2.0.0
request=GetFeature
typeName=camada:nome
bbox=x_min,y_min,x_max,y_max,EPSG:4326
outputFormat=application/json
```

### GeoJSON

Formato JSON para dados geográficos:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "123",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-47.5, -15.9], ...]]
      },
      "properties": {
        "nome": "Fazenda X",
        "area_ha": 150.5
      }
    }
  ]
}
```

### Bounding Box

Retângulo definido por coordenadas mínimas e máximas:

```
x_min (West) ─────────────┐
              │           │
y_max (North) │           │ y_min (South)
              │           │
              └─────────────
                x_max (East)
```

Importante: WGS84 (EPSG:4326) usa:
- x = longitude (-180 a 180)
- y = latitude (-90 a 90)

### Fallback Strategy

Estratégia de resiliência implementada:

1. **Tenta servidor primário** (INCRA)
2. **Se falhar**, tenta secundário (GeoOne)
3. **Se ambos falharem**, retorna erro informativo

Benefícios:
- Maior disponibilidade
- Dados sempre disponíveis
- Experiência do usuário melhorada

---

## 🎓 Lições Aprendidas

### 1. Separação por UF no INCRA

O servidor INCRA separa dados por UF. Solução:

- Criar dicionário de bbox por UF
- Detectar UFs que intersectam área de consulta
- Fazer múltiplas requisições em paralelo
- Agregar resultados

### 2. Timeout em Consultas WFS

Serviços WFS podem demorar. Configuração adequada:

```python
httpx.AsyncClient(timeout=httpx.Timeout(60.0))
```

### 3. Validação de Coordenadas

Sempre validar bbox:
- x_max > x_min
- y_max > y_min
- Valores dentro de -180/180 e -90/90

### 4. Enriquecimento de Dados

Adicionar links de download melhora UX significativamente:

```python
download_links = {
    "vertices_csv": f"https://sigef.../vertice/csv/{codigo}/",
    "limites_shp": f"https://sigef.../limite/shp/{codigo}/"
}
```

### 5. React Query para Cache

`@tanstack/react-query` simplifica:
- Gerenciamento de estado assíncrono
- Cache automático
- Revalidação
- Loading states

---

## 📝 Checklist de Implementação

### Back-end
- [ ] Instalar FastAPI, httpx, pydantic
- [ ] Criar estrutura de pastas (routes, services, models)
- [ ] Copiar e adaptar schemas.py
- [ ] Implementar WFSService
- [ ] Implementar IncraService
- [ ] Criar rotas em consulta.py
- [ ] Configurar CORS
- [ ] Testar endpoints com curl/Postman
- [ ] Documentar API (Swagger automático)

### Front-end
- [ ] Criar projeto React + TypeScript
- [ ] Instalar dependências (axios, react-query, leaflet)
- [ ] Configurar Tailwind CSS
- [ ] Copiar types/index.ts
- [ ] Implementar api.ts
- [ ] Criar ConsultaPanel.tsx
- [ ] Criar ResultsPanel.tsx
- [ ] Criar MapView.tsx com Leaflet
- [ ] Integrar componentes em App.tsx
- [ ] Testar desenho de bbox no mapa
- [ ] Testar consulta e exibição de resultados

### Integração
- [ ] Configurar proxy em vite.config.ts
- [ ] Testar fluxo completo front → back
- [ ] Validar rendering de GeoJSON no mapa
- [ ] Testar links de download
- [ ] Verificar tratamento de erros
- [ ] Testar com diferentes camadas
- [ ] Testar fallback INCRA → GeoOne

### Deploy
- [ ] Criar Dockerfile para back-end
- [ ] Build do front-end (npm run build)
- [ ] Configurar variáveis de ambiente
- [ ] Deploy do back-end
- [ ] Deploy do front-end (CDN/Nginx)
- [ ] Configurar domínio e SSL
- [ ] Testar em produção

---

## 🔗 Recursos Adicionais

### Documentação Técnica

- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **httpx**: https://www.python-httpx.org/
- **React Query**: https://tanstack.com/query/latest
- **Leaflet**: https://leafletjs.com/
- **Leaflet.draw**: https://leaflet.github.io/Leaflet.draw/
- **Axios**: https://axios-http.com/
- **Tailwind CSS**: https://tailwindcss.com/

### Padrões OGC

- **WFS Standard**: https://www.ogc.org/standards/wfs
- **GeoJSON**: https://geojson.org/
- **EPSG:4326**: https://epsg.io/4326

### Servidores INCRA

- **Acervo Fundiário**: https://acervofundiario.incra.gov.br/
- **SIGEF**: https://sigef.incra.gov.br/
- **GeoOne**: https://geoonecloud.com/

---

## 💡 Possíveis Melhorias Futuras

1. **Cache Redis**: Cachear resultados de consultas frequentes
2. **Paginação**: Para grandes resultados (>10000 features)
3. **Filtros Avançados**: Por município, área, data de certificação
4. **Exportação**: SHP, KML, CSV além de GeoJSON
5. **Autenticação**: JWT para controlar acesso
6. **Rate Limiting**: Prevenir abuso da API
7. **Analytics**: Rastrear consultas mais comuns
8. **Testes Automatizados**: pytest para back, vitest para front
9. **CI/CD**: GitHub Actions para deploy automático
10. **Monitoramento**: Sentry, Prometheus, Grafana

---

**Documento criado em**: 29 de Dezembro de 2025  
**Versão da API**: 2.0.0  
**Autor**: Equipe de Desenvolvimento INCRA API

---

Este documento fornece todas as informações necessárias para compreender, manter e replicar a funcionalidade de Consulta em outros projetos. Para dúvidas ou contribuições, consulte o código-fonte e a documentação interativa do Swagger em `/docs`.
