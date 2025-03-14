"""
Utilidades para integrar Qdrant con el sistema de alertas del BOE.
Este módulo proporciona funciones para crear una colección en Qdrant,
indexar documentos del BOE y realizar búsquedas semánticas.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np
import uuid
from django.conf import settings
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from boe_analisis.models_simplified import DocumentoSimplificado

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nombre de la colección en Qdrant
COLLECTION_NAME = "boe_documentos"

# Dimensión de los vectores (depende del modelo de embedding)
VECTOR_SIZE = 384  # para all-MiniLM-L6-v2

# Modelo de embedding
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class QdrantBOE:
    """
    Clase para gestionar la integración con Qdrant para el sistema de alertas del BOE.
    """
    
    def __init__(self, url: str = "http://localhost:6333", api_key: Optional[str] = None):
        """
        Inicializa la conexión con Qdrant.
        
        Args:
            url: URL del servidor Qdrant
            api_key: Clave API para autenticación (opcional)
        """
        self.url = url
        self.api_key = api_key or os.environ.get("QDRANT_API_KEY")
        
        # Inicializar cliente de Qdrant
        self.client = QdrantClient(url=url, api_key=self.api_key)
        
        # Inicializar modelo de embedding
        try:
            self.model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Modelo de embedding inicializado: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"Error al inicializar modelo de embedding: {str(e)}")
            self.model = None
        
        logger.info(f"Inicializado cliente Qdrant en {url}")
        
    def crear_coleccion(self, recrear: bool = False) -> bool:
        """
        Crea la colección en Qdrant si no existe.
        
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
                field_schema="datetime",
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
    
    def generar_embedding(self, texto: str) -> np.ndarray:
        """
        Genera un embedding para el texto proporcionado.
        
        Args:
            texto: Texto para generar embedding
            
        Returns:
            np.ndarray: Vector de embedding
        """
        return self._generar_embedding_cached(texto)
    
    @lru_cache(maxsize=1000)
    def _generar_embedding_cached(self, texto: str) -> np.ndarray:
        """
        Versión cacheada de generar_embedding.
        
        Args:
            texto: Texto para generar embedding
            
        Returns:
            np.ndarray: Vector de embedding
        """
        if not self.model:
            raise Exception("Modelo de embedding no inicializado")
        
        try:
            # Generar embedding
            embedding = self.model.encode(texto)
            return embedding
        except Exception as e:
            logger.error(f"Error al generar embedding: {str(e)}")
            raise
    
    def indexar_documento(self, documento: DocumentoSimplificado) -> bool:
        """
        Indexa un documento en Qdrant.
        
        Args:
            documento: Documento a indexar
            
        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            # Preparar el texto para el embedding (título + texto)
            texto_completo = f"{documento.titulo} {documento.texto if documento.texto else ''}"
            
            # Generar embedding
            embedding = self.generar_embedding(texto_completo)
            
            # Generar un UUID basado en el identificador del documento
            # Esto es necesario porque Qdrant solo acepta enteros o UUIDs como IDs
            punto_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, documento.identificador))
            
            # Preparar payload con metadatos
            payload = {
                "identificador": documento.identificador,
                "titulo": documento.titulo,
                "texto": documento.texto,  
                "fecha_publicacion": documento.fecha_publicacion.isoformat(),
                "departamento": documento.departamento or "",
                "codigo_departamento": documento.codigo_departamento or "",
                "materias": documento.materias or "",
                "palabras_clave": documento.palabras_clave or "",
                "url_pdf": documento.url_pdf or "",
                "url_xml": documento.url_xml or "",
                "vigente": documento.vigente,  
                "longitud_texto": len(documento.texto) if documento.texto else 0,  
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
            
            logger.info(f"Documento {documento.identificador} indexado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al indexar documento {documento.identificador}: {str(e)}")
            return False
    
    def indexar_documentos(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Indexa todos los documentos de la base de datos en Qdrant.
        
        Args:
            limit: Límite de documentos a indexar (opcional)
            
        Returns:
            Dict[str, int]: Estadísticas de la operación
        """
        try:
            # Obtener documentos
            query = DocumentoSimplificado.objects.all()
            if limit:
                query = query[:limit]
                
            total = query.count()
            logger.info(f"Indexando {total} documentos en Qdrant")
            
            # Estadísticas
            stats = {
                "total": total,
                "exitosos": 0,
                "fallidos": 0
            }
            
            # Indexar cada documento
            for documento in query:
                if self.indexar_documento(documento):
                    stats["exitosos"] += 1
                else:
                    stats["fallidos"] += 1
                    
                # Mostrar progreso cada 10 documentos
                if (stats["exitosos"] + stats["fallidos"]) % 10 == 0:
                    logger.info(f"Progreso: {stats['exitosos'] + stats['fallidos']}/{total}")
            
            logger.info(f"Indexación completada. Exitosos: {stats['exitosos']}, Fallidos: {stats['fallidos']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error al indexar documentos: {str(e)}")
            return {"total": 0, "exitosos": 0, "fallidos": 0, "error": str(e)}
    
    def buscar_similares(
        self, 
        texto: str, 
        limit: int = 10, 
        score_threshold: float = 0.3,
        filtros: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos similares al texto proporcionado.
        
        Args:
            texto: Texto para buscar documentos similares
            limit: Número máximo de resultados
            score_threshold: Umbral mínimo de similitud (0-1)
            filtros: Filtros adicionales para la búsqueda
            
        Returns:
            List[Dict[str, Any]]: Lista de documentos similares
        """
        try:
            # Verificar estado de Qdrant antes de buscar
            estado = self.verificar_estado()
            if not estado.get('coleccion_existe') or estado.get('total_documentos', 0) == 0:
                logger.error(f"Qdrant no está listo: {estado}")
                raise Exception(f"Qdrant no está listo: {estado}")
                
            # Preprocesar el texto de búsqueda para mejorar resultados con consultas largas
            texto_procesado = self._preprocesar_consulta(texto)
            logger.info(f"Búsqueda semántica con texto procesado: '{texto_procesado}'")
            
            # Generar embedding para el texto de búsqueda
            query_vector = self.generar_embedding(texto_procesado)
            
            # Preparar parámetros de búsqueda
            search_params = {
                "collection_name": COLLECTION_NAME,
                "query_vector": query_vector.tolist(),
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True,
            }
            
            # Añadir filtros si existen
            if filtros:
                conditions = []
                
                if "departamento" in filtros and filtros["departamento"]:
                    conditions.append(
                        models.FieldCondition(
                            key="departamento",
                            match={"value": filtros["departamento"]}
                        )
                    )
                
                if "fecha_desde" in filtros and filtros["fecha_desde"]:
                    conditions.append(
                        models.FieldCondition(
                            key="fecha_publicacion",
                            range={"gte": filtros["fecha_desde"].isoformat()}
                        )
                    )
                
                if "fecha_hasta" in filtros and filtros["fecha_hasta"]:
                    conditions.append(
                        models.FieldCondition(
                            key="fecha_publicacion",
                            range={"lte": filtros["fecha_hasta"].isoformat()}
                        )
                    )
                
                if conditions:
                    search_params["filter"] = models.Filter(
                        must=conditions
                    )
            
            # Realizar búsqueda
            search_result = self.client.search(**search_params)
            
            # Formatear resultados
            resultados = []
            for hit in search_result:
                resultado = hit.payload.copy()
                resultado["score"] = hit.score
                resultados.append(resultado)
            
            logger.info(f"Búsqueda completada. Se encontraron {len(resultados)} documentos similares")
            return resultados
            
        except Exception as e:
            logger.error(f"Error al buscar documentos similares: {str(e)}")
            return []

    def _preprocesar_consulta(self, texto: str) -> str:
        """
        Preprocesa una consulta para mejorar los resultados de búsqueda.
        Especialmente útil para consultas largas o con múltiples conceptos.
        
        Args:
            texto: Texto de la consulta original
            
        Returns:
            str: Texto de consulta procesado
        """
        # Corregir errores tipográficos comunes
        correcciones = {
            "mnisterio": "ministerio",
            "haceienda": "hacienda",
            "govierno": "gobierno",
            "educacion": "educación",
            "publico": "público",
            "economica": "económica",
            "administracion": "administración",
            "ley": "ley",
            "decreto": "decreto",
            "resolucion": "resolución",
            "orden": "orden",
            "boe": "boe"
        }
        
        palabras = texto.split()
        palabras_corregidas = []
        
        for palabra in palabras:
            palabra_lower = palabra.lower()
            if palabra_lower in correcciones:
                palabras_corregidas.append(correcciones[palabra_lower])
            else:
                palabras_corregidas.append(palabra)
        
        texto = " ".join(palabras_corregidas)
        
        # Si la consulta es muy larga, intentamos extraer los términos más relevantes
        if len(texto.split()) > 5:
            # Reducimos la lista de palabras comunes para mantener más términos relevantes
            # Solo eliminamos palabras muy comunes que no aportan significado semántico
            palabras_comunes = ["y", "a", "por", "con", "un", "una"]
            palabras = [palabra for palabra in texto.split() if palabra.lower() not in palabras_comunes]
            
            # Si después de eliminar palabras comunes tenemos suficientes términos, usamos esos
            if len(palabras) >= 3:
                texto_procesado = " ".join(palabras)
                logger.info(f"Consulta procesada: '{texto}' -> '{texto_procesado}'")
                return texto_procesado
        
        # Si la consulta es corta o no se pudo procesar, la devolvemos tal cual
        logger.info(f"Consulta sin procesar: '{texto}'")
        return texto

    def buscar_por_palabras_clave(self, texto: str, limite: int = 10, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda por palabras clave en la base de datos.
        
        Args:
            texto: Texto de la consulta
            limite: Número máximo de resultados
            filtros: Filtros adicionales para la búsqueda
            
        Returns:
            List[Dict[str, Any]]: Lista de documentos que coinciden con la búsqueda
        """
        from .models_simplified import DocumentoSimplificado
        from django.db.models import Q
        
        try:
            # Dividir la consulta en palabras
            palabras = texto.split()
            
            # Construir consulta para buscar documentos que contengan cualquiera de las palabras
            query = Q()
            for palabra in palabras:
                if len(palabra) > 2:  # Ignorar palabras muy cortas
                    query |= Q(titulo__icontains=palabra) | Q(texto__icontains=palabra)
            
            # Aplicar filtros adicionales si existen
            if filtros:
                if 'departamento' in filtros and filtros['departamento']:
                    query &= Q(departamento__icontains=filtros['departamento'])
                
                if 'fecha_desde' in filtros and filtros['fecha_desde']:
                    query &= Q(fecha__gte=filtros['fecha_desde'])
                
                if 'fecha_hasta' in filtros and filtros['fecha_hasta']:
                    query &= Q(fecha__lte=filtros['fecha_hasta'])
            
            # Ejecutar la consulta
            resultados = DocumentoSimplificado.objects.filter(query).order_by('-fecha')[:limite]
            
            # Formatear resultados
            resultados_formateados = []
            for doc in resultados:
                resultados_formateados.append({
                    'id': doc.identificador,
                    'titulo': doc.titulo,
                    'fecha': doc.fecha.strftime('%Y-%m-%d') if doc.fecha else None,
                    'departamento': doc.departamento,
                    'rango': doc.rango,
                    'score': 1.0,  # Score fijo para resultados de palabras clave
                    'origen': 'palabras_clave'
                })
            
            return resultados_formateados
            
        except Exception as e:
            logger.error(f"Error en búsqueda por palabras clave: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def busqueda_hibrida(self, texto: str, limite: int = 10, score_threshold: float = 0.1, filtros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Realiza una búsqueda híbrida combinando resultados de búsqueda semántica y por palabras clave.
        
        Args:
            texto: Texto de la consulta
            limite: Número máximo de resultados
            score_threshold: Umbral mínimo de similitud para resultados semánticos
            filtros: Filtros adicionales para la búsqueda
            
        Returns:
            Dict[str, Any]: Resultados combinados de ambas búsquedas
        """
        try:
            resultados_combinados = []
            
            # Realizar búsqueda por palabras clave primero (siempre funciona)
            logger.info(f"Realizando búsqueda por palabras clave para: '{texto}'")
            resultados_keywords = self.buscar_por_palabras_clave(texto, limite=limite, filtros=filtros)
            
            # Añadir resultados de palabras clave
            ids_vistos = set()
            for doc in resultados_keywords:
                ids_vistos.add(doc['id'])
                resultados_combinados.append(doc)
            
            # Intentar realizar búsqueda semántica si es posible
            try:
                logger.info(f"Intentando búsqueda semántica para: '{texto}'")
                # Verificar estado de Qdrant antes de buscar
                estado = self.verificar_estado()
                if not estado.get('coleccion_existe') or estado.get('total_documentos', 0) == 0:
                    logger.error(f"Qdrant no está listo: {estado}")
                    raise Exception(f"Qdrant no está listo: {estado}")
                
                resultados_semanticos = self.buscar_similares(
                    texto, 
                    limit=limite, 
                    score_threshold=score_threshold, 
                    filtros=filtros
                )
                
                # Añadir resultados semánticos que no estén ya incluidos
                for doc in resultados_semanticos:
                    if doc['id'] not in ids_vistos:
                        ids_vistos.add(doc['id'])
                        doc['origen'] = 'semantica'
                        resultados_combinados.append(doc)
                
                tipo_busqueda = 'hibrida'
                logger.info(f"Búsqueda híbrida exitosa: {len(resultados_keywords)} por palabras clave + {len(resultados_semanticos)} semánticos")
            except Exception as e:
                logger.warning(f"Error en búsqueda semántica, usando solo palabras clave: {str(e)}")
                import traceback
                logger.warning(traceback.format_exc())
                tipo_busqueda = 'palabras_clave'
            
            # Ordenar por score descendente
            resultados_combinados = sorted(resultados_combinados, key=lambda x: x['score'], reverse=True)
            
            # Limitar al número máximo de resultados
            resultados_combinados = resultados_combinados[:limite]
            
            return {
                'total': len(resultados_combinados),
                'resultados': resultados_combinados,
                'consulta_original': texto,
                'tipo_busqueda': tipo_busqueda
            }
            
        except Exception as e:
            logger.error(f"Error en búsqueda híbrida: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'total': 0,
                'resultados': [],
                'consulta_original': texto,
                'tipo_busqueda': 'error',
                'error': str(e)
            }

    def buscar_por_palabras_clave_lista(
        self, 
        palabras_clave: List[str], 
        limit: int = 10,
        filtros: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos que contengan las palabras clave especificadas.
        
        Args:
            palabras_clave: Lista de palabras clave
            limit: Número máximo de resultados
            filtros: Filtros adicionales para la búsqueda
            
        Returns:
            List[Dict[str, Any]]: Lista de documentos que contienen las palabras clave
        """
        # Convertir lista de palabras clave a texto para búsqueda semántica
        texto_busqueda = " ".join(palabras_clave)
        return self.buscar_similares(texto_busqueda, limit, 0.6, filtros)
    
    def eliminar_documento(self, identificador: str) -> bool:
        """
        Elimina un documento de Qdrant.
        
        Args:
            identificador: Identificador del documento a eliminar
            
        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            # Generar UUID a partir del identificador
            punto_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, identificador))
            
            self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=[punto_id]
                )
            )
            
            logger.info(f"Documento {identificador} eliminado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar documento {identificador}: {str(e)}")
            return False
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la colección.
        
        Returns:
            Dict[str, Any]: Estadísticas de la colección
        """
        try:
            stats = self.client.get_collection(collection_name=COLLECTION_NAME)
            return {
                "vectores": stats.vectors_count,
                "puntos": stats.points_count,
                "segmentos": stats.segments_count,
                "status": stats.status,
                "optimizers_status": stats.optimizer_status,
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return {"error": str(e)}

    def verificar_estado(self) -> Dict[str, Any]:
        """
        Verifica el estado de la conexión con Qdrant y de la colección.
        
        Returns:
            Dict[str, Any]: Información sobre el estado de Qdrant y la colección
        """
        try:
            # Verificar si el cliente está conectado
            # Nota: No todas las versiones de Qdrant tienen el método health()
            # Intentamos obtener la lista de colecciones como prueba de conexión
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            coleccion_existe = COLLECTION_NAME in collection_names
            info_coleccion = None
            
            if coleccion_existe:
                # Obtener información de la colección
                info = self.client.get_collection(COLLECTION_NAME)
                info_coleccion = {
                    "vectores_indexados": info.vectors_count,
                    "dimensiones": info.config.params.vectors.size,
                    "puntos_indexados": info.points_count
                }
            
            return {
                "estado_conexion": "ok",
                "url_qdrant": self.url,
                "coleccion_existe": coleccion_existe,
                "nombre_coleccion": COLLECTION_NAME,
                "info_coleccion": info_coleccion,
                "todas_colecciones": collection_names
            }
            
        except Exception as e:
            logger.error(f"Error al verificar estado de Qdrant: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "estado_conexion": "error",
                "error": str(e),
                "url_qdrant": self.url
            }


# Función para obtener una instancia de QdrantBOE
def get_qdrant_client() -> QdrantBOE:
    """
    Obtiene una instancia de QdrantBOE.
    
    Returns:
        QdrantBOE: Instancia de QdrantBOE
    """
    url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
    api_key = getattr(settings, "QDRANT_API_KEY", os.environ.get("QDRANT_API_KEY"))
    
    return QdrantBOE(url=url, api_key=api_key)
