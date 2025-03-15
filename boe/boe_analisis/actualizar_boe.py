"""
Script para actualizar la base de datos con las últimas publicaciones del BOE
"""

import os
import django
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from tqdm import tqdm

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar modelos después de configurar Django
from boe_analisis.models import Documento

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("actualizacion_boe.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def obtener_sumario_boe(fecha):
    """
    Obtiene el sumario del BOE para una fecha específica
    """
    fecha_str = fecha.strftime("%Y%m%d")
    url = f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{fecha_str}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener el sumario del BOE para {fecha_str}: {e}")
        return None

def procesar_sumario(xml_content):
    """
    Procesa el contenido XML del sumario del BOE
    """
    if not xml_content:
        return []
    
    try:
        root = ET.fromstring(xml_content)
        documentos = []
        
        # Procesar cada sección del BOE
        for seccion in root.findall(".//seccion"):
            seccion_nombre = seccion.get('nombre', '')
            
            # Procesar cada departamento en la sección
            for departamento in seccion.findall(".//departamento"):
                departamento_nombre = departamento.get('nombre', '')
                
                # Procesar cada item (documento) en el departamento
                for item in departamento.findall(".//item"):
                    id_boe = item.get('id', '')
                    titulo = item.find('titulo').text if item.find('titulo') is not None else ''
                    url = f"https://www.boe.es/diario_boe/xml.php?id={id_boe}"
                    
                    documentos.append({
                        'id_boe': id_boe,
                        'titulo': titulo,
                        'seccion': seccion_nombre,
                        'departamento': departamento_nombre,
                        'url': url
                    })
        
        return documentos
    except ET.ParseError as e:
        logger.error(f"Error al procesar el XML del sumario: {e}")
        return []

def guardar_documentos(documentos):
    """
    Guarda los documentos en la base de datos
    """
    nuevos = 0
    actualizados = 0
    
    for doc in tqdm(documentos, desc="Guardando documentos"):
        try:
            # Intentar obtener el contenido completo del documento
            response = requests.get(doc['url'])
            if response.status_code == 200:
                contenido_xml = response.content
                try:
                    root = ET.fromstring(contenido_xml)
                    texto_elemento = root.find(".//texto")
                    contenido = ET.tostring(texto_elemento, encoding='unicode') if texto_elemento is not None else ""
                except ET.ParseError:
                    contenido = ""
            else:
                contenido = ""
            
            # Crear o actualizar el documento en la base de datos
            obj, created = Documento.objects.update_or_create(
                id_boe=doc['id_boe'],
                defaults={
                    'titulo': doc['titulo'],
                    'seccion': doc['seccion'],
                    'departamento': doc['departamento'],
                    'url': f"https://www.boe.es/buscar/doc.php?id={doc['id_boe']}",
                    'contenido': contenido,
                    'fecha_actualizacion': datetime.now()
                }
            )
            
            if created:
                nuevos += 1
            else:
                actualizados += 1
                
        except Exception as e:
            logger.error(f"Error al guardar el documento {doc['id_boe']}: {e}")
    
    return nuevos, actualizados

def actualizar_boe(dias_atras=30):
    """
    Actualiza la base de datos con las publicaciones del BOE de los últimos días
    """
    logger.info(f"Iniciando actualización del BOE para los últimos {dias_atras} días")
    
    fecha_actual = datetime.now()
    documentos_totales = []
    
    # Procesar cada día
    for i in range(dias_atras):
        fecha = fecha_actual - timedelta(days=i)
        logger.info(f"Procesando BOE del {fecha.strftime('%d/%m/%Y')}")
        
        xml_content = obtener_sumario_boe(fecha)
        if xml_content:
            documentos = procesar_sumario(xml_content)
            documentos_totales.extend(documentos)
            logger.info(f"Se encontraron {len(documentos)} documentos para el {fecha.strftime('%d/%m/%Y')}")
        else:
            logger.warning(f"No se pudo obtener el sumario para el {fecha.strftime('%d/%m/%Y')}")
    
    # Guardar todos los documentos en la base de datos
    nuevos, actualizados = guardar_documentos(documentos_totales)
    
    logger.info(f"Actualización completada: {nuevos} documentos nuevos, {actualizados} documentos actualizados")
    return nuevos, actualizados

if __name__ == "__main__":
    nuevos, actualizados = actualizar_boe()
    print(f"Se han añadido {nuevos} documentos nuevos y actualizado {actualizados} documentos existentes.")
