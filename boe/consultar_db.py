import os
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar el modelo después de configurar Django
from boe_analisis.models import Documento

# Contar documentos
total_docs = Documento.objects.count()
print(f'Total de documentos: {total_docs}')

# Mostrar los primeros 5 documentos
print('\nPrimeros 5 documentos:')
for doc in Documento.objects.all()[:5]:
    print(f'- {doc.identificador}: {doc.titulo[:50]}...')
