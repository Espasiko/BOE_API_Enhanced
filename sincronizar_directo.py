import os
import sys
import sqlite3
import logging
from datetime import datetime
import dotenv
from tqdm import tqdm
import json
import uuid
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# Cargar variables de entorno
dotenv.load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de Qdrant
COLLECTION_NAME = "boe_documentos"
VECTOR_SIZE = 384  # para all-MiniLM-L6-v2
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class QdrantSincronizador:
    """
    Clase para sincronizar documentos con Qdrant
    """
    
    def __init__(self, url=None, api_key=None):
        """
        Inicializa la conexión con Qdrant
        
        Args:
            url: URL del servidor Qdrant
            api_key: API Key para autenticación
        """
        self.url = url or os.environ.get("QDRANT_URL")
        self.api_key = api_key or os.environ.get("QDRANT_API_KEY")
        
        if not self.url or not self.api_key:
            raise ValueError("Se requiere URL y API Key para Qdrant")
        
        # Inicializar cliente
        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        
        # Cargar modelo de embeddings
        self.model = SentenceTransformer(MODEL_NAME)
        
        logger.info(f"Inicializado cliente Qdrant en {self.url}")
    
    def crear_coleccion(self, recrear=False):
        """
        Crea la colección en Qdrant si no existe
        
        Args:
            recrear: Si es True, elimina la colección existente y la crea de nuevo
        
        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            # Verificar si la colección ya existe
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if COLLECTION_NAME in collection_names:
                if recrear:
                    logger.info(f"Eliminando colección existente: {COLLECTION_NAME}")
                    self.client.delete_collection(collection_name=COLLECTION_NAME)
                else:
                    logger.info(f"La colección {COLLECTION_NAME} ya existe")
                    return True
            
            # Crear la colección
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            
            # Crear índices para búsqueda por filtros
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="fecha_publicacion",
                field_schema="keyword",
            )
            
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="departamento",
                field_schema="keyword",
            )
            
            logger.info(f"Colección {COLLECTION_NAME} creada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear colección: {str(e)}")
            return False
    
    def generar_embedding(self, texto):
        """
        Genera un embedding para el texto proporcionado
        
        Args:
            texto: Texto para generar el embedding
        
        Returns:
            np.ndarray: Vector de embedding
        """
        return self.model.encode(texto)
    
    def indexar_documento(self, documento):
        """
        Indexa un documento en Qdrant
        
        Args:
            documento: Diccionario con los datos del documento
        
        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            # Preparar el texto para el embedding (título + texto)
            texto_completo = f"{documento['titulo']} {documento['texto'] if documento['texto'] else ''}"
            
            # Generar embedding
            embedding = self.generar_embedding(texto_completo)
            
            # Generar un UUID basado en el identificador del documento
            punto_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, documento['identificador']))
            
            # Preparar payload con metadatos
            payload = {
                "identificador": documento['identificador'],
                "titulo": documento['titulo'],
                "fecha_publicacion": documento['fecha_publicacion'],
                "departamento": documento['departamento'] or "",
                "codigo_departamento": documento['codigo_departamento'] or "",
                "materias": documento['materias'] or "",
                "palabras_clave": documento['palabras_clave'] or "",
                "url_pdf": documento['url_pdf'] or "",
                "url_xml": documento['url_xml'] or "",
            }
            
            # Indexar en Qdrant
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=punto_id,
                        vector=embedding.tolist(),
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"Documento {documento['identificador']} indexado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al indexar documento {documento['identificador']}: {str(e)}")
            return False
    
    def obtener_estadisticas(self):
        """
        Obtiene estadísticas de la colección en Qdrant
        
        Returns:
            dict: Estadísticas de la colección
        """
        try:
            # Obtener información de la colección
            collection_info = self.client.get_collection(collection_name=COLLECTION_NAME)
            
            # Preparar estadísticas
            stats = {
                "vectores": collection_info.config.params.vectors.size,
                "puntos": collection_info.vectors_count,
                "segmentos": len(collection_info.segments_count),
                "status": collection_info.status
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return {"error": str(e)}


class CohereSincronizador:
    """
    Clase para sincronizar documentos con Cohere
    """
    
    def __init__(self, api_key=None):
        """
        Inicializa la conexión con Cohere
        
        Args:
            api_key: API Key para autenticación
        """
        try:
            import cohere
            
            self.api_key = api_key or os.environ.get("COHERE_API_KEY")
            
            if not self.api_key:
                raise ValueError("Se requiere API Key para Cohere")
            
            # Inicializar cliente
            self.client = cohere.Client(api_key=self.api_key)
            
            logger.info("Inicializado cliente Cohere")
            
        except ImportError:
            logger.error("No se pudo importar el módulo cohere. Instálalo con: pip install cohere")
            raise
    
    def sincronizar_documento(self, documento):
        """
        Sincroniza un documento con Cohere generando embeddings
        
        Args:
            documento: Diccionario con los datos del documento
        
        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            # Preparar el contenido del documento
            titulo = documento['titulo']
            contenido = documento['texto'] or ""
            url = documento['url_xml'] or f"https://www.boe.es/diario_boe/xml.php?id={documento['identificador']}"
            
            # Metadatos adicionales
            metadata = {
                'identificador': documento['identificador'],
                'fecha': documento['fecha'],
                'departamento': documento['departamento'] or "Desconocido",
                'url': url
            }
            
            # Preparar el texto completo para el embedding
            texto_completo = f"""
            Título: {titulo}
            Fecha: {metadata['fecha']}
            Departamento: {metadata['departamento']}
            URL: {url}
            
            Contenido:
            {contenido}
            """
            
            # Generar embedding con Cohere
            response = self.client.embed(
                texts=[texto_completo],
                model="embed-multilingual-v3.0",
                input_type="search_document"
            )
            
            if response and hasattr(response, 'embeddings'):
                logger.info(f"Documento {documento['identificador']} sincronizado exitosamente con Cohere")
                return True
            else:
                logger.error(f"Error al sincronizar documento {documento['identificador']} con Cohere: Respuesta inesperada")
                return False
                
        except Exception as e:
            logger.error(f"Error al sincronizar documento {documento['identificador']} con Cohere: {str(e)}")
            return False


def obtener_documentos_sqlite(fecha_str=None, db_path="boe/boe.db", max_docs=None):
    """
    Obtiene documentos de la base de datos SQLite para una fecha específica
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        db_path: Ruta a la base de datos SQLite
        max_docs: Número máximo de documentos a obtener
    
    Returns:
        list: Lista de diccionarios con los datos de los documentos
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        # Convertir fecha a formato SQLite (YYYY-MM-DD)
        fecha_sqlite = fecha.strftime('%Y-%m-%d')
        
        # Verificar si existe la base de datos
        db_path = Path(db_path)
        if not db_path.exists():
            logger.error(f"No se encontró la base de datos en {db_path}")
            return []
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
        cursor = conn.cursor()
        
        # Consulta SQL
        query = """
            SELECT identificador, titulo, texto, fecha_publicacion, 
                   departamento, codigo_departamento, materias, 
                   palabras_clave, url_pdf, url_xml
            FROM boe_analisis_documentosimplificado 
            WHERE fecha_publicacion = ?
        """
        
        # Agregar límite si se especifica
        if max_docs:
            query += f" LIMIT {max_docs}"
        
        # Ejecutar consulta
        cursor.execute(query, (fecha_sqlite,))
        
        # Obtener resultados
        rows = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        documentos = []
        for row in rows:
            doc = dict(row)
            documentos.append(doc)
        
        # Cerrar conexión
        conn.close()
        
        logger.info(f"Se obtuvieron {len(documentos)} documentos de la base de datos para la fecha {fecha}")
        return documentos
        
    except Exception as e:
        logger.error(f"Error al obtener documentos de SQLite: {str(e)}")
        return []


def sincronizar_documentos(fecha_str=None, recrear_qdrant=False, max_docs=None, solo_qdrant=False, solo_cohere=False):
    """
    Sincroniza los documentos con Qdrant y Cohere
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        recrear_qdrant: Si es True, recrea la colección de Qdrant
        max_docs: Número máximo de documentos a sincronizar
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
        
        # Obtener documentos de SQLite
        documentos = obtener_documentos_sqlite(fecha_str=fecha_str, max_docs=max_docs)
        
        if not documentos:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        total_docs = len(documentos)
        print(f"Se encontraron {total_docs} documentos para sincronizar")
        
        # Sincronizar con Qdrant
        if not solo_cohere:
            print("\n=== SINCRONIZACIÓN CON QDRANT ===\n")
            
            try:
                # Inicializar sincronizador de Qdrant
                qdrant = QdrantSincronizador()
                
                # Crear colección
                print("Verificando colección en Qdrant...")
                if qdrant.crear_coleccion(recrear=recrear_qdrant):
                    print("Colección verificada/creada exitosamente")
                else:
                    print("Error al verificar/crear la colección en Qdrant")
                    return
                
                # Indexar documentos
                print(f"Indexando {total_docs} documentos en Qdrant...")
                
                # Estadísticas
                exitosos_qdrant = 0
                fallidos_qdrant = 0
                
                # Indexar cada documento con barra de progreso
                for documento in tqdm(documentos, total=total_docs, desc="Indexando en Qdrant"):
                    if qdrant.indexar_documento(documento):
                        exitosos_qdrant += 1
                    else:
                        fallidos_qdrant += 1
                
                # Mostrar estadísticas
                print(f"\nSincronización con Qdrant completada:")
                print(f"Total de documentos: {total_docs}")
                print(f"Documentos indexados exitosamente: {exitosos_qdrant}")
                print(f"Documentos con errores: {fallidos_qdrant}")
                
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
                print(f"Error durante la sincronización con Qdrant: {str(e)}")
        
        # Sincronizar con Cohere
        if not solo_qdrant:
            print("\n=== SINCRONIZACIÓN CON COHERE ===\n")
            
            try:
                # Inicializar sincronizador de Cohere
                cohere = CohereSincronizador()
                
                # Sincronizar documentos
                print(f"Sincronizando {total_docs} documentos con Cohere...")
                
                # Estadísticas
                exitosos_cohere = 0
                fallidos_cohere = 0
                
                # Sincronizar cada documento con barra de progreso
                for documento in tqdm(documentos, total=total_docs, desc="Sincronizando con Cohere"):
                    if cohere.sincronizar_documento(documento):
                        exitosos_cohere += 1
                    else:
                        fallidos_cohere += 1
                
                # Mostrar estadísticas
                print(f"\nSincronización con Cohere completada:")
                print(f"Total de documentos: {total_docs}")
                print(f"Documentos sincronizados exitosamente: {exitosos_cohere}")
                print(f"Documentos con errores: {fallidos_cohere}")
                
            except Exception as e:
                print(f"Error durante la sincronización con Cohere: {str(e)}")
        
        print("\n=== Sincronización completada ===\n")
        
    except Exception as e:
        print(f"Error durante la sincronización: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sincronizar documentos con Qdrant y Cohere para IA')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--recrear-qdrant', action='store_true', help='Recrear la colección de Qdrant')
    parser.add_argument('--max-docs', type=int, help='Número máximo de documentos a sincronizar')
    parser.add_argument('--solo-qdrant', action='store_true', help='Solo sincronizar con Qdrant')
    parser.add_argument('--solo-cohere', action='store_true', help='Solo sincronizar con Cohere')
    
    args = parser.parse_args()
    
    # Ejecutar sincronización
    sincronizar_documentos(
        fecha_str=args.fecha, 
        recrear_qdrant=args.recrear_qdrant, 
        max_docs=args.max_docs,
        solo_qdrant=args.solo_qdrant,
        solo_cohere=args.solo_cohere
    )
