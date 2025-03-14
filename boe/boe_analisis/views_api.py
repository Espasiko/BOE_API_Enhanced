"""
API para búsqueda semántica de documentos del BOE.
Permite a las IAs y otros sistemas realizar búsquedas por similitud conceptual.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import datetime
import logging
from typing import Dict, Any, List, Optional
from django.conf import settings
import time
import requests
from django.db.models import Q

from .utils_qdrant import QdrantBOE
from .models_simplified import DocumentoSimplificado

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@csrf_exempt
def api_diagnostico_qdrant(request):
    """
    API para verificar el estado de la conexión con Qdrant y de la colección.
    Útil para diagnosticar problemas con la búsqueda semántica.
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener estado de Qdrant
        qdrant_client = QdrantBOE()
        estado = qdrant_client.verificar_estado()
        
        # Verificar si hay documentos en la base de datos
        total_documentos = DocumentoSimplificado.objects.count()
        
        return JsonResponse({
            'success': True,
            'estado_qdrant': estado,
            'total_documentos_bd': total_documentos
        })
        
    except Exception as e:
        logger.error(f"Error en diagnóstico Qdrant: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al realizar diagnóstico: {str(e)}'
        }, status=500)

@csrf_exempt
def api_busqueda_semantica_directa(request):
    """
    API para realizar búsquedas semánticas directas en documentos del BOE.
    Esta API utiliza exclusivamente Qdrant para búsqueda vectorial sin fallback a palabras clave.
    
    Parámetros:
    - q: Consulta de búsqueda
    - limite: Número máximo de resultados (opcional, por defecto 10)
    - umbral: Umbral mínimo de similitud (opcional, por defecto 0.3)
    - departamento: Filtrar por departamento (opcional)
    - fecha_desde: Filtrar por fecha desde (opcional, formato YYYY-MM-DD)
    - fecha_hasta: Filtrar por fecha hasta (opcional, formato YYYY-MM-DD)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener datos de la petición
        data = json.loads(request.body)
        query = data.get('q', '')
        limite = int(data.get('limite', 10))
        umbral = float(data.get('umbral', 0.3))
        
        # Validar parámetros
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Consulta vacía'
            }, status=400)
        
        # Preparar filtros
        filtros = {}
        
        if 'departamento' in data and data['departamento']:
            filtros['departamento'] = data['departamento']
        
        if 'fecha_desde' in data and data['fecha_desde']:
            try:
                filtros['fecha_desde'] = datetime.datetime.strptime(data['fecha_desde'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de fecha inválido para fecha_desde (debe ser YYYY-MM-DD)'
                }, status=400)
        
        if 'fecha_hasta' in data and data['fecha_hasta']:
            try:
                filtros['fecha_hasta'] = datetime.datetime.strptime(data['fecha_hasta'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de fecha inválido para fecha_hasta (debe ser YYYY-MM-DD)'
                }, status=400)
        
        # Realizar búsqueda semántica directa (sin fallback a palabras clave)
        inicio = time.time()
        qdrant_client = QdrantBOE()
        
        # Verificar estado de Qdrant
        estado = qdrant_client.verificar_estado()
        if not estado.get('coleccion_existe') or estado.get('total_documentos', 0) == 0:
            return JsonResponse({
                'success': False,
                'error': f'Qdrant no está listo: {estado}'
            }, status=500)
        
        # Forzar búsqueda semántica sin fallback
        resultados = qdrant_client.buscar_similares(
            texto=query,
            limit=limite,
            score_threshold=umbral,
            filtros=filtros
        )
        
        tiempo_total = time.time() - inicio
        
        return JsonResponse({
            'success': True,
            'total': len(resultados),
            'resultados': resultados,
            'consulta': query,
            'tiempo_procesamiento': tiempo_total,
            'umbral': umbral
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica directa: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la búsqueda: {str(e)}'
        }, status=500)

@csrf_exempt
def api_busqueda_semantica(request):
    """
    API para realizar búsquedas semánticas en documentos del BOE.
    
    Parámetros:
    - q: Consulta de búsqueda
    - limite: Número máximo de resultados (opcional, por defecto 10)
    - umbral: Umbral mínimo de similitud (opcional, por defecto 0.3)
    - departamento: Filtrar por departamento (opcional)
    - fecha_desde: Filtrar por fecha desde (opcional, formato YYYY-MM-DD)
    - fecha_hasta: Filtrar por fecha hasta (opcional, formato YYYY-MM-DD)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener datos de la petición
        data = json.loads(request.body)
        query = data.get('q', '')
        limite = int(data.get('limite', 10))
        umbral = float(data.get('umbral', 0.1))  # Bajamos el umbral predeterminado a 0.1
        
        # Validar parámetros
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Consulta vacía'
            }, status=400)
        
        # Preparar filtros
        filtros = {}
        
        if 'departamento' in data and data['departamento']:
            filtros['departamento'] = data['departamento']
        
        if 'fecha_desde' in data and data['fecha_desde']:
            try:
                filtros['fecha_desde'] = datetime.datetime.strptime(data['fecha_desde'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de fecha inválido para fecha_desde (debe ser YYYY-MM-DD)'
                }, status=400)
        
        if 'fecha_hasta' in data and data['fecha_hasta']:
            try:
                filtros['fecha_hasta'] = datetime.datetime.strptime(data['fecha_hasta'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de fecha inválido para fecha_hasta (debe ser YYYY-MM-DD)'
                }, status=400)
        
        # Realizar búsqueda híbrida (semántica + palabras clave)
        qdrant_client = QdrantBOE()
        resultados = qdrant_client.busqueda_hibrida(query, limite=limite, score_threshold=umbral, filtros=filtros)
        
        # Añadir información sobre la consulta procesada
        resultados['consulta'] = query
        resultados['limite'] = limite
        resultados['umbral'] = umbral
        resultados['filtros'] = filtros
        
        # Añadir información de diagnóstico en modo desarrollo
        if settings.DEBUG:
            estado_qdrant = qdrant_client.verificar_estado()
            resultados['debug'] = {
                'estado_qdrant': estado_qdrant,
                'tiempo_procesamiento': time.time() - time.time()  # Placeholder para tiempo de procesamiento
            }
        
        return JsonResponse({
            'success': True,
            **resultados
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la búsqueda: {str(e)}'
        }, status=500)

@csrf_exempt
def api_tavily_search(request):
    """
    API para realizar búsquedas usando Tavily Search API.
    Permite buscar información en la web y combinarla con resultados locales.
    
    Parámetros:
    - q: Consulta de búsqueda
    - limite: Número máximo de resultados (opcional, por defecto 5)
    - include_domains: Dominios específicos para incluir (opcional)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener datos de la petición
        data = json.loads(request.body)
        query = data.get('q', '')
        limite = int(data.get('limite', 5))
        include_domains = data.get('include_domains', ["boe.es", "mjusticia.gob.es", "lamoncloa.gob.es"])
        
        # Validar parámetros
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Consulta vacía'
            }, status=400)
        
        # Realizar búsqueda en Tavily
        resultados_tavily = buscar_con_tavily(query, limite, include_domains)
        
        # Combinar con resultados locales si es posible
        try:
            # Intentar búsqueda local
            qdrant_client = QdrantBOE()
            resultados_locales = qdrant_client.buscar_por_palabras_clave(query, limite=limite)
            
            # Combinar resultados
            resultados_combinados = combinar_resultados(resultados_tavily, resultados_locales, limite)
            tipo_busqueda = 'combinada'
        except Exception as e:
            logger.warning(f"Error en búsqueda local, usando solo Tavily: {str(e)}")
            resultados_combinados = resultados_tavily
            tipo_busqueda = 'tavily'
        
        return JsonResponse({
            'success': True,
            'total': len(resultados_combinados),
            'resultados': resultados_combinados,
            'consulta': query,
            'tipo_busqueda': tipo_busqueda
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda Tavily: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la búsqueda: {str(e)}'
        }, status=500)

@csrf_exempt
def api_asistente_mistral(request):
    """
    API para el asistente IA con Mistral y Tavily.
    Permite realizar consultas que combinan búsqueda de información y generación de respuestas.
    
    Parámetros:
    - q: Consulta del usuario
    - contexto: Contexto de la conversación (opcional)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener datos de la petición
        data = json.loads(request.body)
        query = data.get('q', '')
        contexto = data.get('contexto', [])
        
        # Validar parámetros
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Consulta vacía'
            }, status=400)
        
        # Realizar búsqueda de información relevante
        resultados_busqueda = buscar_con_tavily(query, limite=3)
        
        # Preparar contexto para Mistral
        contexto_mistral = preparar_contexto_mistral(query, resultados_busqueda, contexto)
        
        # Generar respuesta con Mistral
        respuesta_mistral = generar_respuesta_mistral(contexto_mistral)
        
        return JsonResponse({
            'success': True,
            'respuesta': respuesta_mistral,
            'fuentes': resultados_busqueda,
            'consulta': query
        })
        
    except Exception as e:
        logger.error(f"Error en asistente Mistral: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la consulta: {str(e)}'
        }, status=500)

# Funciones auxiliares para Tavily y Mistral

def buscar_con_tavily(query: str, limite: int = 5, include_domains: List[str] = None) -> List[Dict[str, Any]]:
    """
    Realiza una búsqueda en la base de datos local, simulando la funcionalidad de Tavily.
    En lugar de buscar en la web, buscamos en nuestra propia base de datos.
    
    Args:
        query: Consulta de búsqueda
        limite: Número máximo de resultados
        include_domains: No se usa, se mantiene por compatibilidad
        
    Returns:
        List[Dict[str, Any]]: Lista de resultados de la búsqueda
    """
    try:
        logger.info(f"Realizando búsqueda local para: {query}")
        
        # Usar la búsqueda por palabras clave en nuestra base de datos
        from .models_simplified import DocumentoSimplificado
        
        # Dividir la consulta en palabras clave
        palabras_clave = query.lower().split()
        
        # Filtrar documentos que contengan al menos una de las palabras clave
        # en el título, texto o departamento
        resultados_db = DocumentoSimplificado.objects.all()
        
        for palabra in palabras_clave:
            if len(palabra) > 3:  # Ignorar palabras muy cortas
                resultados_db = resultados_db.filter(
                    Q(titulo__icontains=palabra) | 
                    Q(texto__icontains=palabra) | 
                    Q(departamento__icontains=palabra)
                )
        
        # Limitar resultados
        resultados_db = resultados_db[:limite]
        
        # Formatear resultados como si vinieran de Tavily
        resultados_formateados = []
        for doc in resultados_db:
            # Calcular un score simulado basado en la relevancia
            score = 0.5  # Score base
            for palabra in palabras_clave:
                if palabra in doc.titulo.lower():
                    score += 0.3
                if palabra in doc.texto.lower():
                    score += 0.1
                if palabra in doc.departamento.lower():
                    score += 0.1
            
            # Normalizar score entre 0 y 1
            score = min(score, 1.0)
            
            resultados_formateados.append({
                'id': str(doc.id),
                'titulo': doc.titulo,
                'texto': doc.texto[:500] + '...' if len(doc.texto) > 500 else doc.texto,
                'url': f"/documento/{doc.id}/" if doc.id else "#",
                'score': score,
                'origen': 'tavily_local',
                'departamento': doc.departamento,
                'fecha': doc.fecha.strftime('%Y-%m-%d') if doc.fecha else '',
                'identificador': doc.identificador
            })
        
        # Ordenar por score
        resultados_formateados = sorted(resultados_formateados, key=lambda x: x['score'], reverse=True)
        
        return resultados_formateados
        
    except Exception as e:
        logger.error(f"Error en búsqueda local (Tavily): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def combinar_resultados(resultados_tavily: List[Dict[str, Any]], resultados_locales: List[Dict[str, Any]], limite: int = 10) -> List[Dict[str, Any]]:
    """
    Combina resultados de Tavily y búsqueda local, eliminando duplicados.
    
    Args:
        resultados_tavily: Resultados de Tavily
        resultados_locales: Resultados de búsqueda local
        limite: Número máximo de resultados combinados
        
    Returns:
        List[Dict[str, Any]]: Lista combinada de resultados
    """
    # Combinar resultados eliminando duplicados
    ids_vistos = set()
    resultados_combinados = []
    
    # Primero añadimos los resultados locales
    for doc in resultados_locales:
        ids_vistos.add(doc['id'])
        resultados_combinados.append(doc)
    
    # Luego añadimos los resultados de Tavily que no estén ya incluidos
    for doc in resultados_tavily:
        if doc['id'] not in ids_vistos:
            ids_vistos.add(doc['id'])
            resultados_combinados.append(doc)
    
    # Ordenar por score descendente
    resultados_combinados = sorted(resultados_combinados, key=lambda x: x['score'], reverse=True)
    
    # Limitar al número máximo de resultados
    return resultados_combinados[:limite]

def preparar_contexto_mistral(query: str, resultados: List[Dict[str, Any]], contexto_previo: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Prepara el contexto para la consulta a Mistral.
    
    Args:
        query: Consulta del usuario
        resultados: Resultados de la búsqueda
        contexto_previo: Contexto previo de la conversación
        
    Returns:
        List[Dict[str, str]]: Contexto formateado para Mistral
    """
    # Inicializar contexto
    if contexto_previo is None:
        contexto_previo = []
    
    # Crear contexto con los resultados de la búsqueda
    contexto_sistema = "Eres un asistente especializado en información legal y documentos del BOE (Boletín Oficial del Estado). "
    contexto_sistema += "Responde de manera clara y concisa, citando las fuentes cuando sea apropiado. "
    
    # Añadir información de los resultados
    if resultados:
        contexto_sistema += "Aquí tienes información relevante para responder a la consulta:\n\n"
        for i, resultado in enumerate(resultados[:3]):  # Usar solo los 3 primeros resultados
            contexto_sistema += f"Fuente {i+1}: {resultado['titulo']}\n"
            contexto_sistema += f"Contenido: {resultado['texto'][:500]}...\n\n"
    
    # Crear mensajes para Mistral
    mensajes = [{"role": "system", "content": contexto_sistema}]
    
    # Añadir contexto previo
    for mensaje in contexto_previo:
        mensajes.append(mensaje)
    
    # Añadir consulta actual
    mensajes.append({"role": "user", "content": query})
    
    return mensajes

def generar_respuesta_mistral(contexto: List[Dict[str, str]]) -> str:
    """
    Genera una respuesta usando Mistral AI.
    
    Args:
        contexto: Contexto formateado para Mistral
        
    Returns:
        str: Respuesta generada por Mistral
    """
    try:
        # Obtener la API key de Mistral desde la configuración
        api_key = getattr(settings, 'MISTRAL_API_KEY', '')
        modelo = getattr(settings, 'MISTRAL_MODEL', 'mistral-medium')
        
        # Si no hay API key, devolver respuesta simulada
        if not api_key:
            logger.warning("No se ha configurado MISTRAL_API_KEY. Usando respuesta simulada.")
            return "Esta es una respuesta simulada de Mistral AI. Para usar Mistral, configura MISTRAL_API_KEY en las variables de entorno."
        
        # Realizar llamada a la API de Mistral
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": modelo,
            "messages": contexto,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Verificar si la respuesta es correcta
        if response.status_code == 200:
            respuesta_json = response.json()
            respuesta = respuesta_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            return respuesta
        else:
            logger.error(f"Error al llamar a la API de Mistral: {response.status_code} - {response.text}")
            return f"Error al generar respuesta con Mistral: {response.status_code}. Verifica tu API key y configuración."
        
    except Exception as e:
        logger.error(f"Error al generar respuesta con Mistral: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Lo siento, no pude generar una respuesta. Error: {str(e)}"
