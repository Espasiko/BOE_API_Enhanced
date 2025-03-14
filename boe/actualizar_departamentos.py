"""
Script para actualizar los departamentos de los documentos existentes
"""
import os
import sys
import django
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar después de configurar Django
from boe_analisis.models_simplified import DocumentoSimplificado

def obtener_sumario_boe(fecha):
    """
    Obtiene el sumario del BOE para una fecha específica
    
    Args:
        fecha (str): Fecha en formato YYYYMMDD
    
    Returns:
        str: XML del sumario o None si hay error
    """
    url = f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{fecha}"
    
    try:
        logger.info(f"Solicitando sumario de: {url}")
        
        # Configurar cabeceras para evitar el error 400
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/xml'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'Desconocido')}")
        
        if response.status_code == 200:
            # Verificar que la respuesta es XML
            if 'xml' in response.headers.get('Content-Type', '').lower():
                try:
                    # Intentar parsear el XML para verificar que es válido
                    ET.fromstring(response.content)
                    logger.info("Sumario XML recibido correctamente")
                    return response.content
                except ET.ParseError as e:
                    logger.error(f"Error al parsear el XML: {str(e)}")
                    return None
            else:
                logger.error("La respuesta no contiene un sumario válido")
                return None
        else:
            logger.error(f"Error HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return None

def extraer_departamentos(sumario_xml):
    """
    Extrae los departamentos del sumario XML
    
    Args:
        sumario_xml (str): XML del sumario
    
    Returns:
        dict: Diccionario con los IDs de documentos y sus departamentos
    """
    departamentos = {}
    
    try:
        root = ET.fromstring(sumario_xml)
        
        # Buscar todas las secciones
        secciones = root.findall('.//seccion')
        
        for seccion in secciones:
            # Buscar departamentos en cada sección
            departamentos_xml = seccion.findall('./departamento')
            
            for dept_xml in departamentos_xml:
                nombre_dept = dept_xml.get('nombre')
                
                if not nombre_dept:
                    # Intentar buscar el nombre en un subelemento
                    nombre_elem = dept_xml.find('./nombre')
                    if nombre_elem is not None and nombre_elem.text:
                        nombre_dept = nombre_elem.text
                
                if nombre_dept:
                    # Buscar todos los items (documentos) en este departamento
                    items = dept_xml.findall('.//item')
                    
                    for item in items:
                        id_elem = item.find('./id')
                        if id_elem is not None and id_elem.text:
                            doc_id = id_elem.text
                            departamentos[doc_id] = nombre_dept
                            logger.info(f"Encontrado departamento para {doc_id}: {nombre_dept}")
        
        logger.info(f"Total de departamentos encontrados: {len(departamentos)}")
        return departamentos
        
    except Exception as e:
        logger.error(f"Error al extraer departamentos: {str(e)}")
        return {}

def actualizar_departamentos():
    """
    Actualiza los departamentos de los documentos existentes
    """
    try:
        # Obtener todos los documentos sin departamento
        docs_sin_dept = DocumentoSimplificado.objects.filter(departamento__isnull=True) | DocumentoSimplificado.objects.filter(departamento='')
        
        logger.info(f"Documentos sin departamento: {docs_sin_dept.count()}")
        
        # Agrupar documentos por fecha
        fechas = {}
        for doc in docs_sin_dept:
            fecha_str = doc.fecha_publicacion.strftime('%Y%m%d')
            if fecha_str not in fechas:
                fechas[fecha_str] = []
            fechas[fecha_str].append(doc.identificador)
        
        logger.info(f"Fechas a procesar: {len(fechas)}")
        
        # Procesar cada fecha
        for fecha, ids in fechas.items():
            logger.info(f"Procesando fecha: {fecha} ({len(ids)} documentos)")
            
            # Obtener el sumario para esta fecha
            sumario_xml = obtener_sumario_boe(fecha)
            
            if sumario_xml:
                # Extraer departamentos
                departamentos = extraer_departamentos(sumario_xml)
                
                # Actualizar documentos
                for doc_id in ids:
                    if doc_id in departamentos:
                        try:
                            doc = DocumentoSimplificado.objects.get(identificador=doc_id)
                            doc.departamento = departamentos[doc_id]
                            doc.save()
                            logger.info(f"Actualizado departamento para {doc_id}: {departamentos[doc_id]}")
                        except DocumentoSimplificado.DoesNotExist:
                            logger.warning(f"Documento no encontrado: {doc_id}")
                    else:
                        logger.warning(f"No se encontró departamento para: {doc_id}")
            else:
                logger.error(f"No se pudo obtener el sumario para la fecha: {fecha}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en actualizar_departamentos: {str(e)}")
        return False

def obtener_texto_documentos():
    """
    Obtiene el texto completo de los documentos que no lo tienen
    """
    try:
        # Obtener documentos sin texto
        docs_sin_texto = DocumentoSimplificado.objects.filter(texto__isnull=True) | DocumentoSimplificado.objects.filter(texto='')
        
        logger.info(f"Documentos sin texto: {docs_sin_texto.count()}")
        
        for doc in docs_sin_texto:
            if doc.url_xml:
                try:
                    logger.info(f"Obteniendo texto para {doc.identificador}")
                    
                    # Realizar la petición HTTP
                    response = requests.get(doc.url_xml, timeout=30)
                    
                    if response.status_code == 200:
                        # Parsear el XML
                        root = ET.fromstring(response.content)
                        
                        # Extraer el texto del documento
                        texto_elementos = root.findall('.//texto')
                        
                        if texto_elementos:
                            texto_completo = ""
                            for elem in texto_elementos:
                                if elem.text:
                                    texto_completo += elem.text + "\n\n"
                            
                            if texto_completo:
                                doc.texto = texto_completo
                                doc.save()
                                logger.info(f"Texto actualizado para {doc.identificador} ({len(texto_completo)} caracteres)")
                            else:
                                logger.warning(f"No se encontró texto en el XML para {doc.identificador}")
                        else:
                            # Intentar con otra estructura
                            contenido = root.find('.//cuerpo')
                            if contenido is not None:
                                texto_completo = ET.tostring(contenido, encoding='unicode', method='text')
                                if texto_completo:
                                    doc.texto = texto_completo
                                    doc.save()
                                    logger.info(f"Texto actualizado para {doc.identificador} ({len(texto_completo)} caracteres)")
                                else:
                                    logger.warning(f"No se encontró texto en el cuerpo para {doc.identificador}")
                            else:
                                logger.warning(f"No se encontró contenido para {doc.identificador}")
                    else:
                        logger.error(f"Error al obtener XML para {doc.identificador}: HTTP {response.status_code}")
                
                except Exception as e:
                    logger.error(f"Error al procesar documento {doc.identificador}: {str(e)}")
            else:
                logger.warning(f"El documento {doc.identificador} no tiene URL XML")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en obtener_texto_documentos: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== ACTUALIZACIÓN DE DEPARTAMENTOS Y TEXTOS ===")
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == "departamentos":
            actualizar_departamentos()
        elif sys.argv[1] == "textos":
            obtener_texto_documentos()
        else:
            logger.info("Uso: python actualizar_departamentos.py [departamentos|textos]")
    else:
        # Ejecutar ambas funciones
        logger.info("\n=== ACTUALIZACIÓN DE DEPARTAMENTOS ===")
        actualizar_departamentos()
        
        logger.info("\n=== OBTENCIÓN DE TEXTOS ===")
        obtener_texto_documentos()
