"""
Script de teste para validar a funcionalidade de consulta WFS.
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.v1.schemas import BoundingBox, LayerType, ServerType
from src.infrastructure.wfs.client import WFSService
from src.services.incra_service import IncraService


async def test_consulta():
    """Testa consulta básica."""
    
    # Bbox de teste (região de Curitiba-PR)
    bbox = BoundingBox(
        x_min=-49.35,
        y_min=-25.52,
        x_max=-49.20,
        y_max=-25.40
    )
    
    print("🔍 Testando consulta WFS...")
    print(f"   Bbox: {bbox.to_wfs_bbox()}")
    print(f"   Camada: SIGEF Particular")
    print(f"   Servidor: AUTO (fallback)")
    print()
    
    # Cria serviços
    wfs_service = WFSService()
    incra_service = IncraService(wfs_service)
    
    try:
        # Realiza consulta
        resultado = await incra_service.consultar_imoveis(
            bbox=bbox,
            layer_type=LayerType.SIGEF_PARTICULAR,
            server_type=ServerType.AUTO,
            limite=10
        )
        
        # Exibe resultados
        print(f"✅ Consulta realizada com sucesso!")
        print(f"   Status: {resultado.sucesso}")
        print(f"   Mensagem: {resultado.mensagem}")
        print(f"   Total: {resultado.total} imóveis")
        print(f"   Servidor: {resultado.servidor_utilizado}")
        print(f"   Tempo: {resultado.tempo_resposta_ms}ms")
        print()
        
        # Exibe alguns imóveis
        if resultado.imoveis:
            print(f"📍 Primeiros imóveis encontrados:")
            for i, imovel in enumerate(resultado.imoveis[:3], 1):
                print(f"   {i}. {imovel.denominacao or 'Sem nome'}")
                print(f"      Código: {imovel.parcela_codigo}")
                print(f"      Local: {imovel.municipio}/{imovel.uf}")
                print(f"      Área: {imovel.area_ha} ha")
                print()
        
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await wfs_service.close()


if __name__ == "__main__":
    asyncio.run(test_consulta())
