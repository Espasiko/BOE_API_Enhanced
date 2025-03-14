"""
Servicios de IA para el análisis de documentos del BOE
Incluye funciones para clasificación y resumen de documentos
"""
import logging
import requests
from django.conf import settings

# Importar las librerías necesarias para OpenAI y Mistral
import openai
import json
import os

logger = logging.getLogger(__name__)

class ServicioIA:
    """
    Clase para servicios de IA aplicados a documentos del BOE
    Soporta tanto uso local de modelos como API en la nube
    """
    
    @staticmethod
    def _llamar_api_huggingface(texto, max_tokens=500):
        """
        Método interno para llamar a la API de HuggingFace
        
        Args:
            texto (str): Texto a procesar
            max_tokens (int): Número máximo de tokens a generar
            
        Returns:
            str: Respuesta de la API o None si hay error
        """
        try:
            import os
            import requests
            import json
            import time
            from django.conf import settings
            
            # Obtener la clave API de las variables de entorno o settings
            api_key = os.getenv("HUGGINGFACE_API_KEY") or getattr(settings, "HUGGINGFACE_API_KEY", None)
            
            if not api_key:
                print("Error: No se encontró la clave API de HuggingFace")
                return None
            
            # Modelo de resumen en español
            model_id = "BSC-TeMU/roberta-base-bne-capitel-ner"
            api_url = f"https://api-inference.huggingface.co/models/{model_id}"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Preparar el payload
            payload = {
                "inputs": texto[:4000],  # Limitar el texto para evitar errores
                "parameters": {
                    "max_length": max_tokens,
                    "min_length": 100,
                    "do_sample": True,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            print(f"Llamando a la API de HuggingFace con modelo: {model_id}")
            print(f"Longitud del texto: {len(texto)} caracteres (limitado a 4000)")
            
            # Aumentar el timeout para dar más tiempo a la respuesta
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            
            print(f"Código de respuesta: {response.status_code}")
            
            # Manejar diferentes códigos de estado
            if response.status_code == 200:
                # La petición fue exitosa
                try:
                    result = response.json()
                    print(f"Respuesta exitosa: {str(result)[:200]}...")
                    
                    # Procesar el resultado según el formato de respuesta
                    if isinstance(result, list) and len(result) > 0:
                        if "generated_text" in result[0]:
                            return result[0]["generated_text"]
                        elif "summary_text" in result[0]:
                            return result[0]["summary_text"]
                        else:
                            # Devolver el primer elemento si no tiene una estructura conocida
                            return str(result[0])
                    elif isinstance(result, dict):
                        if "generated_text" in result:
                            return result["generated_text"]
                        elif "summary_text" in result:
                            return result["summary_text"]
                        else:
                            # Devolver todo el diccionario como string si no tiene una estructura conocida
                            return str(result)
                    else:
                        # Si no es un formato conocido, devolver la respuesta como string
                        return str(result)
                except ValueError as e:
                    print(f"Error al procesar la respuesta JSON: {str(e)}")
                    # Si no es JSON, devolver el texto directo
                    return response.text
            
            elif response.status_code == 503:
                # El modelo está cargando, intentar de nuevo después de esperar
                print("El modelo está cargando. Esperando 10 segundos para volver a intentar...")
                time.sleep(10)
                return ServicioIA._llamar_api_huggingface(texto, max_tokens)
                
            else:
                print(f"Error HTTP: {response.status_code}")
                if response.status_code == 401:
                    print("Error de autenticación. Verifica tu API key.")
                elif response.status_code == 404:
                    print(f"Modelo no encontrado: {model_id}")
                    # Intentar con un modelo alternativo
                    print("Intentando con modelo alternativo...")
                    model_id = "PlanTL-GOB-ES/roberta-base-bne"
                    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
                    response = requests.post(api_url, headers=headers, json=payload, timeout=120)
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            print(f"Respuesta exitosa del modelo alternativo: {str(result)[:200]}...")
                            return str(result)
                        except:
                            return response.text
                
                print(f"Respuesta de error: {response.text[:500]}...")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error al llamar a la API de HuggingFace: {str(e)}")
            return None
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return None
    
    @staticmethod
    def _llamar_api_openai(texto, max_tokens=150):
        """
        Método interno para llamar a la API de OpenAI
        
        Args:
            texto (str): Texto a resumir
            max_tokens (int): Número máximo de tokens en la respuesta
            
        Returns:
            str: Resumen generado o mensaje de error
        """
        try:
            if not settings.OPENAI_API_KEY:
                return "No se ha configurado la clave API de OpenAI."
            
            print(f"Llamando a la API de OpenAI")
            
            # Configurar cliente
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Preparar el prompt para resumir texto en español
            prompt = f"""
            Necesito un resumen conciso del siguiente documento legal en español.
            El resumen debe capturar los puntos clave de forma objetiva y clara.
            
            Documento a resumir:
            {texto}
            
            Resumen:
            """
            
            # Llamar a la API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Puedes usar un modelo más potente si lo prefieres
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en resumir documentos legales y oficiales en español."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5
            )
            
            # Obtener el resumen
            resumen = response.choices[0].message.content.strip()
            print(f"Resumen generado con OpenAI: {resumen[:100]}...")
            
            return resumen
            
        except Exception as e:
            error_msg = f"Error al llamar a la API de OpenAI: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return f"No se pudo generar un resumen con OpenAI. Error: {str(e)}"
    
    @staticmethod
    def _llamar_api_mistral(texto, max_tokens=500):
        """
        Método interno para llamar a la API de Mistral
        
        Args:
            texto (str): Texto a resumir
            max_tokens (int): Número máximo de tokens en la respuesta
            
        Returns:
            str: Resumen generado o mensaje de error
        """
        try:
            if not settings.MISTRAL_API_KEY:
                return "No se ha configurado la clave API de Mistral."
            
            print(f"Llamando a la API de Mistral")
            
            # Endpoint de la API de Mistral
            api_url = "https://api.mistral.ai/v1/chat/completions"
            
            # Headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}"
            }
            
            # Payload con instrucciones explícitas para responder en español
            payload = {
                "model": "mistral-medium", # Cambiado de mistral-small a mistral-medium para mejor calidad
                "messages": [
                    {
                        "role": "system", 
                        "content": "Eres un asistente especializado en resumir documentos legales oficiales. SIEMPRE respondes en español. NUNCA respondes en inglés ni en otro idioma que no sea español. Tu tarea es crear resúmenes concisos y precisos de documentos legales del Boletín Oficial del Estado (BOE) de España. Debes generar un resumen completo y detallado, no solo mencionar el título del documento."
                    },
                    {
                        "role": "user", 
                        "content": f"""Por favor, resume el siguiente documento legal del BOE en español. 
                        Debes capturar los puntos clave de forma concisa y objetiva.
                        Es OBLIGATORIO que tu respuesta sea en español.
                        Es OBLIGATORIO que generes un resumen COMPLETO, no solo el título o la primera línea.
                        
                        Documento a resumir:
                        {texto}
                        
                        Resumen en español (mínimo 150 palabras):"""
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3
            }
            
            # Imprimir información de depuración
            print(f"Enviando solicitud a Mistral con payload: {payload}")
            
            # Llamar a la API
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            # Imprimir respuesta para depuración
            print(f"Respuesta de Mistral (status code): {response.status_code}")
            print(f"Respuesta de Mistral (headers): {response.headers}")
            print(f"Respuesta de Mistral (primeros 200 caracteres): {response.text[:200]}...")
            
            # Procesar la respuesta
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                resumen = result["choices"][0]["message"]["content"].strip()
                print(f"Resumen generado con Mistral (longitud: {len(resumen)} caracteres)")
                print(f"Resumen generado con Mistral (primeros 200 caracteres): {resumen[:200]}...")
                
                # Verificar que el resumen no esté vacío o sea demasiado corto
                if not resumen or len(resumen) < 50:
                    print("Error: Resumen demasiado corto o vacío")
                    return "No se pudo generar un resumen adecuado. El modelo generó un texto demasiado corto."
                
                # Verificar que el resumen no sea solo "Generado con Mistral"
                if "generado con mistral" in resumen.lower() and len(resumen) < 100:
                    print("Error: El resumen solo contiene 'Generado con Mistral'")
                    return "Error: El modelo solo devolvió 'Generado con Mistral' sin generar un resumen real."
                
                return resumen
            else:
                print(f"Formato de respuesta inesperado: {result}")
                return "No se pudo generar un resumen. Formato de respuesta inesperado."
                
        except Exception as e:
            error_msg = f"Error al llamar a la API de Mistral: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return f"No se pudo generar un resumen con Mistral. Error: {str(e)}"
    
    @staticmethod
    def _llamar_api_deepseek(texto, max_tokens=150):
        """
        Método interno para llamar a la API de DeepSeek
        
        Args:
            texto (str): Texto a resumir
            max_tokens (int): Número máximo de tokens en la respuesta
            
        Returns:
            str: Resumen generado o mensaje de error
        """
        try:
            if not settings.DEEPSEEK_API_KEY:
                return "No se ha configurado la clave API de DeepSeek."
            
            print(f"Llamando a la API de DeepSeek")
            
            # Configurar cliente
            client = openai.OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            
            # Preparar el prompt para resumir texto en español
            prompt = f"""
            Necesito un resumen detallado del siguiente documento legal en español.
            El resumen debe capturar los puntos clave de forma objetiva y clara.
            IMPORTANTE: Tu respuesta DEBE ser en español.
            
            Documento a resumir:
            {texto}
            
            Resumen en español (mínimo 150 palabras):
            """
            
            # Llamar a la API
            response = client.chat.completions.create(
                model="deepseek-chat", # Modelo de DeepSeek
                messages=[
                    {"role": "system", "content": "Eres un asistente legal especializado en resumir documentos oficiales del Boletín Oficial del Estado (BOE) de España. Siempre respondes en español con resúmenes detallados y precisos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            # Obtener el resumen
            resumen = response.choices[0].message.content.strip()
            print(f"Resumen generado con DeepSeek: {resumen[:100]}...")
            
            return resumen
            
        except Exception as e:
            error_msg = f"Error al llamar a la API de DeepSeek: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return f"No se pudo generar un resumen con DeepSeek. Error: {str(e)}"
    
    @staticmethod
    def clasificar_documento(texto, categorias=None):
        """
        Clasifica un documento en categorías predefinidas
        
        Args:
            texto (str): Texto del documento a clasificar
            categorias (list): Lista de categorías posibles
            
        Returns:
            dict: Diccionario con categorías y puntuaciones
        """
        if categorias is None:
            categorias = [
                "Economía", "Sanidad", "Educación", "Empleo", 
                "Medio Ambiente", "Justicia", "Transporte", "Vivienda"
            ]
        
        # Limitar el texto para evitar errores (máximo ~500 tokens)
        texto_limitado = texto[:2000] if len(texto) > 2000 else texto
        
        if settings.USE_CLOUD_API:
            # Usar la API de HuggingFace
            payload = {
                "inputs": texto_limitado,
                "parameters": {
                    "candidate_labels": categorias
                }
            }
            
            resultado = ServicioIA._llamar_api_huggingface(
                payload, 
                "PlanTL-GOB-ES/roberta-base-bne"
            )
            
            if resultado:
                return {
                    "categorias": resultado.get("labels", []),
                    "puntuaciones": resultado.get("scores", [])
                }
            else:
                logger.error("Error al clasificar documento con la API")
                return {"categorias": [], "puntuaciones": []}
        else:
            # Usar modelo local
            try:
                from transformers import pipeline
                
                nlp = pipeline("zero-shot-classification", 
                               model="PlanTL-GOB-ES/roberta-base-bne")
                
                resultado = nlp(texto_limitado, categorias)
                
                return {
                    "categorias": resultado["labels"],
                    "puntuaciones": resultado["scores"]
                }
            except Exception as e:
                logger.error(f"Error al clasificar documento localmente: {str(e)}")
                return {"categorias": [], "puntuaciones": []}
    
    @staticmethod
    def resumir_documento_huggingface(texto, max_tokens=500):
        """
        Genera un resumen del documento usando la API de HuggingFace
        
        Args:
            texto (str): Texto del documento a resumir
            max_tokens (int): Número máximo de tokens a generar
            
        Returns:
            str: Resumen generado
        """
        try:
            print("Generando resumen con HuggingFace...")
            
            # Preparar el texto para el resumen
            texto_preparado = f"Resumen del siguiente texto: {texto}"
            
            # Llamar a la API
            resultado = ServicioIA._llamar_api_huggingface(texto_preparado, max_tokens)
            
            if resultado:
                print(f"Resumen generado con HuggingFace: {resultado[:200]}...")
                
                # Verificar que el resumen no esté vacío o sea muy corto
                if len(resultado) < 20:
                    print("El resumen generado es demasiado corto, se considera inválido")
                    return None
                
                return resultado
            else:
                print("No se pudo generar un resumen con HuggingFace")
                return None
                
        except Exception as e:
            print(f"Error al generar resumen con HuggingFace: {str(e)}")
            return None
    
    @staticmethod
    def resumir_documento(texto, modelo='default'):
        """
        Genera un resumen del documento
        
        Args:
            texto (str): Texto del documento a resumir
            modelo (str): Modelo a utilizar (default, openai, mistral, huggingface, deepseek)
            
        Returns:
            str: Resumen generado
        """
        print(f"Generando resumen con modelo: {modelo}")
        
        # Verificar si hay texto para resumir
        if not texto or len(texto.strip()) < 50:
            print("Texto demasiado corto para resumir")
            return "El texto es demasiado corto para generar un resumen."
        
        # Limitar el texto a resumir para evitar problemas
        texto_limitado = texto[:10000] if len(texto) > 10000 else texto
        
        # Intentar con el modelo especificado
        resumen = None
        
        if modelo == 'openai':
            resumen = ServicioIA.resumir_documento_openai(texto_limitado)
        elif modelo == 'mistral':
            resumen = ServicioIA._llamar_api_mistral(texto_limitado, max_tokens=500)
        elif modelo == 'huggingface':
            resumen = ServicioIA.resumir_documento_huggingface(texto_limitado)
        elif modelo == 'deepseek':
            resumen = ServicioIA._llamar_api_deepseek(texto_limitado)
        else:
            # Modelo por defecto: intentar con varios modelos en orden de preferencia
            print("Usando modelo por defecto: intentando varios modelos en secuencia")
            
            # 1. Primero intentar con Mistral
            resumen = ServicioIA._llamar_api_mistral(texto_limitado, max_tokens=500)
            
            # 2. Si Mistral falla, intentar con Hugging Face
            if not resumen or len(resumen.strip()) < 50 or "generado con mistral" in resumen.lower():
                print("Mistral falló o generó un resumen inadecuado, intentando con Hugging Face")
                resumen = ServicioIA.resumir_documento_huggingface(texto_limitado)
            
            # 3. Si Hugging Face falla, intentar con DeepSeek
            if not resumen or len(resumen.strip()) < 50:
                print("Hugging Face falló, intentando con DeepSeek")
                resumen = ServicioIA._llamar_api_deepseek(texto_limitado)
            
            # 4. Si todo lo demás falla, intentar con OpenAI (si está configurado)
            if not resumen or len(resumen.strip()) < 50:
                print("Todos los modelos anteriores fallaron, intentando con OpenAI")
                resumen = ServicioIA.resumir_documento_openai(texto_limitado)
        
        # Verificar si se generó un resumen
        if not resumen or len(resumen.strip()) < 50:
            print("No se pudo generar un resumen con ningún modelo")
            return "No se pudo generar un resumen para este documento."
        
        print(f"Resumen generado correctamente ({len(resumen)} caracteres)")
        return resumen
