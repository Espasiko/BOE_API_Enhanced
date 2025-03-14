"""
Script para actualizar los departamentos de los documentos en la base de datos
utilizando el formato XML real del BOE
"""
import os
import sys
import django
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar después de configurar Django
from boe_analisis.models_simplified import DocumentoSimplificado

def obtener_sumario_xml(fecha):
    """
    Obtiene el sumario del BOE para una fecha específica en formato XML
    
    Args:
        fecha (str): Fecha en formato YYYYMMDD
    
    Returns:
        str: XML del sumario o None si hay error
    """
    url = f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{fecha}"
    
    try:
        logger.info(f"Solicitando sumario de: {url}")
        
        # Configurar cabeceras para solicitar XML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/xml, text/xml, */*; q=0.01'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'Desconocido')}")
        
        if response.status_code == 200:
            # Verificar que el contenido es XML
            if 'xml' in response.headers.get('Content-Type', '').lower():
                logger.info("Sumario XML recibido correctamente")
                return response.text
            else:
                # Intentar analizar como XML de todos modos
                try:
                    soup = BeautifulSoup(response.text, 'xml')
                    if soup.find('sumario'):
                        logger.info("Sumario XML detectado en la respuesta")
                        return response.text
                    else:
                        logger.error("La respuesta no contiene un sumario válido")
                        return None
                except Exception as e:
                    logger.error(f"Error al analizar XML: {str(e)}")
                    return None
        else:
            logger.error(f"Error HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return None

def obtener_sumario_api(fecha):
    """
    Obtiene el sumario del BOE para una fecha específica usando la API de datos abiertos
    
    Args:
        fecha (str): Fecha en formato YYYYMMDD
    
    Returns:
        str: XML del sumario o None si hay error
    """
    url = f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{fecha}"
    
    try:
        logger.info(f"Solicitando sumario de API: {url}")
        
        # Configurar cabeceras para solicitar XML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/xml'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'Desconocido')}")
        
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Error HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return None

def extraer_departamentos_xml(xml_content):
    """
    Extrae los departamentos del XML del sumario
    
    Args:
        xml_content (str): XML del sumario
    
    Returns:
        dict: Diccionario con los IDs de documentos y sus departamentos (código y nombre)
    """
    departamentos = {}
    
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        
        # Verificar si tenemos un sumario válido
        sumario = soup.find('sumario')
        if not sumario:
            logger.error("No se encontró la etiqueta 'sumario' en el XML")
            return {}
        
        # Buscar todas las secciones
        secciones = sumario.find_all('seccion')
        
        if not secciones:
            logger.error("No se encontraron secciones en el sumario")
            return {}
        
        logger.info(f"Número de secciones encontradas: {len(secciones)}")
        
        # Procesar cada sección
        for seccion in secciones:
            # Buscar departamentos en cada sección
            departamentos_xml = seccion.find_all('departamento')
            
            logger.info(f"Departamentos encontrados en sección {seccion.get('nombre', 'sin nombre')}: {len(departamentos_xml)}")
            
            for dept_xml in departamentos_xml:
                # Obtener código y nombre del departamento
                codigo_dept = dept_xml.get('codigo', '')
                nombre_dept = dept_xml.get('nombre', '')
                
                if codigo_dept and nombre_dept:
                    logger.info(f"Procesando departamento: {nombre_dept} (código: {codigo_dept})")
                    
                    # Buscar todos los items (documentos) en este departamento
                    items = dept_xml.find_all('item')
                    
                    logger.info(f"Documentos encontrados en departamento {nombre_dept}: {len(items)}")
                    
                    for item in items:
                        identificador = item.find('identificador')
                        if identificador and identificador.text:
                            doc_id = identificador.text.strip()
                            departamentos[doc_id] = {
                                'codigo': codigo_dept,
                                'nombre': nombre_dept
                            }
                            logger.info(f"Asignado departamento para {doc_id}: {nombre_dept} (código: {codigo_dept})")
        
        logger.info(f"Total de departamentos asignados: {len(departamentos)}")
        return departamentos
        
    except Exception as e:
        logger.error(f"Error al extraer departamentos del XML: {str(e)}")
        return {}

def actualizar_departamentos_xml():
    """
    Actualiza los departamentos de los documentos existentes usando el XML del BOE
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
            sumario_xml = obtener_sumario_xml(fecha)
            
            if sumario_xml:
                # Extraer departamentos
                departamentos = extraer_departamentos_xml(sumario_xml)
                
                # Actualizar documentos
                for doc_id in ids:
                    if doc_id in departamentos:
                        try:
                            doc = DocumentoSimplificado.objects.get(identificador=doc_id)
                            doc.departamento = departamentos[doc_id]['nombre']
                            doc.codigo_departamento = departamentos[doc_id]['codigo']
                            doc.save()
                            logger.info(f"Actualizado departamento para {doc_id}: {departamentos[doc_id]['nombre']} (código: {departamentos[doc_id]['codigo']})")
                        except DocumentoSimplificado.DoesNotExist:
                            logger.warning(f"Documento no encontrado: {doc_id}")
                        except Exception as e:
                            logger.error(f"Error al actualizar documento {doc_id}: {str(e)}")
                    else:
                        logger.warning(f"No se encontró departamento para: {doc_id}")
            else:
                logger.error(f"No se pudo obtener el sumario para la fecha: {fecha}")
                
                # Intentar con la API alternativa
                logger.info(f"Intentando obtener sumario con API alternativa para fecha: {fecha}")
                sumario_api = obtener_sumario_api(fecha)
                
                if sumario_api:
                    departamentos = extraer_departamentos_xml(sumario_api)
                    
                    # Actualizar documentos
                    for doc_id in ids:
                        if doc_id in departamentos:
                            try:
                                doc = DocumentoSimplificado.objects.get(identificador=doc_id)
                                doc.departamento = departamentos[doc_id]['nombre']
                                doc.codigo_departamento = departamentos[doc_id]['codigo']
                                doc.save()
                                logger.info(f"Actualizado departamento para {doc_id}: {departamentos[doc_id]['nombre']} (código: {departamentos[doc_id]['codigo']})")
                            except DocumentoSimplificado.DoesNotExist:
                                logger.warning(f"Documento no encontrado: {doc_id}")
                            except Exception as e:
                                logger.error(f"Error al actualizar documento {doc_id}: {str(e)}")
                        else:
                            logger.warning(f"No se encontró departamento para: {doc_id}")
                else:
                    logger.error(f"No se pudo obtener el sumario con API alternativa para la fecha: {fecha}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en actualizar_departamentos_xml: {str(e)}")
        return False

def obtener_texto_documento(doc_id):
    """
    Obtiene el texto completo de un documento del BOE
    
    Args:
        doc_id (str): Identificador del documento (formato BOE-X-YYYY-NNNNN)
    
    Returns:
        str: Texto del documento o None si hay error
    """
    url = f"https://www.boe.es/diario_boe/txt.php?id={doc_id}"
    
    try:
        logger.info(f"Obteniendo texto para {doc_id}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Extraer el texto del HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar el contenido principal
            contenido = soup.find('div', id='textoxslt')
            
            if contenido:
                texto = contenido.get_text(separator='\n').strip()
                logger.info(f"Texto obtenido para {doc_id} ({len(texto)} caracteres)")
                return texto
            else:
                logger.warning(f"No se encontró el contenido principal para {doc_id}")
                return None
        else:
            logger.error(f"Error HTTP {response.status_code} al obtener texto para {doc_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al obtener texto para {doc_id}: {str(e)}")
        return None

def actualizar_textos():
    """
    Actualiza los textos de los documentos existentes
    """
    try:
        # Obtener documentos sin texto
        docs_sin_texto = DocumentoSimplificado.objects.filter(texto__isnull=True) | DocumentoSimplificado.objects.filter(texto='')
        
        logger.info(f"Documentos sin texto: {docs_sin_texto.count()}")
        
        # Procesar cada documento
        for doc in docs_sin_texto:
            texto = obtener_texto_documento(doc.identificador)
            
            if texto:
                doc.texto = texto
                doc.save()
                logger.info(f"Texto actualizado para {doc.identificador} ({len(texto)} caracteres)")
            else:
                logger.warning(f"No se pudo obtener texto para {doc.identificador}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en actualizar_textos: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== ACTUALIZACIÓN DE DEPARTAMENTOS Y TEXTOS ===")
    
    # Verificar si el modelo tiene el campo código_departamento
    try:
        # Verificar si existe el campo codigo_departamento
        field_exists = hasattr(DocumentoSimplificado, 'codigo_departamento')
        
        if not field_exists:
            logger.warning("El campo 'codigo_departamento' no existe en el modelo DocumentoSimplificado")
            logger.warning("Se actualizarán solo los nombres de departamento")
    except Exception as e:
        logger.error(f"Error al verificar campos del modelo: {str(e)}")
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == "departamentos":
            logger.info("\n=== ACTUALIZACIÓN DE DEPARTAMENTOS ===")
            actualizar_departamentos_xml()
        elif sys.argv[1] == "textos":
            logger.info("\n=== ACTUALIZACIÓN DE TEXTOS ===")
            actualizar_textos()
        else:
            logger.info("Uso: python actualizar_departamentos_xml.py [departamentos|textos]")
    else:
        # Ejecutar ambas funciones
        logger.info("\n=== ACTUALIZACIÓN DE DEPARTAMENTOS ===")
        actualizar_departamentos_xml()
        
        logger.info("\n=== ACTUALIZACIÓN DE TEXTOS ===")
        actualizar_textos()
