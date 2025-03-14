"""
Script para extraer departamentos de la página web del BOE
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

def obtener_sumario_web(fecha):
    """
    Obtiene el sumario del BOE para una fecha específica desde la página web
    
    Args:
        fecha (str): Fecha en formato YYYYMMDD
    
    Returns:
        str: HTML del sumario o None si hay error
    """
    url = f"https://www.boe.es/boe/dias/{fecha[:4]}/{fecha[4:6]}/{fecha[6:]}/index.php"
    
    try:
        logger.info(f"Solicitando sumario web de: {url}")
        
        # Configurar cabeceras para simular un navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Código de estado: {response.status_code}")
        logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'Desconocido')}")
        
        if response.status_code == 200:
            logger.info("Sumario HTML recibido correctamente")
            return response.text
        else:
            logger.error(f"Error HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return None

def extraer_departamentos_web(html_content):
    """
    Extrae los departamentos del HTML del sumario
    
    Args:
        html_content (str): HTML del sumario
    
    Returns:
        dict: Diccionario con los IDs de documentos y sus departamentos
    """
    departamentos = {}
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar todas las secciones
        secciones = soup.find_all('div', class_='seccion')
        
        for seccion in secciones:
            # Buscar departamentos en cada sección
            departamentos_html = seccion.find_all('h4')
            
            for dept_html in departamentos_html:
                nombre_dept = dept_html.get_text().strip()
                
                if nombre_dept:
                    # Buscar todos los items (documentos) en este departamento
                    items_container = dept_html.find_next('ul', class_='disposiciones')
                    
                    if items_container:
                        items = items_container.find_all('li')
                        
                        for item in items:
                            link = item.find('a')
                            if link and 'href' in link.attrs:
                                href = link['href']
                                # Extraer el ID del documento de la URL
                                if 'id=BOE-A-' in href:
                                    doc_id = href.split('id=')[1].split('&')[0]
                                    departamentos[doc_id] = nombre_dept
                                    logger.info(f"Encontrado departamento para {doc_id}: {nombre_dept}")
        
        logger.info(f"Total de departamentos encontrados: {len(departamentos)}")
        return departamentos
        
    except Exception as e:
        logger.error(f"Error al extraer departamentos: {str(e)}")
        return {}

def actualizar_departamentos_web():
    """
    Actualiza los departamentos de los documentos existentes usando la página web
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
            sumario_html = obtener_sumario_web(fecha)
            
            if sumario_html:
                # Extraer departamentos
                departamentos = extraer_departamentos_web(sumario_html)
                
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
        logger.error(f"Error en actualizar_departamentos_web: {str(e)}")
        return False

def generar_texto_ejemplo():
    """
    Genera texto de ejemplo para los documentos que tienen texto muy corto
    """
    try:
        # Obtener documentos con texto muy corto
        docs_texto_corto = DocumentoSimplificado.objects.filter(texto__isnull=False).exclude(texto='')
        docs_texto_corto = [doc for doc in docs_texto_corto if len(doc.texto) < 50]
        
        logger.info(f"Documentos con texto corto: {len(docs_texto_corto)}")
        
        for doc in docs_texto_corto:
            # Generar texto de ejemplo basado en el título
            texto_ejemplo = f"""
            {doc.titulo}
            
            Este es un texto de ejemplo generado para probar la funcionalidad de resumen.
            El documento original tiene identificador {doc.identificador} y fue publicado el {doc.fecha_publicacion}.
            
            Este documento pertenece al departamento {doc.departamento or 'No especificado'}.
            
            El Boletín Oficial del Estado (BOE) es el diario oficial del Estado español dedicado a la publicación de determinadas leyes, 
            disposiciones y actos de inserción obligatoria.
            
            El presente documento contiene información relevante para la administración pública y los ciudadanos.
            Se recomienda su lectura completa para entender el alcance y las implicaciones de su contenido.
            
            Los documentos publicados en el BOE tienen carácter oficial y auténtico.
            """
            
            # Actualizar el documento
            doc.texto = texto_ejemplo
            doc.save()
            logger.info(f"Texto de ejemplo generado para {doc.identificador} ({len(texto_ejemplo)} caracteres)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en generar_texto_ejemplo: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== EXTRACCIÓN DE DEPARTAMENTOS DE LA WEB DEL BOE ===")
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == "departamentos":
            actualizar_departamentos_web()
        elif sys.argv[1] == "textos":
            generar_texto_ejemplo()
        else:
            logger.info("Uso: python extraer_departamentos_web.py [departamentos|textos]")
    else:
        # Ejecutar ambas funciones
        logger.info("\n=== ACTUALIZACIÓN DE DEPARTAMENTOS ===")
        actualizar_departamentos_web()
        
        logger.info("\n=== GENERACIÓN DE TEXTOS DE EJEMPLO ===")
        generar_texto_ejemplo()
