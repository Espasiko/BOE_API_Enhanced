import os
import sys
import django
import logging
from datetime import datetime
import dotenv
from tqdm import tqdm
from tavily import TavilyClient

# Cargar variables de entorno
dotenv.load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.boe.settings')
django.setup()

# Importar los modelos
from boe_analisis.models_simplified import DocumentoSimplificado

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sincronizar_tavily(fecha_str=None, api_key=None, max_docs=None):
    """
    Sincroniza los documentos de una fecha específica con Tavily
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        api_key: API Key de Tavily (si es None, se busca en las variables de entorno)
        max_docs: Número máximo de documentos a sincronizar (si es None, se sincronizan todos)
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\nSincronizando documentos para la fecha {fecha} con Tavily")
        
        # Obtener API Key de Tavily
        tavily_api_key = api_key or os.environ.get("TAVILY_API_KEY")
        
        if not tavily_api_key:
            print("Error: No se encontró la API Key de Tavily")
            print("Asegúrate de tener TAVILY_API_KEY configurada en el archivo .env o proporcionarla como argumento")
            return
        
        # Inicializar cliente de Tavily
        tavily_client = TavilyClient(api_key=tavily_api_key)
        
        # Obtener documentos para la fecha especificada
        query = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha)
        if max_docs:
            query = query[:max_docs]
        
        documentos = list(query)
        total_docs = len(documentos)
        
        if total_docs == 0:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        print(f"Sincronizando {total_docs} documentos con Tavily...")
        
        # Estadísticas
        exitosos = 0
        fallidos = 0
        
        # Procesar cada documento con barra de progreso
        for documento in tqdm(documentos, total=total_docs, desc="Sincronizando documentos"):
            try:
                # Preparar el contenido del documento
                contenido = {
                    "title": documento.titulo,
                    "content": documento.texto or "",
                    "url": documento.url_xml or f"https://www.boe.es/diario_boe/xml.php?id={documento.identificador}",
                    "metadata": {
                        "identificador": documento.identificador,
                        "fecha_publicacion": documento.fecha_publicacion.isoformat(),
                        "departamento": documento.departamento or "",
                        "materias": documento.materias or ""
                    }
                }
                
                # Enviar documento a Tavily
                response = tavily_client.add_to_knowledge_base(
                    content=contenido["content"],
                    title=contenido["title"],
                    url=contenido["url"],
                    metadata=contenido["metadata"]
                )
                
                # Verificar respuesta
                if response and "id" in response:
                    exitosos += 1
                    logger.info(f"Documento {documento.identificador} sincronizado exitosamente con Tavily (ID: {response['id']})")
                else:
                    fallidos += 1
                    logger.error(f"Error al sincronizar documento {documento.identificador} con Tavily: Respuesta inesperada")
                    
            except Exception as e:
                fallidos += 1
                logger.error(f"Error al sincronizar documento {documento.identificador} con Tavily: {str(e)}")
        
        # Mostrar estadísticas
        print(f"\nSincronización con Tavily completada:")
        print(f"Total de documentos: {total_docs}")
        print(f"Documentos sincronizados exitosamente: {exitosos}")
        print(f"Documentos con errores: {fallidos}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Tavily')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--api-key', type=str, help='API Key de Tavily (por defecto: se usa la variable de entorno TAVILY_API_KEY)')
    parser.add_argument('--max-docs', type=int, help='Número máximo de documentos a sincronizar')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_tavily(fecha_str=args.fecha, api_key=args.api_key, max_docs=args.max_docs)
