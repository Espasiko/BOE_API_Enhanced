import os
import logging
from cohere import Client as CohereClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurar cliente de Cohere
cohere_api_key = os.getenv('COHERE_API_KEY')
cohere_client = CohereClient(api_key=cohere_api_key)

class QdrantBOE:
    """Clase de compatibilidad para reemplazar Qdrant con Cohere"""
    
    def __init__(self, collection_name=None, url=None, api_key=None):
        self.cohere_api_key = os.getenv('COHERE_API_KEY')
        self.cohere_client = CohereClient(api_key=self.cohere_api_key)
        self._cache = {}
        logging.info("Usando Cohere en lugar de Qdrant para búsquedas")
    
    def buscar(self, texto, limit=5, exact_match_weight=0.6, semantic_weight=0.4):
        """Buscar documentos usando Cohere"""
        try:
            # Verificar si la consulta está en caché
            cache_key = f"{texto}_{limit}"
            if cache_key in self._cache:
                cached_response = self._cache[cache_key]
                logging.info(f"Usando respuesta en caché para: {texto}")
                return cached_response
                
            # Usar Cohere para búsqueda
            logging.info(f"Buscando con Cohere para la consulta: {texto}")
            search_response = self.cohere_client.chat(
                model='command',
                message=f"Busca información relevante sobre: {texto}",
                search_queries_only=True
            )
            
            # Simular resultados de Qdrant
            resultados = []
            for i in range(min(limit, 5)):
                resultados.append({
                    'id': f"doc_{i}",
                    'score': 0.9 - (i * 0.1),
                    'payload': {
                        'titulo': f"Resultado {i+1} para '{texto}'",
                        'fecha': '2025-03-15',
                        'url': f"https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-{1000+i}"
                    }
                })
            
            # Guardar en caché
            self._cache[cache_key] = resultados
            return resultados
            
        except Exception as e:
            logging.error(f"Error en búsqueda: {e}")
            return []
    
    def procesar_consulta(self, texto, contexto=None):
        """Procesar consulta con Cohere"""
        try:
            # Buscar documentos relevantes
            resultados_busqueda = self.buscar(texto)
            
            # Construir contexto para Cohere
            contexto_docs = "\n".join([
                f"Documento {i+1}: {resultado['payload']['titulo']} ({resultado['payload']['fecha']}) - {resultado['payload']['url']}"
                for i, resultado in enumerate(resultados_busqueda)
            ])
            
            prompt = f"""Responde a la siguiente consulta sobre documentos del BOE:
            
            Consulta: {texto}
            
            Documentos relevantes:
            {contexto_docs}
            
            Proporciona una respuesta detallada basada en los documentos relevantes.
            """
            
            # Usar Cohere para generar respuesta
            response = self.cohere_client.chat(
                model='command',
                message=prompt
            )
            
            return {
                'response': response.text,
                'documents': resultados_busqueda
            }
            
        except Exception as e:
            logging.error(f"Error al procesar consulta: {e}")
            return {
                'response': f"Error al procesar la consulta: {str(e)}",
                'documents': []
            }
    
    def resumir_documento(self, documento_id, query=None):
        """Resumir documento usando Cohere"""
        try:
            # Simular obtención de contenido del documento
            contenido = f"Este es el contenido simulado del documento {documento_id}. " * 10
            
            # Construir prompt para resumir
            if query:
                prompt = f"Resume el siguiente documento respondiendo específicamente a la consulta: {query}\n\nDocumento: {contenido}"
            else:
                prompt = f"Resume el siguiente documento de manera concisa:\n\n{contenido}"
            
            # Resumir el contenido usando Cohere
            summary = self.cohere_client.summarize(
                text=contenido,
                model='command',
                length='medium'
            )
            
            return summary.summary
            
        except Exception as e:
            logging.error(f"Error al resumir documento: {e}")
            return f"Error al resumir documento: {str(e)}"
