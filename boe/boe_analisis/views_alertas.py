# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone

from .forms import RegistroUsuarioForm, PerfilUsuarioForm, AlertaUsuarioForm
from .models_alertas import PerfilUsuario, AlertaUsuario, NotificacionAlerta, CategoriaAlerta
from .models_simplified import DocumentoSimplificado

def registro(request):
    """
    Vista para registro de nuevos usuarios
    """
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, f"¡Bienvenido/a {username}! Tu cuenta ha sido creada correctamente.")
            return redirect('dashboard')
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'boe_analisis/registro.html', {'form': form})

@login_required
def dashboard(request):
    """
    Dashboard principal del usuario
    """
    # Obtener alertas del usuario
    alertas = AlertaUsuario.objects.filter(usuario=request.user)
    
    # Obtener notificaciones pendientes
    notificaciones_pendientes = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user,
        estado='pendiente'
    ).order_by('-fecha_notificacion')[:5]
    
    # Obtener estadísticas
    total_alertas = alertas.count()
    total_notificaciones = NotificacionAlerta.objects.filter(alerta__usuario=request.user).count()
    notificaciones_no_leidas = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user,
        estado='pendiente'
    ).count()
    
    # Obtener documentos recientes del BOE
    documentos_recientes = DocumentoSimplificado.objects.all().order_by('-fecha_publicacion')[:5]
    
    return render(request, 'boe_analisis/dashboard.html', {
        'alertas': alertas,
        'notificaciones_pendientes': notificaciones_pendientes,
        'total_alertas': total_alertas,
        'total_notificaciones': total_notificaciones,
        'notificaciones_no_leidas': notificaciones_no_leidas,
        'documentos_recientes': documentos_recientes,
    })

@login_required
def perfil(request):
    """
    Vista para editar el perfil del usuario
    """
    try:
        perfil = request.user.perfil
    except PerfilUsuario.DoesNotExist:
        perfil = PerfilUsuario.objects.create(usuario=request.user)
    
    # Calcular contadores para la plantilla
    notificaciones_count = NotificacionAlerta.objects.filter(alerta__usuario=request.user).count()
    notificaciones_pendientes_count = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user,
        estado='pendiente'
    ).count()
    
    # Añadir contadores al usuario para acceso en la plantilla
    request.user.notificaciones_count = notificaciones_count
    request.user.notificaciones_pendientes_count = notificaciones_pendientes_count
    
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect('dashboard')
    else:
        form = PerfilUsuarioForm(instance=perfil)
    
    return render(request, 'boe_analisis/perfil.html', {'form': form})

@login_required
def listar_alertas(request):
    """
    Vista para listar las alertas del usuario
    """
    alertas = AlertaUsuario.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    # Añadir conteo de notificaciones para cada alerta
    for alerta in alertas:
        alerta.total_notificaciones = alerta.notificaciones.count()
        alerta.notificaciones_pendientes = alerta.notificaciones.filter(estado='pendiente').count()
    
    return render(request, 'boe_analisis/alertas/listar.html', {'alertas': alertas})

@login_required
def crear_alerta(request):
    """
    Vista para crear una nueva alerta
    """
    if request.method == 'POST':
        form = AlertaUsuarioForm(request.POST)
        if form.is_valid():
            alerta = form.save(commit=False)
            alerta.usuario = request.user
            alerta.save()
            form.save_m2m()  # Guardar relaciones ManyToMany
            messages.success(request, f"Alerta '{alerta.nombre}' creada correctamente.")
            return redirect('listar_alertas')
    else:
        form = AlertaUsuarioForm()
    
    # Obtener categorías disponibles
    categorias = CategoriaAlerta.objects.all()
    
    return render(request, 'boe_analisis/alertas/crear.html', {
        'form': form,
        'categorias': categorias
    })

@login_required
def editar_alerta(request, alerta_id):
    """
    Vista para editar una alerta existente
    """
    alerta = get_object_or_404(AlertaUsuario, id=alerta_id, usuario=request.user)
    
    if request.method == 'POST':
        form = AlertaUsuarioForm(request.POST, instance=alerta)
        if form.is_valid():
            form.save()
            messages.success(request, f"Alerta '{alerta.nombre}' actualizada correctamente.")
            return redirect('listar_alertas')
    else:
        form = AlertaUsuarioForm(instance=alerta)
    
    # Obtener categorías disponibles
    categorias = CategoriaAlerta.objects.all()
    
    return render(request, 'boe_analisis/alertas/editar.html', {
        'form': form,
        'alerta': alerta,
        'categorias': categorias
    })

@login_required
def eliminar_alerta(request, alerta_id):
    """
    Vista para eliminar una alerta
    """
    alerta = get_object_or_404(AlertaUsuario, id=alerta_id, usuario=request.user)
    
    if request.method == 'POST':
        nombre = alerta.nombre
        alerta.delete()
        messages.success(request, f"Alerta '{nombre}' eliminada correctamente.")
        return redirect('listar_alertas')
    
    return render(request, 'boe_analisis/alertas/eliminar.html', {'alerta': alerta})

@login_required
def listar_notificaciones(request):
    """
    Vista para listar las notificaciones del usuario
    """
    estado = request.GET.get('estado', None)
    alerta_id = request.GET.get('alerta', None)
    
    # Filtrar notificaciones
    notificaciones = NotificacionAlerta.objects.filter(alerta__usuario=request.user)
    
    if estado:
        notificaciones = notificaciones.filter(estado=estado)
    
    if alerta_id:
        notificaciones = notificaciones.filter(alerta_id=alerta_id)
    
    # Ordenar por fecha (más recientes primero)
    notificaciones = notificaciones.order_by('-fecha_notificacion')
    
    # Paginación
    paginator = Paginator(notificaciones, 10)
    page = request.GET.get('page', 1)
    notificaciones_paginadas = paginator.get_page(page)
    
    # Obtener alertas para el filtro
    alertas = AlertaUsuario.objects.filter(usuario=request.user)
    
    return render(request, 'boe_analisis/alertas/notificaciones.html', {
        'notificaciones': notificaciones_paginadas,
        'alertas': alertas,
        'estado': estado,
        'alerta_id': alerta_id
    })

@login_required
def ver_notificacion(request, notificacion_id):
    """
    Vista para ver una notificación específica
    """
    notificacion = get_object_or_404(NotificacionAlerta, id=notificacion_id, alerta__usuario=request.user)
    
    # Obtener el documento completo
    from .models_simplified import DocumentoSimplificado
    documento = DocumentoSimplificado.objects.filter(identificador=notificacion.documento).first()
    
    # Marcar como leída si está pendiente
    if notificacion.estado == 'pendiente':
        notificacion.estado = 'leida'
        notificacion.save()
    
    return render(request, 'boe_analisis/alertas/ver_notificacion.html', {
        'notificacion': notificacion,
        'documento': documento
    })

@login_required
def generar_resumen_ia(request, notificacion_id):
    """
    Genera un resumen para una notificación específica mediante IA
    Solo cuando el usuario lo solicita explícitamente
    """
    from django.http import JsonResponse
    
    notificacion = get_object_or_404(NotificacionAlerta, id=notificacion_id, alerta__usuario=request.user)
    
    # Obtener el documento completo
    from .models_simplified import DocumentoSimplificado
    documento = DocumentoSimplificado.objects.filter(identificador=notificacion.documento).first()
    
    if documento:
        from .services_ia import ServicioIA
        texto_completo = f"{documento.titulo}\n\n{documento.texto}"
        notificacion.resumen = ServicioIA.resumir_documento(texto_completo)
        notificacion.save()
        
        return JsonResponse({
            'success': True,
            'resumen': notificacion.resumen
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se encontró el documento'
        }, status=404)

@login_required
def cambiar_estado_notificacion(request, notificacion_id):
    """
    Vista para cambiar el estado de una notificación (AJAX)
    """
    if request.method == 'POST' and request.is_ajax():
        notificacion = get_object_or_404(NotificacionAlerta, id=notificacion_id, alerta__usuario=request.user)
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado in ['pendiente', 'leida', 'archivada']:
            notificacion.estado = nuevo_estado
            notificacion.save()
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def estadisticas(request):
    """
    Vista para mostrar estadísticas de alertas y notificaciones
    """
    # Obtener alertas del usuario
    alertas = AlertaUsuario.objects.filter(usuario=request.user)
    
    # Estadísticas generales
    total_alertas = alertas.count()
    total_notificaciones = NotificacionAlerta.objects.filter(alerta__usuario=request.user).count()
    
    # Notificaciones por estado
    notificaciones_por_estado = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user
    ).values('estado').annotate(total=Count('id'))
    
    # Convertir a formato para gráficos
    estados_labels = []
    estados_data = []
    estados_colors = []
    
    for item in notificaciones_por_estado:
        estados_labels.append(item['estado'].capitalize())
        estados_data.append(item['total'])
        if item['estado'] == 'pendiente':
            estados_colors.append('#ffc107')  # Amarillo
        elif item['estado'] == 'leida':
            estados_colors.append('#28a745')  # Verde
        elif item['estado'] == 'archivada':
            estados_colors.append('#6c757d')  # Gris
        else:
            estados_colors.append('#007bff')  # Azul
    
    # Notificaciones por alerta
    notificaciones_por_alerta = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user
    ).values('alerta__nombre').annotate(total=Count('id')).order_by('-total')
    
    # Convertir a formato para gráficos
    alertas_labels = []
    alertas_data = []
    alertas_colors = []
    
    # Generar colores aleatorios para cada alerta
    import random
    
    for i, item in enumerate(notificaciones_por_alerta):
        alertas_labels.append(item['alerta__nombre'])
        alertas_data.append(item['total'])
        # Generar color aleatorio en formato hexadecimal
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        alertas_colors.append(color)
    
    # Notificaciones por relevancia
    relevancia_data = [
        NotificacionAlerta.objects.filter(alerta__usuario=request.user, relevancia__gte=75).count(),
        NotificacionAlerta.objects.filter(alerta__usuario=request.user, relevancia__gte=50, relevancia__lt=75).count(),
        NotificacionAlerta.objects.filter(alerta__usuario=request.user, relevancia__lt=50).count()
    ]
    
    relevancia_labels = ['Alta', 'Media', 'Baja']
    relevancia_colors = ['#28a745', '#ffc107', '#6c757d']  # Verde, Amarillo, Gris
    
    # Tendencia de notificaciones en el tiempo (últimos 30 días)
    from datetime import timedelta
    
    fecha_inicio = timezone.now() - timedelta(days=30)
    fecha_fin = timezone.now()
    
    # Crear un diccionario con todas las fechas en el rango
    import datetime
    
    fechas = {}
    fecha_actual = fecha_inicio.date()
    while fecha_actual <= fecha_fin.date():
        fechas[fecha_actual.strftime('%Y-%m-%d')] = 0
        fecha_actual += datetime.timedelta(days=1)
    
    # Obtener conteo de notificaciones por fecha
    notificaciones_por_fecha = NotificacionAlerta.objects.filter(
        alerta__usuario=request.user,
        fecha_notificacion__gte=fecha_inicio,
        fecha_notificacion__lte=fecha_fin
    ).extra({
        'fecha': "date(fecha_notificacion)"
    }).values('fecha').annotate(total=Count('id'))
    
    # Actualizar el diccionario con los conteos reales
    for item in notificaciones_por_fecha:
        # Verificar si fecha es un objeto datetime o una cadena
        if hasattr(item['fecha'], 'strftime'):
            fecha_str = item['fecha'].strftime('%Y-%m-%d')
        else:
            # Si es una cadena, usarla directamente
            fecha_str = item['fecha']
        fechas[fecha_str] = item['total']
    
    # Convertir a listas para el gráfico
    tendencia_labels = list(fechas.keys())
    tendencia_data = list(fechas.values())
    
    # Palabras clave más frecuentes
    palabras_clave = {}
    
    for alerta in alertas:
        for palabra in alerta.palabras_clave.split(','):
            palabra = palabra.strip().lower()
            if palabra:
                if palabra in palabras_clave:
                    palabras_clave[palabra] += 1
                else:
                    palabras_clave[palabra] = 1
    
    # Ordenar por frecuencia y tomar las 10 más comunes
    palabras_clave_ordenadas = sorted(palabras_clave.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Convertir a listas para el gráfico
    palabras_labels = [item[0] for item in palabras_clave_ordenadas]
    palabras_data = [item[1] for item in palabras_clave_ordenadas]
    
    # Categorías más utilizadas
    categorias_por_alerta = AlertaUsuario.objects.filter(
        usuario=request.user
    ).values('categorias__nombre').annotate(total=Count('id')).order_by('-total')
    
    # Convertir a formato para gráficos
    categorias_labels = []
    categorias_data = []
    categorias_colors = []
    
    for item in categorias_por_alerta:
        if item['categorias__nombre']:  # Ignorar None
            categorias_labels.append(item['categorias__nombre'])
            categorias_data.append(item['total'])
            # Obtener color de la categoría
            try:
                categoria = CategoriaAlerta.objects.get(nombre=item['categorias__nombre'])
                categorias_colors.append(categoria.color)
            except:
                # Color por defecto si no se encuentra la categoría
                categorias_colors.append('#007bff')
    
    context = {
        'total_alertas': total_alertas,
        'total_notificaciones': total_notificaciones,
        
        # Datos para gráfico de estados
        'estados_labels': estados_labels,
        'estados_data': estados_data,
        'estados_colors': estados_colors,
        
        # Datos para gráfico de alertas
        'alertas_labels': alertas_labels,
        'alertas_data': alertas_data,
        'alertas_colors': alertas_colors,
        
        # Datos para gráfico de relevancia
        'relevancia_labels': relevancia_labels,
        'relevancia_data': relevancia_data,
        'relevancia_colors': relevancia_colors,
        
        # Datos para gráfico de tendencia
        'tendencia_labels': tendencia_labels,
        'tendencia_data': tendencia_data,
        
        # Datos para nube de palabras clave
        'palabras_labels': palabras_labels,
        'palabras_data': palabras_data,
        
        # Datos para gráfico de categorías
        'categorias_labels': categorias_labels,
        'categorias_data': categorias_data,
        'categorias_colors': categorias_colors,
    }
    
    return render(request, 'boe_analisis/alertas/estadisticas.html', context)
