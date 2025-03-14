"""
Script para actualizar los documentos en Qdrant y asegurarse de que todos tengan contenido completo.
Este script verifica que los documentos en la base de datos tengan texto completo antes de indexarlos en Qdrant.
También identifica documentos con texto potencialmente incompleto para su actualización.
"""

import os
import sys
import django
import logging
import requests
from datetime import datetime, timedelta
import dotenv
from tqdm import tqdm
import re
import time

# Cargar variables de entorno
dotenv.load_dotenv()

# Configurar Django
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boe'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar los modelos y utilidades
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.utils_qdrant import QdrantBOE, get_qdrant_client

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Longitud mínima esperada para un texto completo (en caracteres)
LONGITUD_MINIMA_TEXTO = 500

def verificar_documentos_sin_texto():
    """
    Verifica cuántos documentos no tienen texto completo en la base de datos.
    
    Returns:
        tuple: (total_documentos, documentos_sin_texto, documentos_texto_incompleto)
    """
    total_documentos = DocumentoSimplificado.objects.count()
    documentos_sin_texto = DocumentoSimplificado.objects.filter(texto__isnull=True).count()
    documentos_texto_vacio = DocumentoSimplificado.objects.filter(texto='').count()
    
    # Para documentos con texto potencialmente incompleto, debemos hacerlo manualmente
    # ya que Django no soporta __length para TextField
    documentos_texto_incompleto = 0
    
    # Tomar una muestra de documentos con texto para verificar longitud
    documentos_con_texto = DocumentoSimplificado.objects.exclude(texto__isnull=True).exclude(texto='')
    
    # Limitar a 1000 documentos para no sobrecargar la memoria
    muestra = documentos_con_texto.order_by('-fecha_publicacion')[:1000]
    
    for doc in muestra:
        if len(doc.texto) < LONGITUD_MINIMA_TEXTO:
            documentos_texto_incompleto += 1
    
    # Estimar el total basado en la proporción de la muestra
    if muestra.count() > 0:
        proporcion = documentos_texto_incompleto / muestra.count()
        documentos_texto_incompleto = int(proporcion * documentos_con_texto.count())
    
    return total_documentos, documentos_sin_texto + documentos_texto_vacio, documentos_texto_incompleto

def obtener_texto_completo(url_xml):
    """
    Obtiene el texto completo de un documento del BOE a partir de su URL XML.
    
    Args:
        url_xml: URL del documento XML
        
    Returns:
        str: Texto completo del documento o None si hay error
    """
    try:
        # Realizar petición HTTP para obtener el XML
        response = requests.get(url_xml, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Error al obtener XML: {response.status_code}")
            return None
        
        # Extraer el texto del XML
        xml_content = response.text
        
        # Extraer el texto entre las etiquetas <texto>...</texto>
        texto_match = re.search(r'<texto>(.*?)</texto>', xml_content, re.DOTALL)
        if texto_match:
            texto_completo = texto_match.group(1)
            
            # Limpiar etiquetas HTML
            texto_completo = re.sub(r'<[^>]+>', ' ', texto_completo)
            
            # Normalizar espacios
            texto_completo = re.sub(r'\s+', ' ', texto_completo).strip()
            
            return texto_completo
        else:
            logger.error(f"No se encontró texto en el XML")
            return None
            
    except Exception as e:
        logger.error(f"Error al obtener texto completo: {str(e)}")
        return None

def actualizar_textos_documentos(dias_atras=30, limite=None):
    """
    Actualiza los textos de documentos que están incompletos o vacíos.
    
    Args:
        dias_atras: Número de días hacia atrás para buscar documentos
        limite: Límite de documentos a actualizar (None para todos)
        
    Returns:
        dict: Estadísticas de la actualización
    """
    print(f"\n=== Actualizando textos de documentos ===")
    
    # Calcular fecha límite
    fecha_limite = datetime.now().date() - timedelta(days=dias_atras)
    
    # Obtener documentos con texto incompleto o vacío
    query = DocumentoSimplificado.objects.filter(
        fecha_publicacion__gte=fecha_limite
    ).filter(
        # Sin texto o texto vacío
        texto__isnull=True
    ) | DocumentoSimplificado.objects.filter(
        fecha_publicacion__gte=fecha_limite,
        texto=''
    )
    
    # Si hay un límite, aplicarlo
    if limite:
        query = query[:limite]
    
    total_documentos = query.count()
    
    if total_documentos == 0:
        print("No se encontraron documentos con texto incompleto o vacío")
        return {"actualizados": 0, "errores": 0}
    
    print(f"Actualizando textos de {total_documentos} documentos...")
    
    # Estadísticas
    actualizados = 0
    errores = 0
    
    # Actualizar cada documento con barra de progreso
    for documento in tqdm(query, total=total_documentos, desc="Actualizando textos"):
        # Verificar si tiene URL XML
        if not documento.url_xml:
            logger.warning(f"Documento {documento.identificador} no tiene URL XML")
            errores += 1
            continue
        
        # Obtener texto completo
        texto_completo = obtener_texto_completo(documento.url_xml)
        
        if not texto_completo:
            logger.warning(f"No se pudo obtener texto para {documento.identificador}")
            errores += 1
            continue
        
        # Actualizar documento
        documento.texto = texto_completo
        documento.save()
        actualizados += 1
        
        # Esperar un poco para no sobrecargar el servidor
        time.sleep(0.2)
    
    print(f"\nActualización de textos completada:")
    print(f"Total de documentos procesados: {total_documentos}")
    print(f"Documentos actualizados exitosamente: {actualizados}")
    print(f"Documentos con errores: {errores}")
    
    return {"actualizados": actualizados, "errores": errores}

def actualizar_documentos_qdrant(dias_atras=30, recrear=False, solo_con_texto=True, texto_completo=True):
    """
    Actualiza los documentos en Qdrant para asegurarse de que todos tengan contenido completo.
    
    Args:
        dias_atras: Número de días hacia atrás para sincronizar documentos
        recrear: Si es True, recrea la colección de Qdrant
        solo_con_texto: Si es True, solo indexa documentos que tengan texto
        texto_completo: Si es True, solo indexa documentos con texto de longitud adecuada
    """
    try:
        print(f"\n=== Actualizando documentos en Qdrant ===")
        
        # Verificar la URL y API Key de Qdrant
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            print("Error: No se encontraron las credenciales de Qdrant en el archivo .env")
            print("Asegúrate de tener QDRANT_URL y QDRANT_API_KEY configurados correctamente")
            return
        
        print(f"Conectando a Qdrant en: {qdrant_url}")
        
        # Inicializar cliente de Qdrant
        qdrant = QdrantBOE(url=qdrant_url, api_key=qdrant_api_key)
        
        # Verificar la conexión
        try:
            # Intentar obtener estadísticas para verificar la conexión
            estadisticas = qdrant.obtener_estadisticas()
            if "error" in estadisticas:
                print(f"Error al conectar con Qdrant: {estadisticas['error']}")
                return
            print("Conexión con Qdrant establecida correctamente")
        except Exception as e:
            print(f"Error al conectar con Qdrant: {str(e)}")
            return
        
        # Crear o verificar la colección
        if recrear:
            print("Recreando colección en Qdrant...")
            if not qdrant.crear_coleccion(recrear=True):
                print("Error al recrear la colección en Qdrant")
                return
            print("Colección recreada exitosamente")
        else:
            print("Verificando colección en Qdrant...")
            if not qdrant.crear_coleccion(recrear=False):
                print("Error al verificar la colección en Qdrant")
                return
            print("Colección verificada exitosamente")
        
        # Verificar documentos sin texto
        total_docs, docs_sin_texto, docs_texto_incompleto = verificar_documentos_sin_texto()
        print(f"\nEstadísticas de documentos:")
        print(f"Total de documentos en la base de datos: {total_docs}")
        print(f"Documentos sin texto: {docs_sin_texto} ({(docs_sin_texto/total_docs*100):.2f}%)")
        print(f"Documentos con texto potencialmente incompleto (estimado): {docs_texto_incompleto} ({(docs_texto_incompleto/total_docs*100):.2f}%)")
        
        # Calcular fecha límite
        fecha_limite = datetime.now().date() - timedelta(days=dias_atras)
        
        # Obtener documentos para sincronizar
        query = DocumentoSimplificado.objects.filter(fecha_publicacion__gte=fecha_limite)
        
        # Filtrar según parámetros
        if solo_con_texto:
            query = query.exclude(texto__isnull=True).exclude(texto='')
            print(f"\nSincronizando SOLO documentos con texto de los últimos {dias_atras} días")
            
            if texto_completo:
                print(f"Se filtrarán documentos con texto menor a {LONGITUD_MINIMA_TEXTO} caracteres durante el procesamiento")
        else:
            print(f"\nSincronizando TODOS los documentos de los últimos {dias_atras} días")
        
        total_a_sincronizar = query.count()
        
        if total_a_sincronizar == 0:
            print(f"No se encontraron documentos para sincronizar")
            return
        
        print(f"Indexando {total_a_sincronizar} documentos en Qdrant...")
        
        # Estadísticas
        exitosos = 0
        fallidos = 0
        filtrados_por_longitud = 0
        
        # Indexar cada documento con barra de progreso
        for documento in tqdm(query, total=total_a_sincronizar, desc="Indexando documentos"):
            # Verificar que el documento tenga todos los campos necesarios
            campos_completos = True
            campos_faltantes = []
            
            if not documento.texto or documento.texto.strip() == '':
                campos_completos = False
                campos_faltantes.append('texto')
                
            if not documento.titulo or documento.titulo.strip() == '':
                campos_completos = False
                campos_faltantes.append('titulo')
            
            if not documento.identificador:
                campos_completos = False
                campos_faltantes.append('identificador')
            
            if not documento.fecha_publicacion:
                campos_completos = False
                campos_faltantes.append('fecha_publicacion')
            
            # Si faltan campos esenciales, saltar este documento
            if not campos_completos:
                logger.warning(f"Documento {documento.identificador} incompleto. Campos faltantes: {', '.join(campos_faltantes)}")
                fallidos += 1
                continue
            
            # Verificar longitud del texto si se requiere texto completo
            if texto_completo and documento.texto and len(documento.texto) < LONGITUD_MINIMA_TEXTO:
                logger.warning(f"Documento {documento.identificador} con texto potencialmente incompleto ({len(documento.texto)} caracteres)")
                filtrados_por_longitud += 1
                continue
            
            # Indexar documento en Qdrant
            if qdrant.indexar_documento(documento):
                exitosos += 1
            else:
                fallidos += 1
        
        # Mostrar estadísticas
        print(f"\nSincronización completada:")
        print(f"Total de documentos procesados: {total_a_sincronizar}")
        print(f"Documentos indexados exitosamente: {exitosos}")
        print(f"Documentos filtrados por longitud de texto: {filtrados_por_longitud}")
        print(f"Documentos con errores: {fallidos}")
        
        # Obtener estadísticas de la colección
        print("\nEstadísticas de la colección en Qdrant:")
        estadisticas = qdrant.obtener_estadisticas()
        
        if "error" in estadisticas:
            print(f"Error al obtener estadísticas: {estadisticas['error']}")
        else:
            print(f"Vectores: {estadisticas['vectores']}")
            print(f"Puntos: {estadisticas['puntos']}")
            print(f"Segmentos: {estadisticas['segmentos']}")
            print(f"Estado: {estadisticas['status']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Actualizar documentos en Qdrant')
    parser.add_argument('--dias', type=int, default=30, help='Número de días hacia atrás para sincronizar documentos')
    parser.add_argument('--recrear', action='store_true', help='Recrear la colección de Qdrant')
    parser.add_argument('--todos', action='store_true', help='Sincronizar todos los documentos, incluso los que no tienen texto')
    parser.add_argument('--actualizar-textos', action='store_true', help='Actualizar textos incompletos antes de sincronizar')
    parser.add_argument('--limite', type=int, help='Límite de documentos a actualizar')
    parser.add_argument('--incluir-incompletos', action='store_true', help='Incluir documentos con texto potencialmente incompleto')
    
    args = parser.parse_args()
    
    # Si se solicita actualizar textos, hacerlo primero
    if args.actualizar_textos:
        actualizar_textos_documentos(dias_atras=args.dias, limite=args.limite)
    
    # Ejecutar actualización de Qdrant
    actualizar_documentos_qdrant(
        dias_atras=args.dias, 
        recrear=args.recrear, 
        solo_con_texto=not args.todos,
        texto_completo=not args.incluir_incompletos
    )
