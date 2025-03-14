# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
import datetime

from .models_simplified import DocumentoSimplificado
from .services_ia import ServicioIA
from .utils_busqueda import busqueda_multiple_campos, normalizar_texto
from .utils_qdrant import QdrantBOE  # Importamos la clase QdrantBOE

def sumario_hoy(request):
    """
    Vista para mostrar el sumario del BOE del día actual.
    Solo se descarga una vez al día.
    """
    # Obtener la fecha actual
    hoy = timezone.now().date()
    
    # Buscar documentos publicados hoy
    documentos = DocumentoSimplificado.objects.filter(fecha_publicacion=hoy)
    
    # Si no hay documentos para hoy, buscar la última fecha con documentos
    if not documentos.exists():
        ultima_fecha = DocumentoSimplificado.objects.order_by('-fecha_publicacion').first()
        if ultima_fecha:
            documentos = DocumentoSimplificado.objects.filter(
                fecha_publicacion=ultima_fecha.fecha_publicacion
            )
    
    # Agrupar documentos por departamento
    departamentos = {}
    for doc in documentos:
        if doc.departamento not in departamentos:
            departamentos[doc.departamento] = []
        departamentos[doc.departamento].append(doc)
    
    # Ordenar departamentos alfabéticamente
    departamentos_ordenados = dict(sorted(departamentos.items()))
    
    return render(request, 'boe_analisis/documentos/sumario_hoy.html', {
        'documentos': documentos,
        'departamentos': departamentos_ordenados,
        'fecha': documentos.first().fecha_publicacion if documentos.exists() else hoy,
    })

def busqueda_avanzada(request):
    """
    Vista para búsqueda avanzada de documentos del BOE.
    Permite filtrar por departamento, materias, fechas, etc.
    Incluye opción de búsqueda semántica con Qdrant.
    """
    # Obtener parámetros de búsqueda
    query = request.GET.get('q', '')
    departamento = request.GET.get('departamento', '')
    materias = request.GET.get('materias', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    busqueda_semantica = request.GET.get('semantica', '') == 'on'  # Nuevo parámetro para búsqueda semántica
    
    # Iniciar queryset con todos los documentos
    documentos = DocumentoSimplificado.objects.all()
    
    # Aplicar filtros si se proporcionan
    if query:
        if busqueda_semantica:
            # Usar búsqueda semántica con Qdrant
            try:
                # Preparar filtros para Qdrant
                filtros = {}
                if departamento:
                    filtros['departamento'] = departamento
                
                if fecha_desde:
                    try:
                        filtros['fecha_desde'] = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                if fecha_hasta:
                    try:
                        filtros['fecha_hasta'] = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                # Realizar búsqueda semántica
                qdrant_client = QdrantBOE()
                resultados_qdrant = qdrant_client.buscar_similares(query, limit=100, score_threshold=0.3, filtros=filtros)
                
                # Obtener IDs de documentos encontrados
                ids_documentos = [resultado.get('identificador') for resultado in resultados_qdrant]
                
                # Filtrar documentos por los IDs encontrados
                if ids_documentos:
                    documentos = documentos.filter(identificador__in=ids_documentos)
                    
                    # Ordenar según el score de similitud (necesitamos preservar el orden de Qdrant)
                    # Creamos un diccionario para mapear ID -> score
                    scores = {resultado.get('identificador'): resultado.get('score') for resultado in resultados_qdrant}
                    
                    # Añadimos el score como atributo a cada documento
                    for doc in documentos:
                        doc.score = scores.get(doc.identificador, 0)
                    
                    # Ordenamos la lista manualmente
                    documentos = sorted(list(documentos), key=lambda x: x.score, reverse=True)
                else:
                    documentos = DocumentoSimplificado.objects.none()  # No se encontraron resultados
            except Exception as e:
                print(f"Error en búsqueda semántica: {str(e)}")
                # Si falla la búsqueda semántica, volvemos a la búsqueda normal
                documentos = busqueda_multiple_campos(
                    documentos, 
                    ['titulo', 'texto', 'identificador', 'departamento', 'materias'], 
                    query
                )
        else:
            # Usar búsqueda tolerante en múltiples campos (método tradicional)
            documentos = busqueda_multiple_campos(
                documentos, 
                ['titulo', 'texto', 'identificador', 'departamento', 'materias'], 
                query
            )
    
    # Si no estamos usando búsqueda semántica, aplicamos los filtros adicionales
    if not busqueda_semantica or not query:
        if departamento:
            documentos = documentos.filter(departamento__icontains=departamento)
        
        if materias:
            documentos = documentos.filter(materias__icontains=materias)
        
        if fecha_desde:
            try:
                fecha_desde = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                documentos = documentos.filter(fecha_publicacion__gte=fecha_desde)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                documentos = documentos.filter(fecha_publicacion__lte=fecha_hasta)
            except ValueError:
                pass
        
        # Ordenar por fecha de publicación (más recientes primero)
        if isinstance(documentos, list):
            # Ya está ordenado por score
            pass
        else:
            documentos = documentos.order_by('-fecha_publicacion')
    
    # Obtener lista única de departamentos y materias para los filtros
    todos_departamentos = list(DocumentoSimplificado.objects.exclude(departamento__isnull=True).exclude(departamento='').values_list('departamento', flat=True).distinct())
    
    # Ordenar departamentos alfabéticamente
    todos_departamentos.sort()
    
    # Para las materias, necesitamos procesarlas ya que están almacenadas como texto separado por comas
    todas_materias = []
    for doc_materias in DocumentoSimplificado.objects.exclude(materias__isnull=True).exclude(materias='').values_list('materias', flat=True).distinct():
        if doc_materias:
            for materia in doc_materias.split(','):
                materia = materia.strip()
                if materia and materia not in todas_materias:
                    todas_materias.append(materia)
    
    # Ordenar materias alfabéticamente
    todas_materias.sort()
    
    # Imprimir información de depuración
    print(f"Total de documentos en la base de datos: {DocumentoSimplificado.objects.count()}")
    print(f"Departamentos encontrados: {todos_departamentos}")
    print(f"Materias encontradas: {todas_materias}")
    if isinstance(documentos, list):
        print(f"Documentos filtrados: {len(documentos)}")
    else:
        print(f"Documentos filtrados: {documentos.count()}")
    print(f"Términos de búsqueda: '{query}' (normalizado: '{normalizar_texto(query)}')")
    print(f"Búsqueda semántica: {'Activada' if busqueda_semantica else 'Desactivada'}")
    
    # Paginación
    if isinstance(documentos, list):
        # Paginación manual para listas (resultados de búsqueda semántica)
        paginator = Paginator(documentos, 20)  # 20 documentos por página
    else:
        # Paginación normal para querysets
        paginator = Paginator(documentos, 20)  # 20 documentos por página
    
    page = request.GET.get('page', 1)
    documentos_paginados = paginator.get_page(page)
    
    return render(request, 'boe_analisis/documentos/busqueda_avanzada.html', {
        'documentos': documentos_paginados,
        'query': query,
        'departamento': departamento,
        'materias': materias,
        'fecha_desde': fecha_desde if isinstance(fecha_desde, str) else fecha_desde.strftime('%Y-%m-%d') if fecha_desde else '',
        'fecha_hasta': fecha_hasta if isinstance(fecha_hasta, str) else fecha_hasta.strftime('%Y-%m-%d') if fecha_hasta else '',
        'todos_departamentos': todos_departamentos,
        'todas_materias': todas_materias,
        'busqueda_semantica': busqueda_semantica,  # Pasamos el estado de la búsqueda semántica a la plantilla
    })

def ver_documento(request, documento_id):
    """
    Vista para ver un documento específico con opciones para resumir con IA.
    """
    documento = get_object_or_404(DocumentoSimplificado, identificador=documento_id)
    
    return render(request, 'boe_analisis/documentos/ver_documento.html', {
        'documento': documento,
    })

def resumir_documento_ia(request, documento_id):
    """
    Vista para generar un resumen de un documento mediante IA.
    Permite seleccionar el modelo de IA a utilizar.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    documento = get_object_or_404(DocumentoSimplificado, identificador=documento_id)
    modelo_ia = request.POST.get('modelo_ia', 'default')
    
    # Obtener el texto completo del documento
    texto_completo = f"{documento.titulo}\n\n{documento.texto}"
    
    # Log para diagnóstico
    print(f"Generando resumen para documento {documento_id} con modelo {modelo_ia}")
    print(f"Longitud del texto: {len(texto_completo)} caracteres")
    
    try:
        # Intentar generar el resumen utilizando el servicio de IA
        resumen = ServicioIA.resumir_documento(texto_completo, modelo=modelo_ia)
        
        # Verificar si el resumen es válido
        if not resumen or len(resumen.strip()) < 20:
            print(f"Resumen demasiado corto o vacío: '{resumen}'")
            return JsonResponse({
                'success': False, 
                'error': 'El resumen generado es demasiado corto o no contiene información útil. Por favor, intenta con otro modelo.'
            })
            
        if "error" in resumen.lower() or "no se pudo" in resumen.lower():
            print(f"El servicio de IA devolvió un mensaje de error: '{resumen}'")
            return JsonResponse({
                'success': False, 
                'error': resumen
            })
            
        print(f"Resumen generado exitosamente con longitud: {len(resumen)} caracteres")
        
        return JsonResponse({
            'success': True,
            'resumen': resumen,
            'modelo': modelo_ia
        })
    except Exception as e:
        # Capturar cualquier excepción durante el proceso
        error_mensaje = str(e)
        print(f"Error al generar resumen: {error_mensaje}")
        
        return JsonResponse({
            'success': False,
            'error': f"Error al generar el resumen: {error_mensaje}"
        })
