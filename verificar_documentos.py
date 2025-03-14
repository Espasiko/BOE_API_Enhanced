import os
import sys
import django
import logging
from datetime import datetime
from tqdm import tqdm

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar los modelos
from boe_analisis.models_simplified import DocumentoSimplificado

def verificar_documentos(fecha_str=None):
    """
    Verifica el estado de los documentos en la base de datos para una fecha específica
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        print(f"\nVerificando documentos para la fecha: {fecha}")
        
        # Obtener estadísticas
        total_docs = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha).count()
        
        if total_docs == 0:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        docs_con_texto = DocumentoSimplificado.objects.filter(
            fecha_publicacion=fecha, 
            texto__isnull=False
        ).exclude(texto='').count()
        
        docs_sin_texto = total_docs - docs_con_texto
        
        print(f"Total de documentos: {total_docs}")
        print(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs*100:.1f}%)")
        print(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs*100:.1f}%)")
        
        # Mostrar departamentos
        print("\nDocumentos por departamento:")
        departamentos = DocumentoSimplificado.objects.filter(
            fecha_publicacion=fecha
        ).values('departamento').distinct()
        
        for dept in departamentos:
            dept_name = dept['departamento'] or "Sin departamento"
            count = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha,
                departamento=dept['departamento']
            ).count()
            
            count_con_texto = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha,
                departamento=dept['departamento'],
                texto__isnull=False
            ).exclude(texto='').count()
            
            print(f"- {dept_name}: {count} documentos ({count_con_texto} con texto)")
        
        # Mostrar algunos ejemplos de documentos
        print("\nEjemplos de documentos:")
        documentos = DocumentoSimplificado.objects.filter(
            fecha_publicacion=fecha
        ).order_by('?')[:5]  # Seleccionar 5 documentos aleatorios
        
        for i, doc in enumerate(documentos):
            print(f"\n{i+1}. {doc.identificador} - {doc.titulo[:100]}...")
            print(f"   Departamento: {doc.departamento or 'No especificado'}")
            print(f"   URL XML: {doc.url_xml or 'No disponible'}")
            
            if doc.texto:
                # Mostrar solo los primeros 150 caracteres del texto
                texto_preview = doc.texto[:150].replace('\n', ' ').strip()
                print(f"   Texto: {texto_preview}...")
                print(f"   Longitud del texto: {len(doc.texto)} caracteres")
            else:
                print("   Texto: No disponible")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Verificar el estado de los documentos en la base de datos')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    
    args = parser.parse_args()
    
    # Ejecutar verificación
    verificar_documentos(fecha_str=args.fecha)
