# Funcionalidade de Consulta WFS - Implementação

## ✅ Status da Implementação

A funcionalidade de consulta de imóveis INCRA/SIGEF via WFS foi **implementada com sucesso**!

## 📋 O Que Foi Implementado

### Backend (FastAPI)

#### 1. **Schemas e Modelos** (`src/api/v1/schemas.py`)
- ✅ `LayerType` - Enum com tipos de camadas WFS
- ✅ `ServerType` - Enum com tipos de servidores (INCRA, GeoOne, AUTO)
- ✅ `BoundingBox` - Modelo para coordenadas geográficas com validação
- ✅ `ConsultaRequest` - Request de consulta
- ✅ `ConsultaResponse` - Response com GeoJSON FeatureCollection
- ✅ `ImovelResponse` - Dados de um imóvel encontrado
- ✅ `DownloadLinks` - Links de download para cada parcela

#### 2. **Serviço WFS** (`src/infrastructure/wfs/client.py`)
- ✅ `WFSService` - Cliente HTTP assíncrono para servidores WFS
- ✅ Consulta no servidor INCRA (por UF)
- ✅ Consulta no servidor GeoOne (nacional)
- ✅ Estratégia AUTO com fallback automático
- ✅ Detecção automática de UFs que intersectam o bbox
- ✅ Verificação de intersecção de bounding boxes

#### 3. **Serviço de Negócio** (`src/services/incra_service.py`)
- ✅ `IncraService` - Orquestração de consultas
- ✅ Processamento e enriquecimento de features
- ✅ Geração automática de links de download SIGEF
- ✅ Conversão de área para hectares
- ✅ Extração inteligente de campos com fallbacks
- ✅ Construção de resposta GeoJSON padronizada

#### 4. **Rotas da API** (`src/api/v1/routes/consulta.py`)
- ✅ `POST /api/v1/consultar` - Consulta via JSON
- ✅ `GET /api/v1/consultar` - Consulta via query params
- ✅ `GET /api/v1/consultar/bbox/{coords}` - Consulta com bbox compacto
- ✅ `GET /api/v1/consultar/download` - Download de GeoJSON
- ✅ Documentação Swagger automática
- ✅ Validação de parâmetros com Pydantic

#### 5. **Configurações** (`src/core/config.py`)
- ✅ URLs dos servidores WFS (INCRA e GeoOne)
- ✅ Mapeamento de camadas por tipo
- ✅ Mapeamento de UFs com bounding boxes
- ✅ URLs de download do SIGEF
- ✅ Timeouts e limites configuráveis

### Frontend (React + TypeScript)

#### 1. **Types TypeScript** (`frontend/src/types/api.ts`)
- ✅ Interfaces para todas as estruturas de dados
- ✅ Tipos `LayerType` e `ServerType`
- ✅ `BoundingBox`, `ConsultaRequest`, `ConsultaResponse`
- ✅ `ImovelResponse`, `DownloadLinks`

#### 2. **Serviço de API** (`frontend/src/services/consultaService.ts`)
- ✅ `consultarImoveis()` - Consulta via POST
- ✅ `consultarImoveisGet()` - Consulta via GET
- ✅ `consultarPorBboxPath()` - Consulta com bbox no path
- ✅ `getDownloadUrl()` - Gera URL de download
- ✅ `downloadGeoJSON()` - Baixa GeoJSON

#### 3. **Página de Consulta** (`frontend/src/pages/ConsultaPage.tsx`)
- ✅ Formulário de consulta com campos de bbox
- ✅ Seleção de camada (7 opções)
- ✅ Seleção de servidor (INCRA, GeoOne, AUTO)
- ✅ Limite de resultados configurável
- ✅ Lista de resultados com detalhes
- ✅ Botões de download individuais (CSV, SHP, Info)
- ✅ Download de GeoJSON completo
- ✅ Exibição de metadados (total, tempo, servidor usado)
- ✅ Tratamento de erros
- ✅ Loading states

#### 4. **Integração**
- ✅ Rota `/consulta` adicionada ao App
- ✅ Link de navegação no sidebar
- ✅ Export da página no index
- ✅ Integração com sistema de download existente

## 🚀 Como Usar

### 1. Via Interface Web

1. Acesse `http://localhost:3002/consulta`
2. Configure o bounding box (coordenadas WGS84):
   - Longitude Mínima (Oeste)
   - Latitude Mínima (Sul)
   - Longitude Máxima (Leste)
   - Latitude Máxima (Norte)
3. Selecione a camada desejada (ex: SIGEF Particular)
4. Escolha o servidor (recomendado: Automático)
5. Defina o limite de resultados (padrão: 100)
6. Clique em **Consultar**
7. Veja os resultados na lista
8. Clique nos botões de download para baixar dados de cada parcela:
   - **Todos** (verde): Baixa Parcela + Vértice + Limite de uma vez
   - **Parcela** (azul): Informações gerais (código, denominação, área, etc.)
   - **Vértice** (azul): Coordenadas dos vértices do perímetro
   - **Limite** (azul): Informações dos limites/confrontações
   - **Memorial** (roxo): Memorial descritivo em PDF
   - **Info** (cinza): Ver detalhes completos no SIGEF

### 2. Via API REST

#### Consulta POST (recomendado)

```bash
curl -X POST http://localhost:8000/api/v1/consultar \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": {
      "x_min": -49.17,
      "y_min": -25.17,
      "x_max": -49.15,
      "y_max": -25.14
    },
    "camada": "sigef_particular",
    "servidor": "auto",
    "limite": 100
  }'
```

#### Consulta GET (para testes)

```bash
curl "http://localhost:8000/api/v1/consultar?x_min=-49.17&y_min=-25.17&x_max=-49.15&y_max=-25.14&camada=sigef_particular&servidor=auto&limite=100"
```

#### Download GeoJSON

```bash
curl "http://localhost:8000/api/v1/consultar/download?x_min=-49.17&y_min=-25.17&x_max=-49.15&y_max=-25.14&camada=sigef_particular" -o resultado.geojson
```

### 3. Via Python

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/consultar",
        json={
            "bbox": {
                "x_min": -49.17,
                "y_min": -25.17,
                "x_max": -49.15,
                "y_max": -25.14
            },
            "camada": "sigef_particular",
            "servidor": "auto",
            "limite": 100
        }
    )
    
    resultado = response.json()
    print(f"Total: {resultado['total']} imóveis")
    
    for imovel in resultado['imoveis']:
        print(f"- {imovel['denominacao']} ({imovel['parcela_codigo']})")
```

## 📊 Exemplo de Resposta

```json
{
  "sucesso": true,
  "mensagem": "Consulta realizada com sucesso. 45 imóveis encontrados.",
  "total": 45,
  "servidor_utilizado": "incra",
  "camada": "Imóveis Certificados SIGEF - Particular",
  "bbox_consultado": {
    "x_min": -49.17,
    "y_min": -25.17,
    "x_max": -49.15,
    "y_max": -25.14
  },
  "tempo_resposta_ms": 2345.67,
  "imoveis": [
    {
      "id": "feature_123",
      "parcela_codigo": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "denominacao": "Fazenda São José",
      "municipio": "Curitiba",
      "uf": "PR",
      "area_ha": 150.5,
      "situacao": "Certificado",
      "data_certificacao": "2023-05-15",
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "download_links": {
        "vertices_csv": "https://sigef.incra.gov.br/geo/exportar/vertice/csv/a1b2c3d4.../",
        "limites_shp": "https://sigef.incra.gov.br/geo/exportar/limite/shp/a1b2c3d4.../",
        "parcela_shp": "https://sigef.incra.gov.br/geo/exportar/parcela/shp/a1b2c3d4.../",
        "detalhes": "https://sigef.incra.gov.br/geo/parcela/detalhe/a1b2c3d4.../"
      },
      "propriedades": { ... }
    }
  ],
  "type": "FeatureCollection",
  "features": [ ... ]
}
```

## 🎯 Camadas Disponíveis

1. **sigef_particular** - Imóveis Certificados SIGEF - Particular
2. **sigef_publico** - Imóveis Certificados SIGEF - Público
3. **snci_privado** - SNCI Privado
4. **snci_publico** - SNCI Público
5. **assentamentos** - Assentamentos
6. **quilombolas** - Quilombolas
7. **pendentes_titulacao** - Pendentes de Titulação

## 🌐 Servidores WFS

### INCRA (por UF)
- **URL**: `https://acervofundiario.incra.gov.br/i3geo/ogc.php`
- **Características**:
  - Dados separados por UF
  - Mais atualizados
  - Pode ficar indisponível
  - Requer múltiplas requisições (uma por UF)

### GeoOne (Nacional)
- **URL**: `https://geoonecloud.com/geoserver/GeoINCRA/wfs`
- **Características**:
  - Dados nacionais em camada única
  - Mais estável
  - Pode estar desatualizado
  - Uma única requisição

### AUTO (Recomendado)
- Tenta INCRA primeiro
- Se falhar, usa GeoOne como fallback
- Melhor disponibilidade e resiliência

## 🔗 Integração com Downloads

A funcionalidade de consulta está **totalmente integrada** com o sistema de download existente:

1. **Downloads através da nossa API**: Todos os downloads são feitos através da API FastAPI (`/api/v1/sigef/download`), não diretamente do SIGEF
2. **Mesmos tipos de arquivo da tela de Downloads**:
   - **Todos**: Baixa parcela, vértice e limite de uma vez (através do servidor)
   - **Parcela**: CSV com informações gerais da parcela
   - **Vértice**: CSV com coordenadas dos vértices
   - **Limite**: CSV com informações dos limites/confrontações
   - **Memorial**: PDF do memorial descritivo
   - **Info**: Link direto para detalhes no SIGEF
3. **Experiência consistente**: Os botões e comportamentos são idênticos à tela de Downloads
4. **Download via blob**: Arquivos são baixados como blob e salvos localmente no navegador

### Arquivos CSV Disponíveis

#### Parcela
Contém informações gerais da parcela:
- Código SIGEF (UUID)
- Denominação do imóvel
- Área em hectares
- Perímetro em metros
- Município e UF
- Situação (Certificado, Pendente, etc.)
- Datas de certificação

#### Vértice
Contém as coordenadas geográficas dos vértices:
- Sequência do vértice
- Latitude e Longitude (WGS84)
- Código da parcela
- Tipo de vértice

#### Limite
Contém informações sobre confrontações:
- Código do limite
- Tipo de confrontação
- Nome do confrontante
- Código da parcela

#### Memorial Descritivo (PDF)
Documento oficial com:
- Descrição completa do imóvel
- Coordenadas de todos os vértices
- Área e perímetro
- Confrontações detalhadas
- Informações do responsável técnico

## 📝 Documentação da API

Acesse a documentação interativa (Swagger):
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testes

Para testar a funcionalidade, execute:

```bash
# Backend
python test_consulta.py

# Frontend
# Acesse http://localhost:3002/consulta e teste manualmente
```

## ⚙️ Configurações

### Variáveis de Ambiente (.env)

```env
# WFS Configuration
WFS_INCRA_BASE_URL=https://acervofundiario.incra.gov.br/i3geo/ogc.php
WFS_GEOONE_BASE_URL=https://geoonecloud.com/geoserver/GeoINCRA/wfs
WFS_REQUEST_TIMEOUT=60
WFS_MAX_FEATURES=10000
```

### Limites e Timeouts

- **Timeout de requisição**: 60 segundos
- **Máximo de features**: 10.000 por consulta
- **Limite padrão**: 1.000 resultados
- **Range de limites**: 1 a 10.000

## 🎨 Screenshots da Interface

A interface inclui:
- ✅ Formulário intuitivo para definir bounding box
- ✅ Seleção visual de camadas e servidores
- ✅ Lista de resultados com informações detalhadas
- ✅ Botões de ação para downloads
- ✅ Indicadores de carregamento
- ✅ Mensagens de erro amigáveis
- ✅ Metadados da consulta (tempo, servidor, total)

## 🔄 Fluxo de Dados

```
Frontend (React)
    ↓
consultaService.consultarImoveis()
    ↓
POST /api/v1/consultar
    ↓
ConsultaRoute (FastAPI)
    ↓
IncraService.consultar_imoveis()
    ↓
WFSService.get_features_auto()
    ↓
[Tenta INCRA] → [Se falhar: GeoOne]
    ↓
Processa features
    ↓
Retorna GeoJSON + metadados
    ↓
Frontend renderiza resultados
```

## ✨ Funcionalidades Futuras

Possíveis melhorias:
- 🗺️ Integração com Leaflet para mapa interativo
- 🎨 Visualização dos polígonos no mapa
- 📊 Estatísticas agregadas (área total, por município, etc.)
- 💾 Cache de consultas frequentes
- 📄 Paginação de resultados
- 🔍 Filtros avançados (por município, área, data, etc.)
- 📦 Download em lote dos imóveis selecionados
- 🔔 Notificações de download completo

## 🤝 Compatibilidade

- ✅ Python 3.11+
- ✅ FastAPI 0.100+
- ✅ React 18+
- ✅ TypeScript 5+
- ✅ Todos os navegadores modernos

## 📚 Referências

- [Documentação INCRA WFS](https://acervofundiario.incra.gov.br/)
- [Documentação GeoOne](https://geoonecloud.com/)
- [Padrão WFS OGC](https://www.ogc.org/standards/wfs)
- [GeoJSON Specification](https://geojson.org/)
- [EPSG:4326 (WGS84)](https://epsg.io/4326)

---

**Data de Implementação**: 29 de Dezembro de 2025  
**Status**: ✅ Implementação Completa e Funcional
