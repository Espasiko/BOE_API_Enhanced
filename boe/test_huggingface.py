"""
Script de prueba para verificar la conexión con Hugging Face
"""
import os
import sys
import logging
from dotenv import load_dotenv
import requests
import json
import time

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")

if not API_KEY:
    logger.error("No se encontró la clave API de Hugging Face en las variables de entorno")
    sys.exit(1)

logger.info(f"Clave API encontrada: {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) > 10 else ''}")

def test_api_connection():
    """
    Prueba la conexión a la API de Hugging Face
    """
    logger.info("Probando conexión a la API de Hugging Face...")
    
    # URL de la API para el modelo RoBERTa
    api_url = "https://api-inference.huggingface.co/models/PlanTL-GOB-ES/roberta-base-bne"
    
    # Headers con la clave API
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Payload para una tarea de fill-mask
    payload = {
        "inputs": "El lenguaje <mask> es importante para la comunicación."
    }
    
    try:
        # Realizar la petición
        logger.info(f"Enviando petición a {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        # Verificar el código de estado
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Headers de respuesta: {response.headers}")
        
        if response.status_code == 200:
            # La petición fue exitosa
            result = response.json()
            logger.info("Respuesta exitosa:")
            logger.info(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        elif response.status_code == 503:
            # El modelo está cargando
            logger.warning("El modelo está cargando. Espera unos segundos e intenta de nuevo.")
            logger.info(f"Respuesta: {response.text}")
            time.sleep(10)
            logger.info("Intentando de nuevo después de esperar...")
            return test_api_connection()  # Llamada recursiva con precaución
        else:
            # Otro error
            logger.error(f"Error en la petición: {response.status_code}")
            logger.error(f"Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al conectar con la API: {str(e)}")
        return False

def test_transformers_local():
    """
    Prueba el uso local de transformers (requiere descargar el modelo)
    """
    logger.info("Probando uso local de transformers...")
    
    try:
        # Intentar importar transformers
        from transformers import pipeline, AutoTokenizer, AutoModelForMaskedLM
        
        logger.info("Cargando tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained("PlanTL-GOB-ES/roberta-base-bne")
        
        logger.info("Cargando modelo...")
        model = AutoModelForMaskedLM.from_pretrained("PlanTL-GOB-ES/roberta-base-bne")
        
        logger.info("Creando pipeline...")
        pipe = pipeline("fill-mask", model=model, tokenizer=tokenizer)
        
        logger.info("Ejecutando inferencia...")
        result = pipe("El lenguaje <mask> es importante para la comunicación.")
        
        logger.info("Resultado:")
        for item in result:
            logger.info(f"- {item['token_str']} (score: {item['score']:.4f})")
        
        return True
    except Exception as e:
        logger.error(f"Error al usar transformers localmente: {str(e)}")
        return False

def test_summarization_api():
    """
    Prueba la API para resumir texto (usando un modelo diferente)
    """
    logger.info("Probando API para resumir texto...")
    
    # URL de la API para un modelo de resumen en español
    api_url = "https://api-inference.huggingface.co/models/mrm8488/t5-base-finetuned-spanish-summarization"
    
    # Headers con la clave API
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Texto de ejemplo para resumir
    texto = """
    El Boletín Oficial del Estado (BOE) es el diario oficial del Estado español dedicado a la publicación de determinadas leyes, 
    disposiciones y actos de inserción obligatoria. Su edición, impresión, publicación y difusión está encomendada a la Agencia 
    Estatal Boletín Oficial del Estado, organismo público dependiente del Ministerio de la Presidencia. El BOE publica las leyes 
    de las Cortes Generales, las disposiciones emanadas del Gobierno de España y las disposiciones generales de las comunidades 
    autónomas, así como los actos, disposiciones, resoluciones y anuncios que el ordenamiento jurídico considera de publicación 
    obligatoria en el diario oficial.
    """
    
    # Payload para una tarea de resumen
    payload = {
        "inputs": texto,
        "parameters": {
            "max_length": 100,
            "min_length": 30
        }
    }
    
    try:
        # Realizar la petición
        logger.info(f"Enviando petición a {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        # Verificar el código de estado
        logger.info(f"Código de estado: {response.status_code}")
        
        if response.status_code == 200:
            # La petición fue exitosa
            result = response.json()
            logger.info("Respuesta exitosa:")
            logger.info(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        elif response.status_code == 503:
            # El modelo está cargando
            logger.warning("El modelo está cargando. Espera unos segundos e intenta de nuevo.")
            logger.info(f"Respuesta: {response.text}")
            return False
        else:
            # Otro error
            logger.error(f"Error en la petición: {response.status_code}")
            logger.error(f"Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al conectar con la API: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== PRUEBA DE CONEXIÓN CON HUGGING FACE ===")
    
    # Probar conexión a la API con modelo de máscara
    logger.info("\n=== PRUEBA 1: MODELO ROBERTA (FILL-MASK) ===")
    roberta_success = test_api_connection()
    
    # Probar API de resumen
    logger.info("\n=== PRUEBA 2: MODELO DE RESUMEN ===")
    summary_success = test_summarization_api()
    
    # Probar uso local si las APIs fallaron
    if not roberta_success and not summary_success:
        logger.info("\n=== PRUEBA 3: USO LOCAL DE TRANSFORMERS ===")
        local_success = test_transformers_local()
        
        if local_success:
            logger.info("✅ El uso local de transformers funciona correctamente")
        else:
            logger.error("❌ Falló tanto la API como el uso local")
    else:
        if roberta_success:
            logger.info("✅ La conexión a la API de RoBERTa funciona correctamente")
        if summary_success:
            logger.info("✅ La conexión a la API de resumen funciona correctamente")
