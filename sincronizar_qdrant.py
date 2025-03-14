import os
import sys
import django
import logging
from datetime import datetime
import dotenv
from tqdm import tqdm

# Cargar variables de entorno
dotenv.load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.boe.settings')
django.setup()

# Importar los modelos y utilidades
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.utils_qdrant import QdrantBOE, get_qdrant_client

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sincronizar_qdrant(fecha_str=None, recrear=False):
    """
    Sincroniza los documentos de una fecha específica con Qdrant
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        recrear: Si es True, recrea la colección de Qdrant
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\nSincronizando documentos para la fecha {fecha} con Qdrant")
        
        # Verificar la URL y API Key de Qdrant
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            print("Error: No se encontraron las credenciales de Qdrant en el archivo .env")
            print("Asegúrate de tener QDRANT_URL y QDRANT_API_KEY configurados correctamente")
            return
        
        print(f"Conectando a Qdrant en: {qdrant_url}")
        
        # Inicializar cliente de Qdrant
        qdrant = QdrantBOE(url=qdrant_url, api_key=qdrant_api_key)
        
        # Verificar la conexión
        try:
            # Intentar obtener estadísticas para verificar la conexión
            estadisticas = qdrant.obtener_estadisticas()
            if "error" in estadisticas:
                print(f"Error al conectar con Qdrant: {estadisticas['error']}")
                return
            print("Conexión con Qdrant establecida correctamente")
        except Exception as e:
            print(f"Error al conectar con Qdrant: {str(e)}")
            return
        
        # Crear o verificar la colección
        if recrear:
            print("Recreando colección en Qdrant...")
            if not qdrant.crear_coleccion(recrear=True):
                print("Error al recrear la colección en Qdrant")
                return
            print("Colección recreada exitosamente")
        else:
            print("Verificando colección en Qdrant...")
            if not qdrant.crear_coleccion(recrear=False):
                print("Error al verificar la colección en Qdrant")
                return
            print("Colección verificada exitosamente")
        
        # Obtener documentos para la fecha especificada
        documentos = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha)
        total_docs = documentos.count()
        
        if total_docs == 0:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        print(f"Indexando {total_docs} documentos en Qdrant...")
        
        # Estadísticas
        exitosos = 0
        fallidos = 0
        
        # Indexar cada documento con barra de progreso
        for documento in tqdm(documentos, total=total_docs, desc="Indexando documentos"):
            if qdrant.indexar_documento(documento):
                exitosos += 1
            else:
                fallidos += 1
        
        # Mostrar estadísticas
        print(f"\nSincronización completada:")
        print(f"Total de documentos: {total_docs}")
        print(f"Documentos indexados exitosamente: {exitosos}")
        print(f"Documentos con errores: {fallidos}")
        
        # Obtener estadísticas de la colección
        print("\nEstadísticas de la colección en Qdrant:")
        estadisticas = qdrant.obtener_estadisticas()
        
        if "error" in estadisticas:
            print(f"Error al obtener estadísticas: {estadisticas['error']}")
        else:
            print(f"Vectores: {estadisticas['vectores']}")
            print(f"Puntos: {estadisticas['puntos']}")
            print(f"Segmentos: {estadisticas['segmentos']}")
            print(f"Estado: {estadisticas['status']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Qdrant')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--recrear', action='store_true', help='Recrear la colección de Qdrant')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_qdrant(fecha_str=args.fecha, recrear=args.recrear)
