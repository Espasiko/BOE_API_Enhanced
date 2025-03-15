import os
import sys
import logging
import re
import io
from dotenv import load_dotenv
from mistralai import Mistral
from cohere import Client as CohereClient

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurar clientes de API
mistral_api_key = os.getenv('MISTRAL_API_KEY')
mistral_model = os.getenv('MISTRAL_MODEL', 'mistral-medium')
mistral_client = Mistral(api_key=mistral_api_key)

cohere_api_key = os.getenv('COHERE_API_KEY', 'Cz5uxPlfvNKq2zT3Vhk4KXxx3f13dRzVtoXYIylS')
cohere_client = CohereClient(api_key=cohere_api_key)

# Configuración de Qdrant (mantenemos la compatibilidad)
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

# Nombre correcto de la colección en Qdrant
QDRANT_COLLECTION_NAME = "boe_documentos"  # Nombre correcto de la colección

# Funciones específicas para el comparador de versiones
def buscar_documentos_boe(query, max_results=5):
    """
    Busca documentos del BOE usando Cohere
    """
    try:
        response = cohere_client.chat(
            message=f"""Busca documentos del BOE relacionados con: {query}
            
            Proporciona una lista de documentos relevantes con la siguiente información para cada uno:
            1. Referencia del documento (código BOE)
            2. Título del documento
            3. Fecha de publicación en formato DD/MM/YYYY
            4. URL del documento (debe ser una URL válida del BOE)
            5. Breve descripción del contenido
            
            Formatea la respuesta en JSON con la estructura adecuada.
            """,
            model="command-r",
            temperature=0.2
        )
        return response.text
    except Exception as e:
        logging.error(f"Error en buscar_documentos_boe: {e}")
        return f"Error al buscar documentos: {str(e)}"

def obtener_versiones_documento(referencia):
    """
    Obtiene las versiones disponibles de un documento del BOE
    """
    try:
        response = cohere_client.chat(
            message=f"""Busca las diferentes versiones del documento del BOE con referencia {referencia}.
            
            Proporciona una lista de todas las versiones disponibles con la siguiente información para cada una:
            1. Identificador de la versión
            2. Nombre descriptivo de la versión
            3. Fecha de publicación
            
            Formatea la respuesta en JSON con la estructura adecuada.
            """,
            model="command-r",
            temperature=0.2
        )
        return response.text
    except Exception as e:
        logging.error(f"Error en obtener_versiones_documento: {e}")
        return f"Error al obtener versiones: {str(e)}"

def comparar_versiones_documento(referencia, version_original, version_comparar):
    """
    Compara dos versiones de un documento del BOE
    """
    try:
        response = cohere_client.chat(
            message=f"""Analiza las diferencias entre dos versiones del documento del BOE con referencia {referencia}.
            
            Versión original: {version_original}
            Versión a comparar: {version_comparar}
            
            Proporciona un análisis detallado de las diferencias entre ambas versiones. Debes seguir EXACTAMENTE este formato de respuesta en JSON:

            ```json
            {{
                "comparacion": "Resumen general de los cambios entre las versiones",
                "estadisticas": {{
                    "adiciones": 5,
                    "eliminaciones": 3,
                    "modificaciones": 7
                }},
                "cambios_detallados": [
                    {{
                        "seccion": "Artículo 1",
                        "tipo_cambio": "modificación",
                        "descripcion": "Se ha modificado la redacción del artículo",
                        "texto_original": "Texto original del artículo",
                        "texto_nuevo": "Nuevo texto del artículo"
                    }},
                    {{
                        "seccion": "Artículo 2",
                        "tipo_cambio": "adición",
                        "descripcion": "Se ha añadido un nuevo artículo",
                        "texto_original": "",
                        "texto_nuevo": "Texto del nuevo artículo"
                    }},
                    {{
                        "seccion": "Artículo 3",
                        "tipo_cambio": "eliminación",
                        "descripcion": "Se ha eliminado este artículo",
                        "texto_original": "Texto del artículo eliminado",
                        "texto_nuevo": ""
                    }}
                ]
            }}
            ```

            Es IMPRESCINDIBLE que sigas este formato exacto y que proporciones valores numéricos (no texto) para las estadísticas. Los tipos de cambio deben ser únicamente: "adición", "eliminación" o "modificación".
            
            Para cada cambio, incluye la sección o artículo afectado, una descripción del cambio, el texto original y el texto nuevo.
            """,
            model="command-r",
            temperature=0.2,
            max_tokens=4000
        )
        return response.text
    except Exception as e:
        logging.error(f"Error en comparar_versiones_documento: {e}")
        return f"Error al comparar versiones: {str(e)}"

def planning_agent(prompt):
    """Agente de planificación usando Mistral"""
    try:
        messages = [{"role": "user", "content": prompt}]
        response = mistral_client.chat.complete(
            model=mistral_model,
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error en planning_agent: {e}")
        return "No se pudo procesar la solicitud."

def summarization_agent(text):
    """Agente de resumen usando Cohere"""
    try:
        response = cohere_client.summarize(
            text=text,
            model='command',
            length='medium'
        )
        return response.summary
    except Exception as e:
        logging.error(f"Error en summarization_agent: {e}")
        return "No se pudo generar el resumen."

def workflow(prompt, context=None):
    """Flujo de trabajo simplificado"""
    result = planning_agent(prompt)
    return result

# Clase para búsqueda en Qdrant (simplificada para usar Cohere)
class QdrantSearch:
    def __init__(self, collection_name=QDRANT_COLLECTION_NAME):
        self.collection_name = collection_name
        self._cache = {}
    
    def search(self, query, limit=5, exact_match_weight=0.6, semantic_weight=0.4):
        """Buscar documentos usando Cohere en lugar de Qdrant"""
        try:
            # Usar caché si existe
            cache_key = f"search_{query}_{limit}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            # Realizar búsqueda con Cohere
            response = cohere_client.chat(
                message=f"""Busca documentos del BOE relacionados con: {query}
                
                Proporciona una lista de {limit} documentos relevantes con la siguiente información para cada uno:
                1. Identificador único del documento
                2. Título del documento
                3. Texto completo o extracto relevante
                4. URL del documento en el BOE
                5. Porcentaje de relevancia con respecto a la consulta
                
                Formatea la respuesta en JSON.
                """,
                model="command-r",
                temperature=0.2
            )
            
            # Procesar respuesta
            texto_respuesta = response.text
            
            # Intentar extraer JSON de la respuesta
            import json
            json_match = re.search(r'```json\n(.*?)\n```', texto_respuesta, re.DOTALL)
            
            if json_match:
                resultados = json.loads(json_match.group(1))
            else:
                # Si no se encuentra JSON con formato de código, buscar cualquier JSON válido
                json_match = re.search(r'({[\s\S]*})', texto_respuesta)
                if json_match:
                    try:
                        resultados = json.loads(json_match.group(1))
                    except:
                        # Si no se puede parsear, crear resultados básicos
                        resultados = {
                            "documentos": []
                        }
                else:
                    # Si no se encuentra ningún JSON, crear resultados básicos
                    resultados = {
                        "documentos": []
                    }
            
            # Guardar en caché
            self._cache[cache_key] = resultados
            
            return resultados
            
        except Exception as e:
            logging.error(f"Error en QdrantSearch.search: {e}")
            return {"documentos": []}
    
    def process_query(self, query, context=None):
        """Procesar consulta con Mistral"""
        try:
            # Buscar documentos relevantes
            search_results = self.search(query)
            
            # Preparar contexto para Mistral
            context_str = ""
            if "documentos" in search_results:
                for i, doc in enumerate(search_results["documentos"]):
                    context_str += f"\nDocumento {i+1}:\n"
                    context_str += f"Título: {doc.get('titulo', 'Sin título')}\n"
                    context_str += f"Texto: {doc.get('texto', 'Sin texto')}\n"
                    context_str += f"URL: {doc.get('url', 'Sin URL')}\n"
                    context_str += f"Relevancia: {doc.get('relevancia', '0')}%\n"
            
            # Procesar con Mistral
            prompt = f"""Consulta: {query}
            
            Contexto de documentos del BOE:
            {context_str}
            
            Responde a la consulta basándote en la información proporcionada en los documentos. 
            Si la información no es suficiente, indícalo claramente.
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = mistral_client.chat.complete(
                model=mistral_model,
                messages=messages,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error en QdrantSearch.process_query: {e}")
            return f"Error al procesar la consulta: {str(e)}"
    
    def summarize_document(self, document_id, query=None):
        """Resumir documento usando Cohere"""
        try:
            # Obtener documento (simulado)
            document_text = f"Documento con ID {document_id} relacionado con la consulta: {query}"
            
            # Resumir con Cohere
            response = cohere_client.summarize(
                text=document_text,
                model='command',
                length='medium',
                format='paragraph'
            )
            
            return response.summary
            
        except Exception as e:
            logging.error(f"Error en QdrantSearch.summarize_document: {e}")
            return f"Error al resumir el documento: {str(e)}"

# Clase base para agentes
class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.cache = {}
    
    def preprocess_query(self, query):
        """Preprocesar la consulta"""
        return query
    
    def postprocess_response(self, response):
        """Postprocesar la respuesta"""
        return response
    
    def validate_query(self, query):
        """Validar la consulta"""
        return True
    
    def validate_response(self, response):
        """Validar la respuesta"""
        return True
    
    def get_from_cache(self, query):
        """Obtener respuesta de la caché"""
        return self.cache.get(query)
    
    def add_to_cache(self, query, response):
        """Añadir respuesta a la caché"""
        self.cache[query] = response
    
    def run(self, query):
        """Ejecutar el agente"""
        # Verificar caché
        cached_response = self.get_from_cache(query)
        if cached_response:
            return cached_response
        
        # Preprocesar
        processed_query = self.preprocess_query(query)
        
        # Validar
        if not self.validate_query(processed_query):
            return "Consulta no válida"
        
        # Ejecutar lógica específica del agente
        response = "No implementado"
        
        # Postprocesar
        processed_response = self.postprocess_response(response)
        
        # Validar respuesta
        if not self.validate_response(processed_response):
            return "Respuesta no válida"
        
        # Guardar en caché
        self.add_to_cache(query, processed_response)
        
        return processed_response

# Agente de planificación
class PlanningAgent(Agent):
    def run(self, query):
        """Ejecutar el agente de planificación"""
        # Verificar caché
        cached_response = self.get_from_cache(query)
        if cached_response:
            return cached_response
        
        try:
            # Ejecutar con Mistral
            messages = [{"role": "user", "content": query}]
            response = mistral_client.chat.complete(
                model=mistral_model,
                messages=messages,
                stream=False
            )
            
            result = response.choices[0].message.content
            
            # Guardar en caché
            self.add_to_cache(query, result)
            
            return result
            
        except Exception as e:
            logging.error(f"Error en PlanningAgent.run: {e}")
            return f"Error en el agente de planificación: {str(e)}"

# Agente de resumen
class SummarizationAgent(Agent):
    def run(self, query):
        """Ejecutar el agente de resumen"""
        # Verificar caché
        cached_response = self.get_from_cache(query)
        if cached_response:
            return cached_response
        
        try:
            # Ejecutar con Cohere
            response = cohere_client.summarize(
                text=query,
                model='command',
                length='medium',
                format='paragraph'
            )
            
            result = response.summary
            
            # Guardar en caché
            self.add_to_cache(query, result)
            
            return result
            
        except Exception as e:
            logging.error(f"Error en SummarizationAgent.run: {e}")
            return f"Error en el agente de resumen: {str(e)}"

# Agente de Python
class PythonAgent(Agent):
    def extract_code(self, text):
        """Extrae el código Python del texto dado."""
        code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        return text
    
    def run_code(self, code):
        """Ejecuta el código Python y verifica si hay errores."""
        try:
            # Capturar la salida
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            
            # Ejecutar código
            exec(code)
            
            # Restaurar stdout
            sys.stdout = old_stdout
            
            return redirected_output.getvalue()
        except Exception as e:
            return f"Error al ejecutar el código: {str(e)}"

# Flujo de trabajo para el agente de Python
class PythonAgentWorkflow:
    def __init__(self, planning_agent, python_agent, summarization_agent):
        self.planning_agent = planning_agent
        self.python_agent = python_agent
        self.summarization_agent = summarization_agent
        self.state = {}
    
    def run(self, query):
        """Ejecutar el flujo de trabajo completo"""
        try:
            # Paso 1: Planificación
            planning_prompt = f"""Analiza la siguiente consulta y genera código Python para resolverla:
            
            {query}
            
            Proporciona solo el código Python necesario, sin explicaciones adicionales.
            """
            
            code_plan = self.planning_agent.run(planning_prompt)
            
            # Paso 2: Extraer y ejecutar código
            code = self.python_agent.extract_code(code_plan)
            code_output = self.python_agent.run_code(code)
            
            # Paso 3: Resumir resultados
            summary_prompt = f"""Consulta original: {query}
            
            Resultado de la ejecución del código:
            {code_output}
            
            Resume los resultados de manera clara y concisa.
            """
            
            summary = self.summarization_agent.run(summary_prompt)
            
            # Combinar resultados
            result = f"""Respuesta a tu consulta:
            
            {summary}
            
            Detalles técnicos:
            {code_output}
            """
            
            return result
            
        except Exception as e:
            logging.error(f"Error en PythonAgentWorkflow.run: {e}")
            return f"Error en el flujo de trabajo: {str(e)}"

# Captura de la salida de print
class Tee(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_stdout = sys.stdout
    
    def write(self, data):
        self.original_stdout.write(data)
        return super().write(data)
    
    def flush(self):
        self.original_stdout.flush()
        return super().flush()

# Crear instancias de los agentes con los IDs correctos
planning_agent = PlanningAgent("ag:977f4f16:20250311:planningagent:ede524f0")
python_agent = PythonAgent("ag:977f4f16:20250311:pythonagent:19b69527")
summarization_agent = SummarizationAgent("ag:977f4f16:20250311:summarizationagent:6aaba406")

# Crear instancia del flujo de trabajo
workflow_instance = PythonAgentWorkflow(planning_agent, python_agent, summarization_agent)

def run_workflow(query):
    """Ejecuta el flujo de trabajo completo con la consulta dada."""
    return workflow_instance.run(query)

def procesar_consulta(query):
    """Procesa una consulta y devuelve los resultados."""
    try:
        # Determinar el tipo de consulta
        if query.lower().startswith(("buscar", "encuentra", "localiza")):
            # Búsqueda de documentos
            qdrant_search = QdrantSearch()
            return qdrant_search.search(query)
        elif query.lower().startswith(("analiza", "resume", "explica")):
            # Análisis o resumen
            return summarization_agent.run(query)
        elif query.lower().startswith(("calcula", "programa", "código")):
            # Ejecución de código
            return run_workflow(query)
        else:
            # Consulta general
            qdrant_search = QdrantSearch()
            return qdrant_search.process_query(query)
    except Exception as e:
        logging.error(f"Error en procesar_consulta: {e}")
        return f"Error al procesar la consulta: {str(e)}"
