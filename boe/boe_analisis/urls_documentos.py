# -*- coding: utf-8 -*-
from django.urls import path
from . import views_documentos

urlpatterns = [
    # Sumario del BOE del día actual
    path('sumario-hoy/', views_documentos.sumario_hoy, name='sumario_hoy'),
    
    # Búsqueda avanzada de documentos
    path('busqueda-avanzada/', views_documentos.busqueda_avanzada, name='busqueda_avanzada'),
    
    # Ver documento específico
    path('documento/<str:documento_id>/', views_documentos.ver_documento, name='ver_documento'),
    
    # Resumir documento con IA
    path('documento/<str:documento_id>/resumir/', views_documentos.resumir_documento_ia, name='resumir_documento_ia'),
]
