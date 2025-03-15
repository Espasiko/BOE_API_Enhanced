# Create your views here.
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from boe_analisis.models import *
from django.db.models import Count
import datetime
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .import_os import planning_agent, summarization_agent, workflow
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def index(request):
    """Vista principal que redirecciona al sistema de alertas"""
    from django.shortcuts import redirect
    return redirect('alertas/dashboard/')

def api_info(request):
    """Vista que devuelve información básica sobre la API"""
    return JsonResponse({
        'mensaje': 'Bienvenido a la API del BOE',
        'endpoints': {
            'api/': 'API principal con todos los recursos',
            'api/documento/': 'Documentos del BOE',
            'api/boe/': 'Documentos específicos del BOE',
            'api/departamento/': 'Departamentos',
            'api/materia/': 'Materias',
            'api/legislatura/': 'Legislaturas',
            'api/semantica/': 'Búsqueda semántica de documentos (para IAs y aplicaciones)'
        },
        'documentacion_semantica': {
            'descripcion': 'API para búsqueda semántica de documentos del BOE',
            'metodos': ['GET', 'POST'],
            'parametros': {
                'q': 'Consulta de búsqueda (texto)',
                'departamento': 'Filtrar por departamento (opcional)',
                'fecha_desde': 'Fecha inicial en formato YYYY-MM-DD (opcional)',
                'fecha_hasta': 'Fecha final en formato YYYY-MM-DD (opcional)',
                'limite': 'Número máximo de resultados (por defecto 10, máximo 100)',
                'umbral': 'Umbral de similitud (0-1, por defecto 0.3)'
            },
            'ejemplo_get': '/api/semantica/?q=protección%20de%20datos&limite=5',
            'ejemplo_post': '{"q": "protección de datos", "limite": 5}'
        }
    })

@cache_page(60 * 60 * 24)
def leyes_legislatura(request):
    """Devuelve estadísticas de leyes por legislatura"""
    legislaturas = Legislatura.objects.all()
    data = []
    for legislatura in legislaturas:
        leyes = Documento.objects.filter(legislatura=legislatura).count()
        data.append({
            'legislatura': legislatura.nombre_legislatura,
            'leyes': leyes,
            'inicio': legislatura.inicio.strftime('%Y-%m-%d'),
            'final': legislatura.final.strftime('%Y-%m-%d') if legislatura.final else None,
            'presidente': legislatura.presidente,
            'partido': legislatura.partido.nombre if legislatura.partido else None
        })
    return JsonResponse(data, safe=False)

@cache_page(60 * 60 * 24)
def leyes_meses_legislatura(request, meses=None):
    """Devuelve estadísticas de leyes por meses en una legislatura"""
    legislaturas = Legislatura.objects.all()
    data = []
    for legislatura in legislaturas:
        if meses:
            fecha_inicio = legislatura.inicio
            fecha_fin = fecha_inicio + datetime.timedelta(days=int(meses)*30)
            leyes = Documento.objects.filter(legislatura=legislatura, fecha_publicacion__range=(fecha_inicio, fecha_fin)).count()
        else:
            leyes = Documento.objects.filter(legislatura=legislatura).count()
        
        data.append({
            'legislatura': legislatura.nombre_legislatura,
            'leyes': leyes,
            'inicio': legislatura.inicio.strftime('%Y-%m-%d'),
            'final': legislatura.final.strftime('%Y-%m-%d') if legislatura.final else None,
            'presidente': legislatura.presidente,
            'partido': legislatura.partido.nombre if legislatura.partido else None
        })
    return JsonResponse(data, safe=False)

def materias_legislatura(request, materias=None):
    """Devuelve estadísticas de materias por legislatura"""
    legislaturas = Legislatura.objects.all()
    data = []
    for legislatura in legislaturas:
        if materias:
            materia = Materia.objects.get(codigo=materias)
            leyes = Documento.objects.filter(legislatura=legislatura, materias=materia).count()
        else:
            leyes = Documento.objects.filter(legislatura=legislatura).count()
        
        data.append({
            'legislatura': legislatura.nombre_legislatura,
            'leyes': leyes,
            'inicio': legislatura.inicio.strftime('%Y-%m-%d'),
            'final': legislatura.final.strftime('%Y-%m-%d') if legislatura.final else None,
            'presidente': legislatura.presidente,
            'partido': legislatura.partido.nombre if legislatura.partido else None
        })
    return JsonResponse(data, safe=False)

def top_materias(request):
    """Devuelve las 10 materias con más documentos"""
    materias = Materia.objects.annotate(num_docs=Count('documento')).order_by('-num_docs')[:10]
    data = []
    for materia in materias:
        data.append({
            'materia': materia.titulo,
            'codigo': materia.codigo,
            'documentos': materia.num_docs
        })
    return JsonResponse(data, safe=False)

def years(request, materia=None):
    """Devuelve los años con documentos"""
    if materia:
        materia = Materia.objects.get(id=materia)
        documentos = Documento.objects.filter(materias=materia)
    else:
        documentos = Documento.objects.all()
    
    years = documentos.dates('fecha_publicacion', 'year')
    data = []
    for year in years:
        if materia:
            count = documentos.filter(fecha_publicacion__year=year.year, materias=materia).count()
        else:
            count = documentos.filter(fecha_publicacion__year=year.year).count()
        data.append({
            'year': year.year,
            'count': count
        })
    return JsonResponse(data, safe=False)

def api_docs(request):
    """Vista que muestra la documentación de la API de búsqueda semántica"""
    return render(request, 'boe_analisis/api_docs.html')

@csrf_exempt
def procesar_consulta_ia(request):
    """Vista que procesa las consultas usando los agentes de Mistral"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        query = data.get('query')
        
        if not query:
            return JsonResponse({'error': 'Consulta vacía'}, status=400)

        print(f"Consulta recibida: {query}")  # Debug log

        # Crear instancias de los agentes (ya están creados en import_os.py)
        from .import_os import planning_agent, summarization_agent, workflow
        
        # Procesar la consulta con los agentes
        try:
            # Primero obtenemos una respuesta del agente de planificación
            planning_result = planning_agent.run(query)
            
            # Luego resumimos la respuesta con el agente de resumen
            summary = summarization_agent.run(f"Resumir la siguiente información sobre documentos del BOE relacionados con la consulta '{query}':\n\n{planning_result}")
            
            # Extraer información de documentos mencionados en la respuesta
            import re
            
            # Procesar los resultados para extraer la información de los documentos
            documentos_por_departamento = {}
            documentos_encontrados = False
            
            # Buscar referencias a documentos del BOE en el texto
            # Patrones para diferentes formatos de documentos BOE
            patrones = [
                # Patrón para documentos con formato BOE-A-YYYY-XXXXX
                r"BOE-[A-Z]-\d{4}-\d+",
                # Patrón para fechas de publicación en el BOE
                r"publicado en el (?:Boletín Oficial del Estado|BOE) (?:el|del) (\d{1,2} de [a-zé]+ de \d{4})",
                # Patrón para decretos, órdenes, etc.
                r"((?:Real )?Decreto|Orden|Resolución|Ley|Ley Orgánica)[\s\w,]*de\s+\d{1,2}\s+de\s+[a-zé]+\s+de\s+\d{4}",
                # Patrón para referencias a documentos por número
                r"(?:Decreto|Orden|Resolución|Ley|Ley Orgánica)\s+(?:núm\.|número)?\s*(\d+\/\d{4})"
            ]
            
            # Buscar departamentos mencionados
            dept_patterns = [
                r"(Ministerio de [^\.,:;]+)",
                r"(Fiscalía [^\.,:;]+)",
                r"(Consejo [^\.,:;]+)",
                r"(Tribunal [^\.,:;]+)",
                r"(Delegación [^\.,:;]+)",
                r"(Dirección General [^\.,:;]+)"
            ]
            
            # Extraer departamentos
            departamentos = set()
            for pattern in dept_patterns:
                matches = re.finditer(pattern, planning_result + " " + summary, re.IGNORECASE)
                for match in matches:
                    departamentos.add(match.group(1).strip())
            
            # Si no hay departamentos identificados, usar un departamento genérico
            if not departamentos:
                departamentos.add("Administración General del Estado")
            
            # Inicializar diccionario de departamentos
            for dept in departamentos:
                documentos_por_departamento[dept] = []
            
            # Extraer documentos mencionados
            doc_id_counter = 1
            for pattern in patrones:
                matches = re.finditer(pattern, planning_result + " " + summary, re.IGNORECASE)
                for match in matches:
                    documentos_encontrados = True
                    doc_text = match.group(0)
                    
                    # Extraer fecha si está disponible
                    fecha_match = re.search(r"(\d{1,2} de [a-zé]+ de \d{4})", doc_text)
                    fecha = fecha_match.group(1) if fecha_match else "2025-03-13"  # Fecha por defecto
                    
                    # Generar ID único para el documento
                    doc_id = f"BOE-{doc_id_counter}"
                    doc_id_counter += 1
                    
                    # Extraer contexto alrededor del documento (una oración)
                    contexto_pattern = r"[^\.!?]*" + re.escape(doc_text) + r"[^\.!?]*[\.!?]"
                    contexto_match = re.search(contexto_pattern, planning_result + " " + summary)
                    contexto = contexto_match.group(0).strip() if contexto_match else doc_text
                    
                    # Determinar a qué departamento asignar este documento
                    departamento_asignado = None
                    for dept in departamentos:
                        if dept.lower() in contexto.lower():
                            departamento_asignado = dept
                            break
                    
                    # Si no se puede asignar a un departamento específico, asignar al primero
                    if not departamento_asignado:
                        departamento_asignado = list(departamentos)[0]
                    
                    # Crear documento
                    documento = {
                        'id': doc_id,
                        'titulo': doc_text,
                        'descripcion': contexto,
                        'fecha': fecha,
                        'url': f'https://www.boe.es/buscar/doc.php?id={doc_text}' if 'BOE-' in doc_text else 'https://www.boe.es/buscar/index.php',
                        'exact_score': 0.9 - (0.05 * (doc_id_counter - 1)),
                        'semantic_score': 0.85 - (0.05 * (doc_id_counter - 1))
                    }
                    
                    documentos_por_departamento[departamento_asignado].append(documento)
            
            # Si no se encontraron documentos específicos pero hay información relevante en el resumen
            if not documentos_encontrados and summary and "no se encontraron" not in summary.lower():
                # Extraer información relevante del resumen
                parrafos = summary.split('\n\n')
                for i, parrafo in enumerate(parrafos):
                    if parrafo.strip():
                        # Asignar a un departamento (el primero disponible)
                        departamento_asignado = list(departamentos)[0]
                        
                        # Crear un documento basado en el párrafo
                        documento = {
                            'id': f'BOE-INFO-{i+1}',
                            'titulo': f'Información relevante del BOE - {i+1}',
                            'descripcion': parrafo.strip(),
                            'fecha': '2025-03-13',  # Fecha por defecto
                            'url': 'https://www.boe.es/buscar/index.php',
                            'exact_score': 0.8,
                            'semantic_score': 0.75
                        }
                        
                        documentos_por_departamento[departamento_asignado].append(documento)
                        documentos_encontrados = True
            
            # Convertir el diccionario a una lista para el formato esperado
            results = []
            for departamento, documentos in documentos_por_departamento.items():
                if documentos:  # Solo incluir departamentos con documentos
                    results.append({
                        'departamento': departamento,
                        'documentos': documentos
                    })
            
            # Si no hay resultados pero tenemos un resumen válido, crear un resultado genérico
            if not results and summary and "no se encontraron" not in summary.lower():
                results = [{
                    'departamento': 'Información del BOE',
                    'documentos': [{
                        'id': 'BOE-INFO',
                        'titulo': 'Información relevante sobre la consulta',
                        'descripcion': summary[:200] + "...",
                        'fecha': '2025-03-13',
                        'url': 'https://www.boe.es',
                        'exact_score': 0.7,
                        'semantic_score': 0.7
                    }]
                }]
            
            response_data = {
                'summary': summary,
                'planning_result': planning_result,  # Incluimos el resultado completo para depuración
                'results': results,
                'status': 'success'
            }
            
            print(f"Enviando respuesta: {response_data['summary'][:100]}...")  # Debug log
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"Error al procesar la consulta con los agentes: {str(e)}")
            return JsonResponse({
                'error': f"Error al procesar la consulta con los agentes: {str(e)}",
                'status': 'error'
            }, status=500)
        
    except Exception as e:
        print(f"Error en procesar_consulta_ia: {str(e)}")  # Debug log
        import traceback
        print(traceback.format_exc())  # Debug log completo
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)

@login_required
def actualizar_base_datos(request):
    """Vista para actualizar la base de datos con las últimas publicaciones del BOE"""
    from .actualizar_boe import actualizar_boe
    
    if request.method == 'POST':
        try:
            dias = int(request.POST.get('dias', 30))
            nuevos, actualizados = actualizar_boe(dias)
            messages.success(request, f'Actualización completada: {nuevos} documentos nuevos, {actualizados} documentos actualizados.')
        except Exception as e:
            messages.error(request, f'Error durante la actualización: {str(e)}')
    
    return render(request, 'boe_analisis/actualizar_base_datos.html')

def asistente_ia(request):
    """Vista que muestra el asistente IA para consultas sobre el BOE"""
    return render(request, 'boe_analisis/asistente_ia.html')

@csrf_exempt
def test_endpoint(request):
    """Endpoint de prueba para verificar la comunicación"""
    return JsonResponse({
        'status': 'success',
        'message': 'Endpoint de prueba funcionando correctamente',
        'timestamp': datetime.datetime.now().isoformat()
    })
