import os
import sys
import django
import logging
from datetime import datetime
import dotenv
from tqdm import tqdm
import cohere

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

def sincronizar_cohere(fecha_str=None, api_key=None, max_docs=None):
    """
    Sincroniza los documentos de una fecha específica con Cohere
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        api_key: API Key de Cohere (si es None, se busca en las variables de entorno)
        max_docs: Número máximo de documentos a sincronizar (si es None, se sincronizan todos)
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\nSincronizando documentos para la fecha {fecha} con Cohere")
        
        # Obtener API Key de Cohere
        cohere_api_key = api_key or os.environ.get("COHERE_API_KEY")
        
        if not cohere_api_key:
            print("Error: No se encontró la API Key de Cohere")
            print("Asegúrate de tener COHERE_API_KEY configurada en el archivo .env o proporcionarla como argumento")
            return
        
        # Inicializar cliente de Cohere
        co = cohere.Client(api_key=cohere_api_key)
        
        # Obtener documentos para la fecha especificada
        documentos = DocumentoSimplificado.objects.filter(fecha=fecha)
        
        if max_docs:
            documentos = documentos[:int(max_docs)]
        
        total_docs = documentos.count()
        
        if total_docs == 0:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        print(f"Sincronizando {total_docs} documentos con Cohere...")
        
        # Estadísticas
        docs_sincronizados = 0
        docs_fallidos = 0
        
        # Procesar documentos con barra de progreso
        for documento in tqdm(documentos, total=total_docs, desc="Procesando documentos"):
            try:
                # Preparar contenido del documento
                contenido = f"""
                Identificador: {documento.identificador}
                Título: {documento.titulo}
                Fecha: {documento.fecha}
                Departamento: {documento.departamento}
                
                Contenido:
                {documento.texto}
                """
                
                # Generar embeddings con Cohere
                response = co.embed(
                    texts=[contenido],
                    model="embed-multilingual-v3.0",
                    input_type="search_document"
                )
                
                if response and hasattr(response, 'embeddings'):
                    # Aquí podríamos guardar los embeddings en una base de datos si fuera necesario
                    logger.info(f"Documento {documento.identificador} procesado exitosamente con Cohere")
                    docs_sincronizados += 1
                else:
                    logger.error(f"Error al procesar documento {documento.identificador} con Cohere: Respuesta inesperada")
                    docs_fallidos += 1
                
            except Exception as e:
                logger.error(f"Error al procesar documento {documento.identificador} con Cohere: {str(e)}")
                docs_fallidos += 1
        
        print(f"\nSincronización con Cohere completada:")
        print(f"  - Documentos procesados: {docs_sincronizados}")
        print(f"  - Documentos fallidos: {docs_fallidos}")
        print(f"  - Total: {total_docs}")
        
    except Exception as e:
        logger.error(f"Error general en sincronizar_cohere: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Cohere')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--api-key', type=str, help='API Key de Cohere (por defecto: se usa la variable de entorno COHERE_API_KEY)')
    parser.add_argument('--max-docs', type=int, help='Número máximo de documentos a sincronizar')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_cohere(fecha_str=args.fecha, api_key=args.api_key, max_docs=args.max_docs)
