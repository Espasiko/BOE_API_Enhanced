# -*- coding: utf-8 -*-
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_alertas

urlpatterns = [
    # Autenticación
    path('registro/', views_alertas.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='boe_analisis/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard y perfil
    path('dashboard/', views_alertas.dashboard, name='dashboard'),
    path('perfil/', views_alertas.perfil, name='perfil'),
    
    # Alertas
    path('alertas/', views_alertas.listar_alertas, name='listar_alertas'),
    path('alertas/crear/', views_alertas.crear_alerta, name='crear_alerta'),
    path('alertas/editar/<int:alerta_id>/', views_alertas.editar_alerta, name='editar_alerta'),
    path('alertas/eliminar/<int:alerta_id>/', views_alertas.eliminar_alerta, name='eliminar_alerta'),
    
    # Notificaciones
    path('notificaciones/', views_alertas.listar_notificaciones, name='listar_notificaciones'),
    path('notificaciones/ver/<int:notificacion_id>/', views_alertas.ver_notificacion, name='ver_notificacion'),
    path('notificaciones/cambiar-estado/<int:notificacion_id>/', views_alertas.cambiar_estado_notificacion, name='cambiar_estado_notificacion'),
    path('notificaciones/generar-resumen/<int:notificacion_id>/', views_alertas.generar_resumen_ia, name='generar_resumen_ia'),
    
    # Estadísticas
    path('estadisticas/', views_alertas.estadisticas, name='estadisticas'),
]
