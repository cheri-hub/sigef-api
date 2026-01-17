"""
Serviço de consulta de imóveis INCRA/SIGEF.

Este módulo orquestra a consulta e processamento de dados de imóveis
certificados no SIGEF.
"""

import logging
import time
from typing import Any

import httpx

from src.api.v1.schemas import (
    BoundingBox,
    ConsultaResponse,
    DownloadLinks,
    ImovelResponse,
    LayerType,
    ServerType,
)
from src.core.config import LAYER_MAPPING, SIGEF_DOWNLOAD_URLS
from src.infrastructure.wfs.client import WFSService


logger = logging.getLogger(__name__)


class IncraService:
    """
    Serviço para consulta e processamento de imóveis INCRA/SIGEF.
    
    Responsável por:
    - Orquestrar consultas WFS
    - Processar e enriquecer features
    - Gerar links de download
    - Construir resposta GeoJSON
    """
    
    def __init__(self, wfs_service: WFSService):
        """
        Inicializa o serviço INCRA.
        
        Args:
            wfs_service: Serviço WFS para consultas
        """
        self.wfs_service = wfs_service
        self._municipio_cache: dict[str, str] = {}  # Cache de códigos IBGE -> nomes
    
    async def consultar_imoveis(
        self,
        bbox: BoundingBox,
        layer_type: LayerType = LayerType.SIGEF_PARTICULAR,
        server_type: ServerType = ServerType.AUTO,
        limite: int = 1000
    ) -> ConsultaResponse:
        """
        Consulta imóveis por bounding box.
        
        Args:
            bbox: Bounding box da consulta
            layer_type: Tipo de camada a consultar (ignorado quando server_type=AUTO)
            server_type: Servidor a usar (incra, geoone, auto)
            limite: Limite máximo de resultados
            
        Returns:
            ConsultaResponse com features e metadados
        """
        start_time = time.time()
        
        try:
            # Se servidor = AUTO, consulta TODAS as camadas
            if server_type == ServerType.AUTO:
                logger.info("Servidor AUTO: consultando TODAS as camadas")
                all_features = []
                servidores_usados = []
                
                # Itera por todas as camadas disponíveis
                for layer in LayerType:
                    logger.info(f"Consultando camada: {layer.value}")
                    try:
                        features, servidor = await self.wfs_service.get_features_auto(
                            bbox, layer
                        )
                        if features:
                            logger.info(f"Camada {layer.value}: {len(features)} features encontradas")
                            all_features.extend(features)
                            if servidor not in servidores_usados:
                                servidores_usados.append(servidor)
                    except Exception as e:
                        logger.warning(f"Erro ao consultar camada {layer.value}: {e}")
                        continue
                
                features = all_features
                servidor = "+".join(servidores_usados) if servidores_usados else "auto"
                logger.info(f"Total de features encontradas em todas as camadas: {len(features)}")
            
            # Consulta servidor específico (INCRA ou GEOONE) com camada específica
            elif server_type == ServerType.INCRA:
                features, servidor = await self.wfs_service.get_features_incra(
                    bbox, layer_type
                )
            elif server_type == ServerType.GEOONE:
                features, servidor = await self.wfs_service.get_features_geoone(
                    bbox, layer_type
                )
            
            # Limita resultados
            features = features[:limite]
            
            # Processa cada feature
            imoveis = []
            for feature in features:
                try:
                    imovel = await self._process_feature_async(feature)
                    imoveis.append(imovel)
                except Exception as e:
                    logger.error(f"Erro ao processar feature: {e}")
                    continue
            
            # Calcula tempo de resposta
            tempo_ms = (time.time() - start_time) * 1000
            
            # Obtém nome da camada (ou "Todas as Camadas" se AUTO)
            if server_type == ServerType.AUTO:
                camada_nome = "Todas as Camadas"
            else:
                layer_config = LAYER_MAPPING.get(layer_type.value, {})
                camada_nome = layer_config.get("name", layer_type.value)
            
            return ConsultaResponse(
                sucesso=True,
                mensagem=f"Consulta realizada com sucesso. {len(imoveis)} imóveis encontrados.",
                total=len(imoveis),
                servidor_utilizado=servidor,
                camada=camada_nome,
                bbox_consultado=bbox,
                tempo_resposta_ms=round(tempo_ms, 2),
                imoveis=imoveis,
                type="FeatureCollection",
                features=self._build_geojson_features(features)
            )
            
        except Exception as e:
            logger.error(f"Erro na consulta: {e}", exc_info=True)
            tempo_ms = (time.time() - start_time) * 1000
            
            return ConsultaResponse(
                sucesso=False,
                mensagem=f"Erro na consulta: {str(e)}",
                total=0,
                servidor_utilizado="erro",
                camada=layer_type.value,
                bbox_consultado=bbox,
                tempo_resposta_ms=round(tempo_ms, 2),
                imoveis=[],
                type="FeatureCollection",
                features=[]
            )
    
    async def _process_feature_async(self, feature: dict[str, Any]) -> ImovelResponse:
        """
        Processa uma feature WFS e extrai dados padronizados (versão assíncrona).
        
        Os campos podem variar entre INCRA e GeoOne, então usamos
        múltiplos nomes possíveis com fallbacks.
        
        Args:
            feature: Feature GeoJSON do WFS
            
        Returns:
            ImovelResponse com dados padronizados
        """
        props = feature.get("properties", {})
        
        # Log para debug - ver campos disponíveis
        logger.debug(f"Properties disponíveis: {list(props.keys())}")
        
        # Extrai código da parcela (vários nomes possíveis)
        parcela_codigo = (
            props.get("parcela_codigo") or
            props.get("parcela_co") or
            props.get("codigo") or
            props.get("cod_imovel") or
            props.get("id") or
            str(feature.get("id", ""))
        )
        
        # Extrai denominação/nome
        denominacao = (
            props.get("nome_area") or
            props.get("nome_imovel") or
            props.get("denominacao") or
            props.get("nome") or
            None
        )
        
        # Extrai município (pode ser código IBGE ou nome)
        municipio_raw = (
            props.get("municipio_") or
            props.get("municipio") or
            props.get("nome_munic") or
            props.get("nm_municip") or
            None
        )
        
        # Se for código IBGE numérico, busca o nome na API do IBGE
        if municipio_raw is not None:
            if isinstance(municipio_raw, int) or (isinstance(municipio_raw, str) and municipio_raw.isdigit() and len(str(municipio_raw)) == 7):
                municipio = await self._get_municipio_name(str(municipio_raw))
            else:
                municipio = str(municipio_raw)
        else:
            municipio = None
        
        # Extrai UF (pode ser código numérico ou sigla)
        uf_raw = (
            props.get("uf_id") or
            props.get("uf") or
            props.get("sigla_uf") or
            props.get("sg_uf") or
            None
        )
        # Converte código numérico de UF para sigla
        uf = self._convert_uf_code(uf_raw) if uf_raw is not None else None
        
        # Extrai área em hectares
        area_ha = self._parse_area(props)
        
        # Extrai situação
        situacao = (
            props.get("situacao") or
            props.get("situacao_i") or
            props.get("status") or
            None
        )
        
        # Extrai data de certificação
        data_certificacao = (
            props.get("data_certificacao") or
            props.get("dt_certifi") or
            props.get("data_cert") or
            None
        )
        
        # Gera links de download se tiver código da parcela
        download_links = None
        if parcela_codigo:
            download_links = DownloadLinks(
                vertices_csv=SIGEF_DOWNLOAD_URLS["vertices_csv"].format(
                    parcela_codigo=parcela_codigo
                ),
                limites_shp=SIGEF_DOWNLOAD_URLS["limites_shp"].format(
                    parcela_codigo=parcela_codigo
                ),
                parcela_shp=SIGEF_DOWNLOAD_URLS["parcela_shp"].format(
                    parcela_codigo=parcela_codigo
                ),
                detalhes=SIGEF_DOWNLOAD_URLS["detalhes"].format(
                    parcela_codigo=parcela_codigo
                ),
            )
        
        return ImovelResponse(
            id=str(feature.get("id", "")),
            parcela_codigo=parcela_codigo,
            denominacao=denominacao,
            municipio=municipio,
            uf=uf,
            area_ha=area_ha,
            situacao=situacao,
            data_certificacao=data_certificacao,
            geometry=feature.get("geometry", {}),
            download_links=download_links,
            propriedades=props
        )
    
    def _convert_uf_code(self, uf_value: Any) -> str:
        """
        Converte código numérico de UF para sigla.
        
        Args:
            uf_value: Código numérico ou sigla da UF
            
        Returns:
            Sigla da UF
        """
        # Mapeamento de códigos IBGE para siglas
        UF_CODES = {
            11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
            21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
            31: "MG", 32: "ES", 33: "RJ", 35: "SP",
            41: "PR", 42: "SC", 43: "RS",
            50: "MS", 51: "MT", 52: "GO", 53: "DF"
        }
        
        # Se já é string, retorna direto
        if isinstance(uf_value, str):
            return uf_value
        
        # Se é número, converte usando o mapeamento
        if isinstance(uf_value, int):
            return UF_CODES.get(uf_value, str(uf_value))
        
        return str(uf_value)
    
    async def _get_municipio_name(self, codigo_ibge: str) -> str:
        """
        Busca o nome do município pelo código IBGE na API do IBGE.
        
        Args:
            codigo_ibge: Código IBGE do município (ex: 4103107)
            
        Returns:
            Nome do município ou código se não encontrar
        """
        # Verifica cache primeiro
        if codigo_ibge in self._municipio_cache:
            return self._municipio_cache[codigo_ibge]
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{codigo_ibge}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    nome = data.get("nome", codigo_ibge)
                    # Armazena no cache
                    self._municipio_cache[codigo_ibge] = nome
                    logger.debug(f"Município {codigo_ibge} -> {nome}")
                    return nome
                else:
                    logger.warning(f"Erro ao buscar município {codigo_ibge}: status {response.status_code}")
                    return codigo_ibge
        except Exception as e:
            logger.warning(f"Erro ao buscar município {codigo_ibge} na API IBGE: {e}")
            return codigo_ibge
    
    def _parse_area(self, props: dict[str, Any]) -> float | None:
        """
        Extrai e converte área para hectares.
        
        A área pode estar em diferentes campos e unidades.
        
        Args:
            props: Properties da feature
            
        Returns:
            Área em hectares ou None
        """
        # Possíveis campos de área
        area_value = (
            props.get("area_ha") or
            props.get("area") or
            props.get("area_hecta") or
            props.get("area_calc") or
            None
        )
        
        if area_value is None:
            return None
        
        try:
            area = float(area_value)
            
            # Se o valor for muito grande, pode estar em m²
            if area > 1000000:
                area = area / 10000  # Converte m² para ha
            
            return round(area, 4)
        except (ValueError, TypeError):
            return None
    
    def _build_geojson_features(
        self, features: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Constrói lista de features para GeoJSON FeatureCollection.
        
        Args:
            features: Features originais do WFS
            
        Returns:
            Features formatadas para GeoJSON
        """
        return features
