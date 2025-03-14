import os
import re
import sys
import io
import logging
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from mistralai import Mistral
from transformers import pipeline

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración del cliente de Qdrant
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

# Configuración del cliente de Mistral
mistral_api_key = os.getenv("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=mistral_api_key)

# Configuración del modelo de embeddings
embedding_model = pipeline("feature-extraction", model="sentence-transformers/all-MiniLM-L6-v2")

# Nombre correcto de la colección en Qdrant
QDRANT_COLLECTION_NAME = "boe_documentos"  # Nombre correcto de la colección

class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.cache = {}

    def preprocess_query(self, query):
        # Lógica de preprocesamiento
        return query

    def postprocess_response(self, response):
        # Lógica de postprocesamiento
        return response

    def validate_query(self, query):
        # Lógica de validación de la consulta
        if not query:
            raise ValueError("La consulta no puede estar vacía")
        return query

    def validate_response(self, response):
        # Lógica de validación de la respuesta
        if not response:
            raise ValueError("La respuesta no puede estar vacía")
        return response

    def get_from_cache(self, query):
        return self.cache.get(query)

    def add_to_cache(self, query, response):
        self.cache[query] = response

    def run(self, query):
        try:
            query = self.preprocess_query(query)
            query = self.validate_query(query)

            cached_response = self.get_from_cache(query)
            if cached_response:
                return cached_response

            response = client.search(
                collection_name=self.agent_id,
                query_vector=query,
                limit=5  # Número de resultados a devolver
            )
            response = self.validate_response(response)
            response = self.postprocess_response(response)
            self.add_to_cache(query, response)
            return response
        except Exception as e:
            logging.error(f"Error al ejecutar el agente {self.agent_id}: {e}")
            return None

class PlanningAgent(Agent):
    def run(self, query):
        try:
            query = self.preprocess_query(query)
            query = self.validate_query(query)

            cached_response = self.get_from_cache(query)
            if cached_response:
                return cached_response

            # Generar embedding para la consulta
            embeddings = embedding_model(query)
            query_vector = embeddings[0][0]  # Obtener el vector de embedding

            # Buscar en Qdrant
            logging.info(f"Buscando en Qdrant con la consulta: {query}")
            try:
                search_results = client.search(
                    collection_name=QDRANT_COLLECTION_NAME,  # Usar la variable global
                    query_vector=query_vector,
                    limit=5  # Número de resultados a devolver
                )
            except Exception as qdrant_error:
                logging.error(f"Error al buscar en Qdrant: {str(qdrant_error)}")
                # Intentar listar las colecciones disponibles para diagnóstico
                try:
                    collections = client.get_collections()
                    available_collections = [collection.name for collection in collections.collections]
                    logging.info(f"Colecciones disponibles en Qdrant: {available_collections}")
                    context = f"Error al buscar en Qdrant: {str(qdrant_error)}. Colecciones disponibles: {available_collections}"
                except:
                    context = f"Error al buscar en Qdrant: {str(qdrant_error)}. No se pudo obtener la lista de colecciones disponibles."
                
                # Continuar con Mistral aunque falle Qdrant
                search_results = []
            
            if not search_results:
                logging.warning("No se encontraron resultados en Qdrant")
                if 'context' not in locals():
                    context = "No se encontraron documentos relevantes en la base de datos del BOE."
            else:
                # Extraer el contenido de los resultados
                context = "Documentos relevantes encontrados en el BOE:\n\n"
                for i, result in enumerate(search_results):
                    doc_info = result.payload
                    context += f"Documento {i+1}:\n"
                    context += f"Título: {doc_info.get('titulo', 'Sin título')}\n"
                    context += f"Fecha: {doc_info.get('fecha_publicacion', 'Sin fecha')}\n"
                    context += f"Departamento: {doc_info.get('departamento', 'Sin departamento')}\n"
                    context += f"Contenido: {doc_info.get('texto', 'Sin contenido')[:500]}...\n\n"

            # Generar prompt para Mistral con los resultados de Qdrant
            prompt = f"""Eres un asistente especializado en analizar consultas sobre el BOE (Boletín Oficial del Estado).
            Tu tarea es entender la consulta del usuario y proporcionar una respuesta basada en los documentos encontrados.
            
            Consulta del usuario: {query}
            
            Información relevante del BOE:
            {context}
            
            Por favor, analiza la consulta y la información proporcionada, y genera:
            1. Un resumen de los documentos relevantes encontrados
            2. Los aspectos clave que responden a la consulta del usuario
            3. Recomendaciones basadas en la legislación encontrada
            """

            # Usar el cliente de Mistral con el contexto de Qdrant
            messages = [{"role": "user", "content": prompt}]
            response = mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                stream=False
            )

            if not response or not response.choices:
                raise ValueError("La API de Mistral no devolvió un resultado válido.")

            result = response.choices[0].message.content
            result = self.validate_response(result)
            result = self.postprocess_response(result)
            self.add_to_cache(query, result)
            return result

        except Exception as e:
            logging.error(f"Error en PlanningAgent.run: {str(e)}")
            return f"Error al procesar la consulta: {str(e)}"

class SummarizationAgent(Agent):
    def run(self, query):
        try:
            query = self.preprocess_query(query)
            query = self.validate_query(query)

            cached_response = self.get_from_cache(query)
            if cached_response:
                return cached_response

            # Resumir el contenido usando el agente de Mistral
            messages = [{"role": "user", "content": query}]
            summary = mistral_client.chat.complete(
                model="mistral-large-latest", 
                messages=messages,
                stream=False
            )
            if not summary or not summary.choices:
                raise ValueError("La API de Mistral no devolvió un resultado válido.")
            response = summary.choices[0].message.content
            response = self.validate_response(response)
            response = self.postprocess_response(response)
            self.add_to_cache(query, response)
            return response
        except Exception as e:
            logging.error(f"Error al ejecutar el agente {self.agent_id}: {e}")
            return None

class PythonAgent(Agent):
    def extract_code(self, text):
        """Extrae el código Python del texto dado."""
        pattern = r'```python(.*?)```'
        match = re.search(pattern, text, flags=re.DOTALL)
        return match.group(1).strip() if match else None

    def run_code(self, code):
        """Ejecuta el código Python y verifica si hay errores."""
        try:
            exec(code, globals())
            logging.info("Código ejecutado con éxito.")
            return False
        except Exception as e:
            logging.error(f"Error al ejecutar el código: {e}")
            return True

class PythonAgentWorkflow:
    def __init__(self, planning_agent, python_agent, summarization_agent):
        self.planning_agent = planning_agent
        self.python_agent = python_agent
        self.summarization_agent = summarization_agent
        self.state = {}

    def run(self, query):
        try:
            # Paso 1: Generar un plan usando el agente de planificación
            logging.info("Generando plan con el agente de planificación...")
            plan = self.planning_agent.run(query)
            if not plan:
                return "No se pudo generar un plan para la consulta."

            # Paso 2: Extraer el código Python del plan
            logging.info("Extrayendo código Python del plan...")
            code = self.python_agent.extract_code(plan)
            if not code:
                return plan  # Si no hay código, devolver el plan como respuesta

            # Paso 3: Ejecutar el código Python
            logging.info("Ejecutando código Python...")
            has_error = self.python_agent.run_code(code)
            
            # Paso 4: Resumir los resultados
            logging.info("Resumiendo resultados...")
            if has_error:
                summary_query = f"El siguiente código Python tiene errores. Por favor, identifica y explica los errores:\n\n```python\n{code}\n```"
            else:
                summary_query = f"El siguiente código Python se ejecutó correctamente. Por favor, explica qué hace el código:\n\n```python\n{code}\n```"
            
            summary = self.summarization_agent.run(summary_query)
            
            # Combinar los resultados
            result = f"Plan:\n{plan}\n\nResumen:\n{summary}"
            return result
            
        except Exception as e:
            logging.error(f"Error en el flujo de trabajo: {e}")
            return f"Error en el flujo de trabajo: {e}"

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

# Crear el flujo de trabajo
workflow = PythonAgentWorkflow(planning_agent, python_agent, summarization_agent)

def run_workflow(query):
    """Ejecuta el flujo de trabajo completo con la consulta dada."""
    return workflow.run(query)

def procesar_consulta(query):
    """Procesa una consulta y devuelve los resultados."""
    try:
        # Capturar la salida de print
        old_stdout = sys.stdout
        tee = Tee()
        sys.stdout = tee
        
        # Ejecutar el flujo de trabajo
        result = run_workflow(query)
        
        # Restaurar la salida estándar
        sys.stdout = old_stdout
        
        # Devolver el resultado y la salida capturada
        return {
            "result": result,
            "output": tee.getvalue()
        }
    except Exception as e:
        logging.error(f"Error al procesar la consulta: {e}")
        return {
            "result": f"Error al procesar la consulta: {e}",
            "output": ""
        }
