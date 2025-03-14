import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Importar los modelos
from boe.boe_analisis.models import Documento, Departamento
from boe.boe_analisis.models_simplified import DocumentoSimplificado

def consultar_documentos(fecha_str='2025-03-10'):
    try:
        # Convertir string a fecha
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        # Contar documentos en ambos modelos
        total_docs = Documento.objects.filter(fecha_publicacion=fecha).count()
        total_docs_simpl = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha).count()
        
        print(f"\nTotal de documentos para {fecha_str}:")
        print(f"- Modelo completo: {total_docs}")
        print(f"- Modelo simplificado: {total_docs_simpl}")
        
        if total_docs_simpl == 0:
            print("No se encontraron documentos simplificados para esta fecha.")
        else:
            # Estadísticas de textos en documentos simplificados
            docs_con_texto = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha, 
                texto__isnull=False
            ).exclude(texto='').count()
            
            docs_sin_texto = total_docs_simpl - docs_con_texto
            
            print(f"\n--- Estadísticas de textos en documentos simplificados ---")
            print(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs_simpl*100:.1f}%)")
            print(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs_simpl*100:.1f}%)")
            
            # Mostrar algunos documentos simplificados
            print("\n--- Primeros 5 documentos simplificados ---")
            docs = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha)[:5]
            for doc in docs:
                print(f"ID: {doc.identificador}")
                print(f"Título: {doc.titulo[:100]}...")
                
                # Mostrar información sobre el texto
                if doc.texto:
                    texto_len = len(doc.texto)
                    texto_preview = doc.texto[:100] + "..." if texto_len > 100 else doc.texto
                    print(f"Texto: {texto_len} caracteres")
                    print(f"Vista previa: {texto_preview}")
                else:
                    print("Texto: No disponible")
                
                print(f"URL XML: {doc.url_xml}")
                print(f"URL PDF: {doc.url_pdf}")
                print(f"Departamento: {doc.departamento}")
                print("-" * 70)
        
        # Mostrar documentos por departamento
        if total_docs_simpl > 0:
            print("\n--- Documentos simplificados por departamento ---")
            departamentos = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha
            ).values('departamento').distinct()
            
            for depto_dict in departamentos:
                depto = depto_dict['departamento']
                if depto:
                    count = DocumentoSimplificado.objects.filter(
                        fecha_publicacion=fecha, 
                        departamento=depto
                    ).count()
                    print(f"{depto}: {count} documentos")
        
    except Exception as e:
        print(f"Error al consultar la base de datos: {e}")

if __name__ == "__main__":
    # Si se proporciona una fecha como argumento, usarla
    if len(sys.argv) > 1:
        consultar_documentos(sys.argv[1])
    else:
        consultar_documentos()