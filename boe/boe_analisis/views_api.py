"""
API para búsqueda semántica de documentos del BOE.
Permite a las IAs y otros sistemas realizar búsquedas por similitud conceptual.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
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
    - umbral: Umbral mínimo de similitud (opcional, por defecto 0.1)
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
def api_cohere_search(request):
    """
    API para realizar búsquedas usando Cohere.
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
        
        # Realizar búsqueda con Cohere
        resultados_cohere = buscar_con_cohere(query, limite, include_domains)
        
        # Combinar con resultados locales si es posible
        try:
            # Intentar búsqueda local
            from .models_simplified import DocumentoSimplificado
            from django.db.models import Q
            
            # Dividir la consulta en palabras clave
            palabras_clave = query.lower().split()
            
            # Filtrar documentos que contengan al menos una de las palabras clave
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
            
            # Formatear resultados
            resultados_locales = []
            for doc in resultados_db:
                # Generar URL real al documento del BOE
                url_real = f"https://www.boe.es/diario_boe/xml.php?id={doc.identificador}" if doc.identificador else "#"
                
                resultados_locales.append({
                    'id': str(doc.id),
                    'titulo': doc.titulo,
                    'texto': doc.texto[:500] + '...' if len(doc.texto) > 500 else doc.texto,
                    'url': url_real,
                    'score': 0.8,  # Score base para resultados locales
                    'origen': 'local',
                    'departamento': doc.departamento,
                    'fecha': doc.fecha.strftime('%Y-%m-%d') if doc.fecha else '',
                    'identificador': doc.identificador
                })
            
            # Combinar resultados
            resultados_combinados = combinar_resultados(resultados_cohere, resultados_locales, limite)
            tipo_busqueda = 'combinada'
        except Exception as e:
            logger.warning(f"Error en búsqueda local, usando solo Cohere: {str(e)}")
            resultados_combinados = resultados_cohere
            tipo_busqueda = 'cohere'
        
        return JsonResponse({
            'success': True,
            'total': len(resultados_combinados),
            'resultados': resultados_combinados,
            'consulta': query,
            'tipo_busqueda': tipo_busqueda
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda Cohere: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la búsqueda: {str(e)}'
        }, status=500)

@csrf_exempt
def api_asistente_mistral(request):
    """
    API para el asistente que usa Mistral y Cohere
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        modelo = data.get('modelo', 'mistral')  # Modelo por defecto: mistral
        
        if not query:
            return JsonResponse({'error': 'Consulta vacía'}, status=400)
        
        # Verificar si tenemos la respuesta en caché
        cache_key = f"asistente_{modelo}_{query}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return JsonResponse(cached_response)
        
        # Procesar según el modelo seleccionado
        if modelo == 'mistral-cohere':
            # Usar Cohere directamente para búsqueda
            try:
                from .import_os import cohere_client
                
                # Buscar documentos relevantes con Cohere
                resultados_busqueda = buscar_con_cohere(query, limite=3)
                
                # Construir contexto con los resultados
                contexto = ""
                if resultados_busqueda:
                    contexto = "Documentos relevantes:\n"
                    for i, doc in enumerate(resultados_busqueda):
                        contexto += f"{i+1}. {doc['titulo']} - {doc['url']}\n"
                
                # Generar respuesta con Cohere
                response = cohere_client.chat(
                    message=f"Responde a la siguiente consulta sobre documentos del BOE: {query}\n\n{contexto}",
                    model="command-r",
                    temperature=0.2
                )
                
                respuesta = {
                    'respuesta': response.text,
                    'documentos': resultados_busqueda,
                    'modelo': 'con Cohere'
                }
                
                # Guardar en caché
                cache.set(cache_key, respuesta, 3600)  # 1 hora
                
                return JsonResponse(respuesta)
                
            except Exception as e:
                import traceback
                print(f"Error al usar Cohere: {str(e)}")
                print(traceback.format_exc())
                
                # Intentar fallback a búsqueda local
                resultados_busqueda = buscar_local_fallback(query)
                return JsonResponse({
                    'respuesta': f"Lo siento, hubo un error al procesar tu consulta con Cohere. Aquí tienes algunos resultados relacionados.",
                    'documentos': resultados_busqueda,
                    'error': str(e),
                    'modelo': 'fallback'
                })
        else:
            # Usar Mistral para otros modelos
            try:
                from .import_os import mistral_client, planning_agent, summarization_agent
                
                # Buscar documentos relevantes
                resultados_busqueda = buscar_con_cohere(query, limite=3)
                
                # Construir contexto con los resultados
                contexto = ""
                if resultados_busqueda:
                    contexto = "Documentos relevantes:\n"
                    for i, doc in enumerate(resultados_busqueda):
                        contexto += f"{i+1}. {doc['titulo']} - {doc['url']}\n"
                
                # Generar respuesta con Mistral
                messages = [{"role": "user", "content": f"Responde a la siguiente consulta sobre documentos del BOE: {query}\n\n{contexto}"}]
                response = mistral_client.chat.complete(
                    model="mistral-medium",
                    messages=messages,
                    stream=False
                )
                
                respuesta = {
                    'respuesta': response.choices[0].message.content,
                    'documentos': resultados_busqueda,
                    'modelo': modelo
                }
                
                # Guardar en caché
                cache.set(cache_key, respuesta, 3600)  # 1 hora
                
                return JsonResponse(respuesta)
                
            except Exception as e:
                import traceback
                print(f"Error al usar Mistral: {str(e)}")
                print(traceback.format_exc())
                
                # Intentar fallback a búsqueda local
                resultados_busqueda = buscar_local_fallback(query)
                return JsonResponse({
                    'respuesta': f"Lo siento, hubo un error al procesar tu consulta con Mistral. Aquí tienes algunos resultados relacionados.",
                    'documentos': resultados_busqueda,
                    'error': str(e),
                    'modelo': 'fallback'
                })
    
    except Exception as e:
        import traceback
        print(f"Error general en api_asistente_mistral: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

# Funciones auxiliares para Cohere y Mistral

def buscar_con_cohere(query: str, limite: int = 5, include_domains: List[str] = None) -> List[Dict[str, Any]]:
    """
    Realiza una búsqueda usando la API de Cohere.
    
    Args:
        query: Consulta de búsqueda
        limite: Número máximo de resultados
        include_domains: Dominios específicos para incluir
        
    Returns:
        List[Dict[str, Any]]: Lista de resultados de la búsqueda
    """
    try:
        logger.info(f"Realizando búsqueda con Cohere para: {query}")
        
        # Configurar cliente de Cohere
        from cohere import Client as CohereClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        cohere_api_key = os.getenv('COHERE_API_KEY')
        cohere_client = CohereClient(api_key=cohere_api_key)
        
        # Construir la consulta con dominios específicos si se proporcionan
        search_query = query
        if include_domains and len(include_domains) > 0:
            domain_filter = " OR ".join([f"site:{domain}" for domain in include_domains])
            search_query = f"{query} ({domain_filter})"
        
        # Realizar búsqueda con Cohere
        response = cohere_client.chat(
            model='command',
            message=search_query,
            search_queries_only=True
        )
        
        # Obtener resultados de la búsqueda
        search_results = cohere_client.search(
            query=search_query,
            limit=limite
        )
        
        # Formatear resultados
        resultados_formateados = []
        for i, result in enumerate(search_results.results):
            # Calcular un score simulado basado en la posición
            score = 0.9 - (i * 0.1)
            score = max(0.3, score)  # Asegurar que el score no sea menor a 0.3
            
            resultados_formateados.append({
                'id': f"cohere_{i}",
                'titulo': result.title,
                'texto': result.snippet,
                'url': result.url,
                'score': score,
                'origen': 'cohere',
                'departamento': 'Web',
                'fecha': '',
                'identificador': ''
            })
        
        return resultados_formateados
        
    except Exception as e:
        logger.error(f"Error en búsqueda con Cohere: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Devolver resultados simulados en caso de error
        return buscar_local_fallback(query, limite)

def buscar_local_fallback(query: str, limite: int = 5) -> List[Dict[str, Any]]:
    """
    Función de fallback para búsqueda local cuando Cohere falla.
    
    Args:
        query: Consulta de búsqueda
        limite: Número máximo de resultados
        
    Returns:
        List[Dict[str, Any]]: Lista de resultados de la búsqueda
    """
    try:
        logger.info(f"Realizando búsqueda local de fallback para: {query}")
        
        # Usar la búsqueda por palabras clave en nuestra base de datos
        from .models_simplified import DocumentoSimplificado
        from django.db.models import Q
        
        # Dividir la consulta en palabras clave
        palabras_clave = query.lower().split()
        
        # Filtrar documentos que contengan al menos una de las palabras clave
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
        
        # Formatear resultados
        resultados_formateados = []
        for i, doc in enumerate(resultados_db):
            # Generar URL real al documento del BOE
            url_real = f"https://www.boe.es/diario_boe/xml.php?id={doc.identificador}" if doc.identificador else "#"
            
            # Calcular un score simulado basado en la posición
            score = 0.9 - (i * 0.1)
            score = max(0.3, score)  # Asegurar que el score no sea menor a 0.3
            
            resultados_formateados.append({
                'id': str(doc.id),
                'titulo': doc.titulo,
                'texto': doc.texto[:500] + '...' if len(doc.texto) > 500 else doc.texto,
                'url': url_real,
                'score': score,
                'origen': 'local',
                'departamento': doc.departamento,
                'fecha': doc.fecha.strftime('%Y-%m-%d') if doc.fecha else '',
                'identificador': doc.identificador
            })
        
        # Si no hay resultados, devolver un mensaje informativo
        if not resultados_formateados:
            resultados_formateados.append({
                'id': 'no_results',
                'titulo': 'No se encontraron documentos específicos',
                'texto': f'No se encontraron documentos que coincidan con la consulta: "{query}"',
                'url': 'https://www.boe.es',
                'score': 0.1,
                'origen': 'local',
                'departamento': 'Sistema',
                'fecha': '',
                'identificador': ''
            })
        
        return resultados_formateados
        
    except Exception as e:
        logger.error(f"Error en búsqueda local de fallback: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # En caso de error crítico, devolver un mensaje informativo
        return [{
            'id': 'error',
            'titulo': 'Error en la búsqueda',
            'texto': f'Se produjo un error al buscar: {str(e)}',
            'url': 'https://www.boe.es',
            'score': 0.1,
            'origen': 'error',
            'departamento': 'Sistema',
            'fecha': '',
            'identificador': ''
        }]

def combinar_resultados(resultados_cohere: List[Dict[str, Any]], resultados_locales: List[Dict[str, Any]], limite: int = 10) -> List[Dict[str, Any]]:
    """
    Combina resultados de Cohere y búsqueda local, eliminando duplicados.
    
    Args:
        resultados_cohere: Resultados de Cohere
        resultados_locales: Resultados de búsqueda local
        limite: Número máximo de resultados combinados
        
    Returns:
        List[Dict[str, Any]]: Lista combinada de resultados
    """
    # Crear un diccionario para detectar duplicados por URL
    urls_vistas = {}
    resultados_combinados = []
    
    # Añadir resultados de Cohere
    for doc in resultados_cohere:
        url = doc.get('url', '')
        if url and url not in urls_vistas:
            urls_vistas[url] = True
            resultados_combinados.append(doc)
    
    # Añadir resultados locales
    for doc in resultados_locales:
        url = doc.get('url', '')
        if url and url not in urls_vistas:
            urls_vistas[url] = True
            resultados_combinados.append(doc)
    
    # Ordenar por score
    resultados_combinados = sorted(resultados_combinados, key=lambda x: x.get('score', 0), reverse=True)
    
    # Limitar resultados
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
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mistral_api_key = os.getenv('MISTRAL_API_KEY', '')
        modelo = os.getenv('MISTRAL_MODEL', 'mistral-medium')
        
        # Si no hay API key, devolver respuesta simulada
        if not mistral_api_key:
            logger.warning("No se ha configurado MISTRAL_API_KEY. Usando respuesta simulada.")
            return "Esta es una respuesta simulada de Mistral AI. Para usar Mistral, configura MISTRAL_API_KEY en las variables de entorno."
        
        # Usar el SDK de Mistral
        from mistralai import Mistral
        
        # Inicializar el cliente de Mistral
        mistral_client = Mistral(api_key=mistral_api_key)
        
        # Realizar la llamada a la API
        response = mistral_client.chat.complete(
            model=modelo,
            messages=contexto,
            temperature=0.7,
            max_tokens=1000,
            stream=False
        )
        
        # Obtener la respuesta
        respuesta = response.choices[0].message.content
        return respuesta
        
    except Exception as e:
        logger.error(f"Error al generar respuesta con Mistral: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Lo siento, no pude generar una respuesta. Error: {str(e)}"
