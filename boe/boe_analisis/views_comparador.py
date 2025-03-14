"""
Vistas para el comparador de versiones de documentos del BOE usando Cohere
"""

import os
import json
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
import cohere
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener API key de Cohere
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")

def comparador_versiones(request):
    """
    Vista principal del comparador de versiones de documentos del BOE
    """
    return render(request, 'boe_analisis/comparador_versiones.html')

@csrf_exempt
def buscar_documento(request):
    """
    Busca un documento en el BOE por referencia o texto
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            referencia = data.get('referencia', '')
            texto = data.get('texto', '')
            
            # Verificar si tenemos la búsqueda en caché
            cache_key = f"boe_busqueda_{referencia}_{texto}"
            resultados_cache = cache.get(cache_key)
            
            if resultados_cache:
                return JsonResponse({'resultados': resultados_cache})
            
            # Si no está en caché, realizar la búsqueda
            resultados = []
            
            if referencia:
                # Buscar por referencia directa
                url = f"https://www.boe.es/buscar/act.php?id={referencia}"
                response = requests.head(url)
                
                if response.status_code == 200:
                    resultados.append({
                        'id': referencia,
                        'titulo': f"Documento {referencia}",
                        'url': url
                    })
            
            if texto and not resultados:
                # Usar Cohere para buscar documentos por texto
                co = cohere.Client(COHERE_API_KEY)
                response = co.chat(
                    message=f"Busca en el BOE documentos relacionados con: {texto}. Devuelve solo los 5 más relevantes con su referencia BOE-A-XXXX-XXXX, título y URL.",
                    model="command",
                    temperature=0.2
                )
                
                # Procesar respuesta de Cohere para extraer documentos
                texto_respuesta = response.text
                
                # Extraer referencias BOE-A-XXXX-XXXX
                import re
                referencias = re.findall(r'BOE-A-\d{4}-\d{1,5}', texto_respuesta)
                
                for ref in referencias[:5]:  # Limitar a 5 resultados
                    url = f"https://www.boe.es/buscar/act.php?id={ref}"
                    resultados.append({
                        'id': ref,
                        'titulo': f"Documento {ref}",
                        'url': url
                    })
            
            # Guardar en caché
            cache.set(cache_key, resultados, 3600)  # 1 hora
            
            return JsonResponse({'resultados': resultados})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def obtener_versiones(request):
    """
    Obtiene las versiones disponibles de un documento del BOE
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            referencia = data.get('referencia', '')
            
            if not referencia:
                return JsonResponse({'error': 'Referencia no proporcionada'}, status=400)
            
            # Verificar si tenemos las versiones en caché
            cache_key = f"boe_versiones_{referencia}"
            versiones_cache = cache.get(cache_key)
            
            if versiones_cache:
                return JsonResponse({'versiones': versiones_cache})
            
            # Si no está en caché, consultar a Cohere
            co = cohere.Client(COHERE_API_KEY)
            response = co.chat(
                message=f"Para el documento del BOE con referencia {referencia}, lista todas sus versiones disponibles con fecha de publicación. Devuelve solo las fechas en formato DD/MM/YYYY y una breve descripción de cada versión.",
                model="command",
                temperature=0.2
            )
            
            # Procesar respuesta para extraer versiones
            texto_respuesta = response.text
            
            # Extraer fechas en formato DD/MM/YYYY
            import re
            fechas = re.findall(r'\d{2}/\d{2}/\d{4}', texto_respuesta)
            
            # Crear lista de versiones
            versiones = []
            
            # Siempre incluir la versión original y la vigente
            if fechas:
                versiones.append({
                    'id': 'original',
                    'descripcion': f'Versión original ({fechas[0]})',
                    'fecha': fechas[0]
                })
                
                for i, fecha in enumerate(fechas[1:], 1):
                    versiones.append({
                        'id': f'v{i}',
                        'descripcion': f'Modificación ({fecha})',
                        'fecha': fecha
                    })
                
                # La última versión es la vigente
                versiones.append({
                    'id': 'vigente',
                    'descripcion': f'Versión vigente ({fechas[-1]})',
                    'fecha': fechas[-1]
                })
            else:
                # Si no se encontraron fechas, crear versiones genéricas
                versiones = [
                    {'id': 'original', 'descripcion': 'Versión original', 'fecha': ''},
                    {'id': 'vigente', 'descripcion': 'Versión vigente', 'fecha': ''}
                ]
            
            # Guardar en caché
            cache.set(cache_key, versiones, 86400)  # 24 horas
            
            return JsonResponse({'versiones': versiones})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def comparar_versiones(request):
    """
    Compara dos versiones de un documento del BOE utilizando Cohere
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            referencia = data.get('referencia', '')
            version_original = data.get('version_original', 'original')
            version_comparar = data.get('version_comparar', 'vigente')
            
            if not referencia:
                return JsonResponse({'error': 'Referencia no proporcionada'}, status=400)
            
            # Verificar si tenemos la comparación en caché
            cache_key = f"boe_comparacion_{referencia}_{version_original}_{version_comparar}"
            comparacion_cache = cache.get(cache_key)
            
            if comparacion_cache:
                return JsonResponse(comparacion_cache)
            
            # Si no está en caché, consultar a Cohere
            try:
                co = cohere.Client(COHERE_API_KEY)
                
                # Construir prompt para Cohere
                prompt = f"""
                Actúa como un experto en derecho español y análisis de legislación. Necesito que compares las versiones {version_original} y {version_comparar} del documento del BOE con referencia {referencia}.
                
                Analiza detalladamente las diferencias entre ambas versiones y proporciona:
                1. Un resumen ejecutivo de los cambios principales, destacando su impacto legal
                2. Una lista completa de artículos modificados, añadidos o eliminados
                3. Para cada artículo modificado, muestra el texto original y el texto nuevo, resaltando los cambios específicos
                
                Es crucial que identifiques:
                - Cambios en definiciones legales
                - Modificaciones en plazos o términos
                - Alteraciones en procedimientos administrativos
                - Cambios en sanciones o penalizaciones
                
                Formatea la respuesta en JSON con la siguiente estructura:
                {{
                    "resumen": "Texto con resumen ejecutivo de cambios",
                    "estadisticas": {{
                        "articulos_modificados": número,
                        "articulos_anadidos": número,
                        "articulos_eliminados": número,
                        "total_cambios": número
                    }},
                    "cambios": [
                        {{
                            "articulo": "Número y título del artículo",
                            "texto_original": "Texto en versión original",
                            "texto_nuevo": "Texto en versión nueva",
                            "tipo_cambio": "modificado/añadido/eliminado",
                            "importancia": "alta/media/baja",
                            "descripcion": "Breve descripción del cambio y su impacto"
                        }}
                    ]
                }}
                """
                
                # Usar el modelo command-r para mejor comprensión de textos legales
                response = co.chat(
                    message=prompt,
                    model="command-r",
                    temperature=0.2,
                    max_tokens=4000
                )
                
                # Procesar respuesta para extraer la comparación
                texto_respuesta = response.text
                
                # Intentar extraer JSON de la respuesta
                import re
                json_match = re.search(r'```json\n(.*?)\n```', texto_respuesta, re.DOTALL)
                
                if json_match:
                    comparacion_json = json.loads(json_match.group(1))
                else:
                    # Si no se encuentra JSON con formato de código, buscar cualquier JSON válido
                    json_match = re.search(r'({[\s\S]*})', texto_respuesta)
                    if json_match:
                        try:
                            comparacion_json = json.loads(json_match.group(1))
                        except:
                            # Si no se puede parsear, intentar con la respuesta completa
                            try:
                                comparacion_json = json.loads(texto_respuesta)
                            except:
                                # Si todo falla, crear una estructura básica
                                comparacion_json = {
                                    "resumen": "No se pudo generar un resumen estructurado de los cambios. Por favor, intenta nuevamente.",
                                    "estadisticas": {
                                        "articulos_modificados": 0,
                                        "articulos_anadidos": 0,
                                        "articulos_eliminados": 0,
                                        "total_cambios": 0
                                    },
                                    "cambios": [],
                                    "error_procesamiento": True
                                }
                    else:
                        # Si no se encuentra ningún JSON, crear estructura básica
                        comparacion_json = {
                            "resumen": texto_respuesta[:500] + "...",  # Incluir parte de la respuesta como resumen
                            "estadisticas": {
                                "articulos_modificados": 0,
                                "articulos_anadidos": 0,
                                "articulos_eliminados": 0,
                                "total_cambios": 0
                            },
                            "cambios": [],
                            "respuesta_completa": texto_respuesta,
                            "error_procesamiento": True
                        }
                
                # Guardar en caché
                cache.set(cache_key, comparacion_json, 86400)  # 24 horas
                
                return JsonResponse(comparacion_json)
                
            except Exception as e:
                return JsonResponse({
                    'error': f"Error al comunicarse con Cohere: {str(e)}",
                    'tipo': 'api_error'
                }, status=500)
            
        except Exception as e:
            return JsonResponse({
                'error': f"Error en el procesamiento de la solicitud: {str(e)}",
                'tipo': 'solicitud_error'
            }, status=400)
    
    return JsonResponse({'error': 'Método no permitido', 'tipo': 'metodo_error'}, status=405)
