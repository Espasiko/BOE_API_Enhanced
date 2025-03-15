from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_page
from tastypie.api import Api
from tastypie.models import create_api_key

from boe_analisis import views
from boe_analisis import views_api
from boe_analisis import views_comparador
from boe_analisis.api import *

# admin.site.register(boe_analisis)

v1_api = Api(api_name='v1')
v1_api.register(DocumentoResource())
v1_api.register(BOEResource())
v1_api.register(DiarioResource())
v1_api.register(DepartamentoResource())
v1_api.register(MateriaResource())
v1_api.register(RangoResource())
v1_api.register(PartidoResource())
v1_api.register(LegislaturaResource())
v1_api.register(Estado_consolidacionResource())
v1_api.register(Origen_legislativoResource())
v1_api.register(NotaResource())
v1_api.register(AlertaResource())
v1_api.register(PalabraResource())
v1_api.register(ReferenciaResource())
v1_api.register(BusquedaSemanticaResource())

urlpatterns = [
    path('', views.index, name='index'),
    path('api-info/', views.api_info, name='api_info'),
    path('api/', include(v1_api.urls)),
    path('api/semantica/', views_api.api_busqueda_semantica, name='api_semantica'),
    path('api/semantica/directa/', views_api.api_busqueda_semantica_directa, name='api_semantica_directa'),
    path('api/docs/', views.api_docs, name='api_docs'),  
    path('api/diagnostico/', views_api.api_diagnostico_qdrant, name='api_diagnostico'),
    path('api/cohere/', views_api.api_cohere_search, name='api_cohere'),
    path('api/asistente/', views_api.api_asistente_mistral, name='api_asistente'),
    path('asistente-ia/', views.asistente_ia, name='asistente_ia'),
    path('asistente/', views.asistente_ia, name='asistente'),  
    # Ruta para actualizar la base de datos
    path('actualizar-base-datos/', views.actualizar_base_datos, name='actualizar_base_datos'),
    # Rutas para el comparador de versiones
    path('comparador/', views_comparador.comparador_versiones, name='comparador_versiones'),
    path('api/comparador/buscar/', views_comparador.buscar_documento, name='buscar_documento'),
    path('api/comparador/versiones/', views_comparador.obtener_versiones, name='obtener_versiones'),
    path('api/comparador/comparar/', views_comparador.comparar_versiones, name='comparar_versiones'),
    path('v1/legislaturas/', views.leyes_legislatura),
    re_path(r'^v1/legislaturas/meses/(?P<meses>\d+)/$', views.leyes_meses_legislatura),
    path('v1/legislaturas/meses/', views.leyes_meses_legislatura),
    re_path(r'^v1/legislaturas/materia/(?P<materias>\d+)$', views.materias_legislatura),
    path('v1/legislaturas/materia/', views.top_materias),
    path('v1/years/', views.years),
    re_path(r'^v1/years/materia/(?P<materia>\d+)$', views.years),
    path('boe_analisis/procesar_consulta_ia/', views.procesar_consulta_ia, name='procesar_consulta_ia'),
    path('procesar_consulta_ia/', views.procesar_consulta_ia, name='procesar_consulta_ia_alt'),
    path('test/', views.test_endpoint, name='test_endpoint'),
]

models.signals.post_save.connect(create_api_key, sender=User)