"""
Script para probar la generación de resúmenes
"""
import os
import sys
import django
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar después de configurar Django
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.services_ia import ServicioIA

def test_resumen_documento(doc_id=None):
    """
    Prueba la generación de resúmenes para un documento específico o el primero disponible
    """
    try:
        # Obtener un documento para resumir
        if doc_id:
            documento = DocumentoSimplificado.objects.filter(identificador=doc_id).first()
        else:
            documento = DocumentoSimplificado.objects.first()
        
        if not documento:
            logger.error("No se encontró ningún documento para resumir")
            return False
        
        logger.info(f"Documento seleccionado: {documento.identificador} - {documento.titulo[:100]}...")
        
        # Verificar si el documento tiene texto
        if not documento.texto:
            logger.error(f"El documento {documento.identificador} no tiene texto")
            return False
        
        logger.info(f"Longitud del texto: {len(documento.texto)} caracteres")
        logger.info(f"Primeros 200 caracteres: {documento.texto[:200]}...")
        
        # Probar con diferentes modelos
        modelos = ['default', 'mistral', 'huggingface', 'deepseek']
        
        for modelo in modelos:
            logger.info(f"\n=== PRUEBA CON MODELO: {modelo} ===")
            
            try:
                # Generar resumen
                resumen = ServicioIA.resumir_documento(documento.texto, modelo=modelo)
                
                if resumen:
                    logger.info(f"✅ Resumen generado correctamente con {modelo}")
                    logger.info(f"Longitud del resumen: {len(resumen)} caracteres")
                    logger.info(f"Resumen: {resumen[:500]}...")
                    
                    # Si el resumen es exitoso, no es necesario probar más modelos
                    return True
                else:
                    logger.error(f"❌ No se pudo generar un resumen con {modelo}")
            except Exception as e:
                logger.error(f"❌ Error al generar resumen con {modelo}: {str(e)}")
        
        logger.error("❌ No se pudo generar un resumen con ningún modelo")
        return False
        
    except Exception as e:
        logger.error(f"Error en test_resumen_documento: {str(e)}")
        return False

def test_busqueda_tolerante():
    """
    Prueba la búsqueda tolerante a errores
    """
    try:
        from boe_analisis.utils_busqueda import busqueda_tolerante
        
        # Términos de búsqueda con errores ortográficos
        terminos_prueba = [
            "econmia",  # economía
            "presupesto",  # presupuesto
            "adminstracion",  # administración
            "educcion",  # educación
            "goberno"  # gobierno
        ]
        
        for termino in terminos_prueba:
            logger.info(f"\n=== BÚSQUEDA TOLERANTE: '{termino}' ===")
            
            # Buscar en todos los documentos
            documentos = DocumentoSimplificado.objects.all()
            resultados = busqueda_tolerante(documentos, 'texto', termino)
            
            logger.info(f"Resultados encontrados: {len(resultados)}")
            
            # Mostrar los primeros 3 resultados
            for i, doc in enumerate(resultados[:3]):
                logger.info(f"{i+1}. {doc.identificador}: {doc.titulo[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en test_busqueda_tolerante: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== PRUEBAS DE RESUMEN Y BÚSQUEDA ===")
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == "resumen":
            doc_id = sys.argv[2] if len(sys.argv) > 2 else None
            test_resumen_documento(doc_id)
        elif sys.argv[1] == "busqueda":
            test_busqueda_tolerante()
        else:
            logger.info("Uso: python test_resumen.py [resumen|busqueda] [doc_id]")
    else:
        # Ejecutar ambas pruebas
        logger.info("\n=== PRUEBA DE RESUMEN ===")
        test_resumen_documento()
        
        logger.info("\n=== PRUEBA DE BÚSQUEDA TOLERANTE ===")
        test_busqueda_tolerante()
