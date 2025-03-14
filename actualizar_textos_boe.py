import os
import sys
import django
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from tqdm import tqdm

# Configurar Django - Ajustamos la configuración para que funcione correctamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.boe.settings')
django.setup()

# Importar los modelos y utilidades
from boe.boe_analisis.models_simplified import DocumentoSimplificado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("actualizar_textos.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def obtener_texto_completo(url_xml, timeout=60):
    """
    Obtiene el texto completo de un documento a partir de su URL XML
    
    Args:
        url_xml: URL del documento XML
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        Texto completo del documento o None si hay error
    """
    try:
        # Obtener el XML del documento
        response = requests.get(url_xml, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"Error al obtener el XML del documento: {response.status_code}")
            return None
        
        # Parsear el XML
        root = ET.fromstring(response.content)
        
        # Buscar el elemento 'texto'
        texto_elem = root.find('.//texto')
        if texto_elem is None:
            logger.warning(f"No se encontró el elemento 'texto' en el XML")
            return None
        
        # Extraer todo el texto del elemento 'texto'
        texto_completo = ""
        for elem in texto_elem.iter():
            if elem.text:
                texto_completo += elem.text + " "
            if elem.tail:
                texto_completo += elem.tail + " "
        
        return texto_completo.strip()
        
    except Exception as e:
        logger.error(f"Error al obtener el texto completo: {str(e)}")
        return None

def actualizar_textos_documentos(fecha_str=None, forzar=False, limite=None):
    """
    Actualiza los textos completos de los documentos del BOE para una fecha específica
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
        forzar: Si es True, actualiza incluso los documentos que ya tienen texto
        limite: Número máximo de documentos a procesar
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.now().date()
        
        logger.info(f"Actualizando textos de documentos para la fecha: {fecha}")
        
        # Obtener documentos para la fecha especificada
        if forzar:
            # Si se fuerza, actualizar todos los documentos de la fecha
            documentos = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha)
            logger.info(f"Se actualizarán todos los documentos ({documentos.count()}) para la fecha {fecha}")
        else:
            # Si no se fuerza, actualizar solo los documentos sin texto
            documentos = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha
            ).filter(
                texto__isnull=True
            ) | DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha, 
                texto=''
            )
            logger.info(f"Se actualizarán {documentos.count()} documentos sin texto para la fecha {fecha}")
        
        # Limitar la cantidad de documentos si se especifica
        if limite and limite > 0:
            documentos = documentos[:limite]
            logger.info(f"Limitando a {limite} documentos")
        
        # Contadores
        actualizados = 0
        errores = 0
        
        # Actualizar cada documento con barra de progreso
        for doc in tqdm(documentos, desc="Actualizando textos"):
            try:
                # Verificar que el documento tiene URL XML
                if not doc.url_xml:
                    logger.warning(f"Documento {doc.identificador} sin URL XML, saltando...")
                    continue
                
                # Obtener texto completo
                texto = obtener_texto_completo(doc.url_xml)
                
                if texto:
                    # Actualizar documento
                    doc.texto = texto
                    doc.save()
                    actualizados += 1
                    logger.info(f"Texto actualizado para {doc.identificador}: {len(texto)} caracteres")
                else:
                    errores += 1
                    logger.warning(f"No se pudo obtener el texto para {doc.identificador}")
                
            except Exception as e:
                errores += 1
                logger.error(f"Error al actualizar documento {doc.identificador}: {str(e)}")
        
        # Mostrar resumen
        logger.info(f"Proceso completado. Documentos actualizados: {actualizados}, errores: {errores}")
        
        # Mostrar estadísticas finales
        total_docs = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha).count()
        docs_con_texto = DocumentoSimplificado.objects.filter(
            fecha_publicacion=fecha, 
            texto__isnull=False
        ).exclude(texto='').count()
        
        docs_sin_texto = total_docs - docs_con_texto
        
        logger.info(f"\nEstadísticas finales para {fecha}:")
        logger.info(f"Total de documentos: {total_docs}")
        if total_docs > 0:
            logger.info(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs*100:.1f}%)")
            logger.info(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs*100:.1f}%)")
        
        return actualizados, errores
    
    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        return 0, 1

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Actualiza los textos completos de los documentos del BOE')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    parser.add_argument('--forzar', action='store_true', help='Forzar actualización incluso para documentos con texto')
    parser.add_argument('--limite', type=int, help='Limitar el número de documentos a procesar')
    
    args = parser.parse_args()
    
    # Ejecutar actualización
    actualizados, errores = actualizar_textos_documentos(
        fecha_str=args.fecha,
        forzar=args.forzar,
        limite=args.limite
    )
    
    # Mostrar resumen en la consola
    print(f"\nProceso completado. Documentos actualizados: {actualizados}, errores: {errores}")
