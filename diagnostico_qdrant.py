"""
Script de diagnóstico para verificar la conexión con Qdrant.
Este script carga las variables de entorno desde el archivo .env
y verifica si se puede conectar con el cluster de Qdrant.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

# Cargar variables de entorno desde el archivo .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Obtener las variables de entorno
qdrant_url = os.environ.get('QDRANT_URL')
qdrant_api_key = os.environ.get('QDRANT_API_KEY')

print("=== Diagnóstico de conexión con Qdrant ===")
print(f"URL de Qdrant: {qdrant_url}")
print(f"API Key de Qdrant: {'*' * 10 if qdrant_api_key else 'No configurada'}")

# Verificar si las variables están configuradas
if not qdrant_url:
    print("ERROR: No se ha configurado la URL de Qdrant en el archivo .env")
    sys.exit(1)

if not qdrant_api_key:
    print("ADVERTENCIA: No se ha configurado la API Key de Qdrant en el archivo .env")

# Intentar conectar con Qdrant
print("\nIntentando conectar con Qdrant...")
try:
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # Verificar la conexión
    collections = client.get_collections()
    print("✅ Conexión exitosa con Qdrant")
    print(f"Colecciones disponibles: {[c.name for c in collections.collections]}")
    
    # Verificar si existe la colección boe_documentos
    collection_names = [c.name for c in collections.collections]
    if "boe_documentos" in collection_names:
        print("\nVerificando colección boe_documentos...")
        try:
            # Obtener información de la colección
            collection_info = client.get_collection("boe_documentos")
            print(f"✅ Colección boe_documentos encontrada")
            print(f"Vectores: {collection_info.vectors_count}")
            print(f"Dimensión: {collection_info.config.params.vectors.size}")
            
            # Intentar hacer una búsqueda simple
            print("\nRealizando búsqueda de prueba...")
            try:
                # Búsqueda con un vector aleatorio (solo para probar la conexión)
                import numpy as np
                vector_size = collection_info.config.params.vectors.size
                results = client.search(
                    collection_name="boe_documentos",
                    query_vector=np.random.rand(vector_size).tolist(),
                    limit=1
                )
                print(f"✅ Búsqueda exitosa. Resultados: {len(results)}")
            except Exception as e:
                print(f"❌ Error al realizar búsqueda: {str(e)}")
        except Exception as e:
            print(f"❌ Error al obtener información de la colección: {str(e)}")
    else:
        print(f"❌ No se encontró la colección boe_documentos")
        
except UnexpectedResponse as e:
    print(f"❌ Error de respuesta inesperada: {str(e)}")
    print("Posible causa: API Key incorrecta o URL mal formada")
except Exception as e:
    print(f"❌ Error al conectar con Qdrant: {str(e)}")
    print("Posibles causas:")
    print("- URL incorrecta")
    print("- Problemas de red")
    print("- Qdrant no está en ejecución")
    print("- Firewall bloqueando la conexión")
