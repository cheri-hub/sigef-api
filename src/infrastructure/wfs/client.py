"""
Serviço de consulta a servidores WFS (Web Feature Service).

Este módulo implementa a comunicação com servidores WFS do INCRA e GeoOne
para consulta de features geográficas (imóveis certificados).
"""

from asyncio.windows_events import NULL
import logging
from typing import Any

import httpx

from src.api.v1.schemas import BoundingBox, LayerType
from src.core.config import LAYER_MAPPING, UF_MAPPING, get_settings


logger = logging.getLogger(__name__)


class WFSService:
    """
    Serviço para consultas WFS (Web Feature Service).
    
    Responsável por:
    - Consultar servidores WFS do INCRA e GeoOne
    - Detectar UFs que intersectam um bbox
    - Implementar estratégia de fallback automático
    """
    
    def __init__(self):
        """Inicializa o serviço WFS."""
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.wfs_request_timeout),
            verify=False  # Desabilita verificação SSL (comum em servidores gov.br)
        )
    
    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()
    
    async def get_features_auto(
        self, bbox: BoundingBox, layer_type: LayerType
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Estratégia AUTO: Tenta INCRA primeiro, fallback para GeoOne.
        
        Args:
            bbox: Bounding box da consulta
            layer_type: Tipo de camada a consultar
            
        Returns:
            Tupla com (lista de features, servidor utilizado)
        """
        try:
            logger.info(f"Tentando consulta no INCRA para {layer_type.value}")
            features, servidor = await self.get_features_incra(bbox, layer_type)
            if features:
                logger.info(f"INCRA retornou {len(features)} features")
                return features, servidor
        except Exception as e:
            logger.warning(f"INCRA falhou: {e}. Tentando GeoOne...")
        
        # Fallback para GeoOne
        logger.info(f"Usando GeoOne como fallback para {layer_type.value}")
        return await self.get_features_geoone(bbox, layer_type)
    
    async def get_features_incra(
        self, bbox: BoundingBox, layer_type: LayerType
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Consulta no servidor INCRA.
        
        O INCRA separa dados por UF, então precisamos:
        1. Detectar quais UFs intersectam o bbox
        2. Consultar cada UF separadamente
        3. Agregar resultados
        
        Args:
            bbox: Bounding box da consulta
            layer_type: Tipo de camada a consultar
            
        Returns:
            Tupla com (lista de features, servidor utilizado)
        """
        return [], "incra"
    
        layer_config = LAYER_MAPPING.get(layer_type.value)
        if not layer_config:
            raise ValueError(f"Camada não configurada: {layer_type.value}")
        
        # Detecta UFs no bbox
        uf_list = self._detect_ufs_in_bbox(bbox)
        
        if not uf_list:
            logger.warning("Nenhuma UF detectada no bbox fornecido")
            return [], "incra"
        
        logger.info(f"UFs detectadas: {', '.join(uf_list)}")
        
        # Consulta cada UF
        all_features = []
        for uf in uf_list:
            try:
                features = await self._query_incra_uf(bbox, layer_config, uf)
                all_features.extend(features)
                logger.info(f"UF {uf.upper()}: {len(features)} features encontradas")
            except Exception as e:
                logger.error(f"Erro ao consultar UF {uf.upper()}: {e}")
                continue
        
        return all_features, "incra"
    
    async def get_features_geoone(
        self, bbox: BoundingBox, layer_type: LayerType
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Consulta no servidor GeoOne.
        
        O GeoOne tem dados nacionais em camada única.
        Para SIGEF, tenta buscar também as variantes de norma (2n e 1n).
        
        Args:
            bbox: Bounding box da consulta
            layer_type: Tipo de camada a consultar
            
        Returns:
            Tupla com (lista de features, servidor utilizado)
        """
        layer_config = LAYER_MAPPING.get(layer_type.value)
        if not layer_config:
            raise ValueError(f"Camada não configurada: {layer_type.value}")
        
        base_layer = layer_config["geoone_layer"]
        all_features = []
        
        # Verifica se é SIGEF para buscar todas as normas
        if "sigef" in base_layer:
            # Lista de camadas a tentar (3ª, 2ª e 1ª norma)
            layer_variants = [
                base_layer
            ]
            
            logger.info(f"Buscando SIGEF no GeoOne em 3 normas")
            
            for layer_name in layer_variants:
                try:
                    params = {
                        "service": "WFS",
                        "version": "2.0.0",
                        "request": "GetFeature",
                        "typeName": layer_name,
                        "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
                        "outputFormat": "application/json",
                        "srsName": "EPSG:4326",
                        "maxFeatures": self.settings.wfs_max_features
                    }
                    
                    logger.debug(f"GeoOne consultando: {layer_name}")
                    
                    # Log da requisição
                    logger.info(f"[REQUEST] GeoOne GET {self.settings.wfs_geoone_base_url}")
                    logger.info(f"[REQUEST] Params: {params}")
                    
                    response = await self.client.get(
                        self.settings.wfs_geoone_base_url,
                        params=params
                    )
                    
                    # Log da resposta
                    logger.info(f"[RESPONSE] Status: {response.status_code}")
                    logger.info(f"[RESPONSE] Headers: {dict(response.headers)}")
                    logger.info(f"[RESPONSE] Body size: {len(response.content)} bytes")
                    logger.debug(f"[RESPONSE] Body preview: {response.text[:500]}...")
                    
                    response.raise_for_status()
                    
                    data = response.json()
                    features = data.get("features", [])
                    
                    if features:
                        logger.info(f"  {layer_name}: {len(features)} features")
                    
                    all_features.extend(features)
                    
                except Exception as e:
                    logger.debug(f"GeoOne camada {layer_name} não disponível: {e}")
                    continue
        else:
            # Outras camadas: consulta única
            params = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeName": base_layer,
                "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
                "outputFormat": "application/json",
                "srsName": "EPSG:4326",
                "maxFeatures": self.settings.wfs_max_features
            }
            
            logger.info(f"Consultando GeoOne: {base_layer}")
            
            # Log da requisição
            logger.info(f"[REQUEST] GeoOne GET {self.settings.wfs_geoone_base_url}")
            logger.info(f"[REQUEST] Params: {params}")
            
            response = await self.client.get(
                self.settings.wfs_geoone_base_url,
                params=params
            )
            
            # Log da resposta
            logger.info(f"[RESPONSE] Status: {response.status_code}")
            logger.info(f"[RESPONSE] Headers: {dict(response.headers)}")
            logger.info(f"[RESPONSE] Body size: {len(response.content)} bytes")
            logger.debug(f"[RESPONSE] Body preview: {response.text[:500]}...")
            
            response.raise_for_status()
            
            data = response.json()
            all_features = data.get("features", [])
        
        logger.info(f"GeoOne retornou {len(all_features)} features no total")
        
        return all_features, "geoone"
    
    async def _query_incra_uf(
        self, bbox: BoundingBox, layer_config: dict, uf: str
    ) -> list[dict[str, Any]]:
        """
        Consulta uma UF específica no servidor INCRA.
        Para SIGEF Particular e Público, busca todas as normas (1ª, 2ª e 3ª).
        
        Args:
            bbox: Bounding box da consulta
            layer_config: Configuração da camada
            uf: Sigla da UF (minúscula)
            
        Returns:
            Lista de features encontradas (agregadas de todas as normas)
        """
        all_features = []
        
        # Define as variantes de camadas a consultar (todas as normas)
        layer_variants = self._get_layer_variants(layer_config, uf)
        
        for url, typename in layer_variants:
            try:
                params = {
                    "service": "WFS",
                    "version": "1.1.0",
                    "request": "GetFeature",
                    "typename": typename,
                    "bbox": f"{bbox.to_wfs_bbox()},EPSG:4326",
                    "outputFormat": "application/json",
                    "maxFeatures": self.settings.wfs_max_features
                }
                
                # Log da requisição
                logger.info(f"[REQUEST] INCRA GET {url}")
                logger.info(f"[REQUEST] Params: {params}")
                logger.debug(f"Consultando: {url} | typename={typename}")
                
                response = await self.client.get(url, params=params)
                
                # Log da resposta
                logger.info(f"[RESPONSE] Status: {response.status_code}")
                logger.info(f"[RESPONSE] Headers: {dict(response.headers)}")
                logger.info(f"[RESPONSE] Body size: {len(response.content)} bytes")
                logger.info(f"[RESPONSE] Content-Type: {response.headers.get('content-type')}")
                logger.debug(f"[RESPONSE] Body preview: {response.text[:500]}...")
                
                response.raise_for_status()
                
                if response.status_code == 200 and not response.text.strip():
                    logger.debug(f"Norma {typename}: resposta vazia do servidor")
                    continue
                
                # Log primeiros 200 chars se não for JSON
                if 'json' not in response.headers.get('content-type', ''):
                    logger.debug(f"Resposta não-JSON: {response.text[:200]}")
                    continue
                
                data = response.json()
                features = data.get("features", [])
                
                if features:
                    logger.info(f"  {typename}: {len(features)} features")
                
                all_features.extend(features)
                
            except Exception as e:
                # Continua mesmo se uma norma falhar
                logger.debug(f"Norma {typename} não disponível ou erro: {e}")
                continue
        
        return all_features
    
    def _detect_ufs_in_bbox(self, bbox: BoundingBox) -> list[str]:
        """
        Detecta quais UFs intersectam o bbox consultado.
        
        Args:
            bbox: Bounding box da consulta
            
        Returns:
            Lista de siglas de UF (minúsculas)
        """
        uf_list = []
        
        for uf, config in UF_MAPPING.items():
            uf_bbox = config["bbox"]
            if self._bboxes_intersect(bbox, uf_bbox):
                uf_list.append(uf.lower())
        
        return uf_list
    
    def _bboxes_intersect(self, bbox1: BoundingBox, bbox2: list[float]) -> bool:
        """
        Verifica se dois bounding boxes se intersectam.
        
        Args:
            bbox1: Primeiro bbox (BoundingBox object)
            bbox2: Segundo bbox (lista [x_min, y_min, x_max, y_max])
            
        Returns:
            True se intersectam, False caso contrário
        """
        # Bboxes NÃO intersectam se:
        # - bbox1 está completamente à esquerda de bbox2
        # - bbox1 está completamente à direita de bbox2
        # - bbox1 está completamente abaixo de bbox2
        # - bbox1 está completamente acima de bbox2
        
        return not (
            bbox1.x_max < bbox2[0] or  # bbox1 à esquerda de bbox2
            bbox1.x_min > bbox2[2] or  # bbox1 à direita de bbox2
            bbox1.y_max < bbox2[1] or  # bbox1 abaixo de bbox2
            bbox1.y_min > bbox2[3]     # bbox1 acima de bbox2
        )
    
    def _get_layer_variants(self, layer_config: dict, uf: str) -> list[tuple[str, str]]:
        """
        Retorna lista de (url, typename) para todas as normas da camada.
        
        Para SIGEF Particular e Público, retorna 3 variantes (1ª, 2ª e 3ª normas).
        Para outras camadas, retorna apenas a camada padrão.
        
        Args:
            layer_config: Configuração da camada
            uf: Sigla da UF (minúscula)
            
        Returns:
            Lista de tuplas (url, typename)
        """
        base_url_template = layer_config["incra_url_template"]
        base_layer = layer_config["incra_layer"]
        
        # Verifica se é SIGEF (particular ou público) para buscar todas as normas
        if "sigef_particular" in base_layer or "sigef_publico" in base_layer:
            variants = []
            
            # padrão
            variants.append((
                base_url_template.format(uf=uf),
                base_layer.format(uf=uf)
            ))
            
            logger.info(f"Buscando SIGEF para UF {uf.upper()}")
            return variants
        else:
            # Outras camadas: apenas uma consulta
            return [(
                base_url_template.format(uf=uf),
                base_layer.format(uf=uf)
            )]
