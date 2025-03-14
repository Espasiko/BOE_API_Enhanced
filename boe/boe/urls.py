from boe_analisis.models import Documento, Diario, Partido, Legislatura
from boe_analisis.urls import *
from django.urls import path, include
from django.contrib import admin
from boe_analisis import views

# Uncomment the next two lines to enable the admin:
admin.autodiscover()
#admin.site.register(Documento)
#admin.site.register(Partido)
#admin.site.register(Legislatura)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('boe_analisis.urls')),
    path('alertas/', include('boe_analisis.urls_alertas')),
    path('documentos/', include('boe_analisis.urls_documentos')),
    # Uncomment the next line to enable the admin:
    # path('admin/', include(admin.site.urls)),
    # path('search/', include('haystack.urls')),
]
