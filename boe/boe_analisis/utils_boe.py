"""
Utilidades para la obtención y procesamiento de información del BOE
"""
import re
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

def obtener_sumario_boe(fecha, timeout=30):
    """
    Obtiene el sumario del BOE para una fecha específica utilizando la API de datos abiertos
    
    Args:
        fecha: Objeto datetime con la fecha a consultar
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        str: Contenido XML del sumario o None si hay error
    """
    fecha_str = fecha.strftime('%Y%m%d')
    
    # URL de la API de datos abiertos del BOE
    url = f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/xml, text/xml',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    logger.info(f"Solicitando sumario de: {url}")
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=timeout)
        
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'No especificado')}")
        
        if response.status_code == 200:
            # Verificar si la respuesta es XML válido
            if response.text.strip().startswith('<!DOCTYPE html>'):
                logger.error("La respuesta es HTML, no XML. Posible error del servidor.")
                return None
            
            # Verificar si el XML contiene un sumario válido
            if '<sumario>' in response.text:
                logger.info("Sumario XML recibido correctamente")
                
                # Intentar parsear el XML para verificar su estructura
                try:
                    # Verificar la estructura del XML según la API de datos abiertos
                    root = ET.fromstring(response.text)
                    status_code = root.find('.//status/code')
                    
                    if status_code is not None and status_code.text == '200':
                        logger.info("Estructura XML válida")
                        return response.text
                    else:
                        logger.error("El XML no tiene la estructura esperada")
                        return None
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

def obtener_texto_documento(url_xml, timeout=30):
    """
    Obtiene el texto completo de un documento a partir de su URL XML
    
    Args:
        url_xml: URL del documento XML
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        str: Texto del documento o None si hay error
    """
    if not url_xml:
        return None
    
    try:
        session = requests.Session()
        response = session.get(url_xml, timeout=timeout)
        if response.status_code == 200:
            # Parsear el XML
            root = ET.fromstring(response.text)
            
            # Extraer el texto del documento
            texto_elementos = root.findall('.//texto')
            if texto_elementos:
                textos = []
                for elem in texto_elementos:
                    if elem.text:
                        textos.append(elem.text)
                return " ".join(textos)
            
            # Si no hay elementos de texto específicos, intentar obtener todo el contenido
            contenido = root.find('.//documento/texto_consolidado')
            if contenido is not None and contenido.text:
                return contenido.text
        
        return None
    except Exception as e:
        logger.error(f"Error al obtener texto del documento: {str(e)}")
        return None

def extraer_codigo_departamento(departamento):
    """
    Extrae el código numérico del departamento a partir del nombre
    
    Args:
        departamento: Nombre del departamento
        
    Returns:
        str: Código numérico o None si no se encuentra
    """
    if not departamento:
        return None
        
    # Patrones comunes para códigos de departamento
    patrones = [
        r'(\d{1,3})\s*\-',  # Ejemplo: "101 - Ministerio de ..."
        r'Ministerio\s+(\d{1,3})',  # Ejemplo: "Ministerio 101"
        r'Departamento\s+(\d{1,3})'  # Ejemplo: "Departamento 101"
    ]
    
    for patron in patrones:
        match = re.search(patron, departamento)
        if match:
            return match.group(1)
    
    # Si no se encuentra un patrón, intentar extraer cualquier número
    numeros = re.findall(r'\d+', departamento)
    if numeros:
        return numeros[0]
    
    return None

def extraer_palabras_clave(titulo, texto, categorias_alertas=None):
    """
    Extrae palabras clave del título y texto del documento
    basándose en las categorías de alertas y análisis de texto
    
    Args:
        titulo: Título del documento
        texto: Texto del documento
        categorias_alertas: Diccionario con categorías y sus palabras clave
        
    Returns:
        list: Lista de palabras clave extraídas
    """
    palabras_clave = set()
    texto_completo = f"{titulo} {texto}".lower() if texto else titulo.lower()
    
    # Buscar coincidencias con palabras clave de categorías
    if categorias_alertas:
        for categoria, palabras in categorias_alertas.items():
            for palabra in palabras:
                if palabra and len(palabra) > 3 and palabra in texto_completo:
                    palabras_clave.add(palabra)
    
    # Extraer términos legales comunes
    terminos_legales = [
        'ley', 'real decreto', 'decreto', 'orden', 'resolución', 'acuerdo',
        'convenio', 'contrato', 'subvención', 'ayuda', 'beca', 'concurso',
        'oposición', 'licitación', 'adjudicación', 'nombramiento'
    ]
    
    for termino in terminos_legales:
        if termino in texto_completo:
            palabras_clave.add(termino)
    
    # Extraer referencias a leyes y decretos
    referencias = re.findall(r'ley\s+\d+/\d+', texto_completo)
    referencias.extend(re.findall(r'real\s+decreto\s+\d+/\d+', texto_completo))
    referencias.extend(re.findall(r'decreto\s+\d+/\d+', texto_completo))
    
    for ref in referencias:
        palabras_clave.add(ref)
    
    return list(palabras_clave)
