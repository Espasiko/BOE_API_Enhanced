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
from sincronizar_tavily import sincronizar_tavily

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sincronizar_ia(fecha_str=None, recrear_qdrant=False, tavily_api_key=None, max_docs=None, solo_qdrant=False, solo_tavily=False):
    """
    Sincroniza los documentos con Qdrant y Tavily para que las IA de Mistral puedan acceder a ellos
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        recrear_qdrant: Si es True, recrea la colección de Qdrant
        tavily_api_key: API Key de Tavily (si es None, se busca en las variables de entorno)
        max_docs: Número máximo de documentos a sincronizar (si es None, se sincronizan todos)
        solo_qdrant: Si es True, solo sincroniza con Qdrant
        solo_tavily: Si es True, solo sincroniza con Tavily
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\n=== Iniciando sincronización de documentos para la fecha {fecha} ===\n")
        
        # Sincronizar con Qdrant
        if not solo_tavily:
            print("\n=== SINCRONIZACIÓN CON QDRANT ===\n")
            sincronizar_qdrant(fecha_str=fecha_str, recrear=recrear_qdrant)
        
        # Sincronizar con Tavily
        if not solo_qdrant:
            print("\n=== SINCRONIZACIÓN CON TAVILY ===\n")
            sincronizar_tavily(fecha_str=fecha_str, api_key=tavily_api_key, max_docs=max_docs)
        
        print("\n=== Sincronización completada ===\n")
        
    except Exception as e:
        print(f"Error durante la sincronización: {str(e)}")

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Qdrant y Tavily para IA')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--recrear-qdrant', action='store_true', help='Recrear la colección de Qdrant')
    parser.add_argument('--tavily-api-key', type=str, help='API Key de Tavily (por defecto: se usa la variable de entorno TAVILY_API_KEY)')
    parser.add_argument('--max-docs', type=int, help='Número máximo de documentos a sincronizar')
    parser.add_argument('--solo-qdrant', action='store_true', help='Solo sincronizar con Qdrant')
    parser.add_argument('--solo-tavily', action='store_true', help='Solo sincronizar con Tavily')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_ia(
        fecha_str=args.fecha, 
        recrear_qdrant=args.recrear_qdrant, 
        tavily_api_key=args.tavily_api_key, 
        max_docs=args.max_docs,
        solo_qdrant=args.solo_qdrant,
        solo_tavily=args.solo_tavily
    )
