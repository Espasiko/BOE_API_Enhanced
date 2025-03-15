import os
import sys
import django
import logging
from datetime import datetime
import dotenv
import argparse

# Cargar variables de entorno
dotenv.load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.boe.settings')
django.setup()

# Importar funciones de sincronización
from sincronizar_qdrant import sincronizar_qdrant
from sincronizar_cohere import sincronizar_cohere

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sincronizar_ia(fecha_str=None, recrear_qdrant=False, cohere_api_key=None, max_docs=None, solo_qdrant=False, solo_cohere=False):
    """
    Sincroniza los documentos con Qdrant y Cohere para que las IA de Mistral puedan acceder a ellos
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        recrear_qdrant: Si es True, recrea la colección de Qdrant
        cohere_api_key: API Key de Cohere (si es None, se busca en las variables de entorno)
        max_docs: Número máximo de documentos a sincronizar (si es None, se sincronizan todos)
        solo_qdrant: Si es True, solo sincroniza con Qdrant
        solo_cohere: Si es True, solo sincroniza con Cohere
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\n=== Iniciando sincronización de documentos para la fecha {fecha} ===\n")
        
        # Sincronizar con Qdrant
        if not solo_cohere:
            print("\n=== SINCRONIZACIÓN CON QDRANT ===\n")
            sincronizar_qdrant(fecha_str=fecha_str, recrear=recrear_qdrant)
        
        # Sincronizar con Cohere
        if not solo_qdrant:
            print("\n=== SINCRONIZACIÓN CON COHERE ===\n")
            sincronizar_cohere(fecha_str=fecha_str, api_key=cohere_api_key, max_docs=max_docs)
        
        print("\n=== Sincronización completada ===\n")
        
    except Exception as e:
        logger.error(f"Error general en sincronizar_ia: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Qdrant y Cohere para IA')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--recrear-qdrant', action='store_true', help='Recrear la colección de Qdrant')
    parser.add_argument('--cohere-api-key', type=str, help='API Key de Cohere (por defecto: se usa la variable de entorno COHERE_API_KEY)')
    parser.add_argument('--max-docs', type=int, help='Número máximo de documentos a sincronizar')
    parser.add_argument('--solo-qdrant', action='store_true', help='Solo sincronizar con Qdrant')
    parser.add_argument('--solo-cohere', action='store_true', help='Solo sincronizar con Cohere')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_ia(
        fecha_str=args.fecha, 
        recrear_qdrant=args.recrear_qdrant, 
        cohere_api_key=args.cohere_api_key, 
        max_docs=args.max_docs,
        solo_qdrant=args.solo_qdrant,
        solo_cohere=args.solo_cohere
    )
