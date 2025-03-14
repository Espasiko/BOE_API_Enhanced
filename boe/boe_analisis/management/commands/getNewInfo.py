import requests
import logging
from django.core.management.base import BaseCommand, CommandError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from boe_analisis.models_simplified import DocumentoSimplificado

class Command(BaseCommand):
    help = 'Get new information from BOE'
    
    def __init__(self):
        super(Command, self).__init__()
        self.session = requests.Session()
        self.timeout = 30
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def add_arguments(self, parser):
        parser.add_argument('--days', action='store', dest='days', default=1, type=int,
                            help='Number of days to get')
        parser.add_argument('--start', action='store', dest='start', default=None, type=str,
                            help='Start date (format: YYYY-MM-DD)')
    
    def handle(self, *args, **options):
        days = options['days']
        start = options['start']
        
        if start:
            try:
                d = datetime.strptime(start, '%Y-%m-%d')
            except ValueError:
                self.logger.error("Formato de fecha incorrecto. Debe ser YYYY-MM-DD")
                return
        else:
            d = datetime.now()
        
        self.logger.info(f"Obteniendo información del BOE para {days} días a partir de {d.strftime('%Y-%m-%d')}")
        
        for i in range(days):
            current_date = d - timedelta(days=i)
            self.logger.info(f"Procesando fecha: {current_date.strftime('%Y-%m-%d')}")
            
            # Intentar obtener el sumario
            sumario_xml = self.get_sumario(current_date)
            
            if sumario_xml:
                self.logger.info("Sumario obtenido correctamente. Procesando documentos...")
                self.process_sumario(sumario_xml)
            else:
                self.logger.error(f"No se pudo obtener el sumario para la fecha {current_date.strftime('%Y-%m-%d')}")
    
    def get_sumario(self, date):
        """
        Obtiene el sumario del BOE para una fecha específica utilizando la API de datos abiertos
        """
        fecha_str = date.strftime('%Y%m%d')
        
        # URL de la API de datos abiertos del BOE (la que funciona correctamente)
        url = f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/xml, text/xml',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        self.logger.info(f"Solicitando sumario de: {url}")
        
        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            
            self.logger.info(f"Código de estado: {response.status_code}")
            self.logger.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'No especificado')}")
            
            if response.status_code == 200:
                # Verificar si la respuesta es XML válido
                if response.text.strip().startswith('<!DOCTYPE html>'):
                    self.logger.error("La respuesta es HTML, no XML. Posible error del servidor.")
                    return None
                
                # Verificar si el XML contiene un sumario válido
                if '<sumario>' in response.text:
                    self.logger.info("Sumario XML recibido correctamente")
                    
                    # Intentar parsear el XML para verificar su estructura
                    try:
                        # Verificar la estructura del XML según la API de datos abiertos
                        root = ET.fromstring(response.text)
                        status_code = root.find('.//status/code')
                        
                        if status_code is not None and status_code.text == '200':
                            self.logger.info("Estructura XML válida")
                            return response.text
                        else:
                            self.logger.error("El XML no tiene la estructura esperada")
                            return None
                    except ET.ParseError as e:
                        self.logger.error(f"Error al parsear el XML: {str(e)}")
                        return None
                else:
                    self.logger.error("La respuesta no contiene un sumario válido")
                    return None
            else:
                self.logger.error(f"Error HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la petición HTTP: {str(e)}")
            return None
    
    def process_sumario(self, sumario_xml):
        """
        Procesa el sumario XML y extrae los documentos
        """
        try:
            # Parsear el XML del sumario
            root = ET.fromstring(sumario_xml)
            
            # Extraer la fecha de publicación del sumario
            fecha_publicacion = None
            fecha_elem = root.find('.//data/sumario/metadatos/fecha')
            
            if fecha_elem is not None:
                try:
                    fecha_str = fecha_elem.text
                    self.logger.info(f"Fecha encontrada en el sumario: {fecha_str}")
                    fecha_publicacion = datetime.strptime(fecha_str, '%Y%m%d').date()
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Error al parsear la fecha: {str(e)}")
                    fecha_publicacion = datetime.now().date()
            else:
                self.logger.warning("No se encontró la fecha en el sumario, usando la fecha actual")
                fecha_publicacion = datetime.now().date()
            
            self.logger.info(f"Fecha de publicación: {fecha_publicacion}")
            
            # Extraer documentos según la estructura de la API de datos abiertos
            documentos = root.findall('.//data/sumario/diario/seccion/departamento/epigrafe/item')
            
            if not documentos:
                # Intentar con una estructura alternativa
                documentos = root.findall('.//item')
            
            self.logger.info(f"Se encontraron {len(documentos)} documentos en el sumario")
            
            # Imprimir la estructura del XML para depuración
            self.logger.info("Estructura del XML:")
            for child in root:
                self.logger.info(f"- {child.tag}")
                for subchild in child:
                    self.logger.info(f"  - {subchild.tag}")
            
            for documento in documentos:
                try:
                    # Extraer el ID del documento (cambiado de './id' a './identificador')
                    id_elemento = documento.find('./identificador')
                    
                    if id_elemento is not None:
                        doc_id = id_elemento.text
                        
                        # Verificar si el documento ya existe en la base de datos
                        if not DocumentoSimplificado.objects.filter(identificador=doc_id).exists():
                            self.logger.info(f"Procesando nuevo documento: {doc_id}")
                            
                            # En lugar de usar ProcessDocument, vamos a crear el documento directamente
                            try:
                                # Extraer información básica del documento
                                titulo_elem = documento.find('./titulo')
                                url_pdf_elem = documento.find('./url_pdf')
                                url_xml_elem = documento.find('./url_xml')
                                
                                # Buscar el departamento de varias formas posibles
                                departamento = None
                                # 1. Intentar obtener directamente del elemento
                                departamento_elem = documento.find('./departamento')
                                if departamento_elem is not None and departamento_elem.text:
                                    departamento = departamento_elem.text
                                    self.logger.info(f"Departamento encontrado directamente: {departamento}")
                                
                                # 2. Si no se encuentra, intentar obtenerlo del elemento padre
                                if not departamento:
                                    # Navegar hacia arriba en el árbol XML para encontrar el departamento
                                    parent = documento.getparent()
                                    while parent is not None:
                                        if parent.tag == 'departamento':
                                            # Buscar el nombre del departamento en el atributo nombre
                                            if 'nombre' in parent.attrib:
                                                departamento = parent.attrib['nombre']
                                                self.logger.info(f"Departamento encontrado en padre: {departamento}")
                                                break
                                            # O en un elemento hijo llamado nombre
                                            nombre_elem = parent.find('./nombre')
                                            if nombre_elem is not None and nombre_elem.text:
                                                departamento = nombre_elem.text
                                                self.logger.info(f"Departamento encontrado en elemento nombre: {departamento}")
                                                break
                                        parent = parent.getparent()
                                
                                # 3. Si aún no se encuentra, intentar con XPath más complejo
                                if not departamento:
                                    # Buscar en todo el documento por el ID
                                    xpath_query = f".//item[identificador='{doc_id}']/ancestor::departamento"
                                    departamento_nodes = root.findall(xpath_query)
                                    if departamento_nodes and len(departamento_nodes) > 0:
                                        for dept_node in departamento_nodes:
                                            if 'nombre' in dept_node.attrib:
                                                departamento = dept_node.attrib['nombre']
                                                self.logger.info(f"Departamento encontrado con XPath: {departamento}")
                                                break
                                            nombre_elem = dept_node.find('./nombre')
                                            if nombre_elem is not None and nombre_elem.text:
                                                departamento = nombre_elem.text
                                                self.logger.info(f"Departamento encontrado con XPath en elemento nombre: {departamento}")
                                                break
                                
                                materias_elem = documento.find('./materias')
                                
                                # Imprimir la estructura del documento para depuración
                                self.logger.info(f"Estructura del documento {doc_id}:")
                                for elem in documento:
                                    self.logger.info(f"- {elem.tag}: {elem.text if elem.text else 'None'}")
                                
                                if titulo_elem is not None:
                                    # Crear el documento en la base de datos
                                    titulo = titulo_elem.text if titulo_elem is not None else "Sin título"
                                    url_pdf = url_pdf_elem.text if url_pdf_elem is not None else None
                                    url_xml = url_xml_elem.text if url_xml_elem is not None else None
                                    materias = materias_elem.text if materias_elem is not None else None
                                    
                                    # Imprimir información para depuración
                                    self.logger.info(f"Creando documento con ID: {doc_id}")
                                    self.logger.info(f"Título: {titulo[:100]}...")
                                    self.logger.info(f"Departamento: {departamento}")
                                    self.logger.info(f"Materias: {materias}")
                                    
                                    doc = DocumentoSimplificado(
                                        identificador=doc_id,
                                        fecha_publicacion=fecha_publicacion,
                                        titulo=titulo,
                                        url_pdf=url_pdf,
                                        url_xml=url_xml,
                                        departamento=departamento,
                                        materias=materias
                                    )
                                    
                                    # Intentar obtener el texto completo del documento
                                    if url_xml:
                                        try:
                                            texto = self.get_documento_texto(url_xml)
                                            if texto:
                                                doc.texto = texto
                                        except Exception as e:
                                            self.logger.error(f"Error al obtener el texto del documento {doc_id}: {str(e)}")
                                    
                                    doc.save()
                                    self.logger.info(f"Documento {doc_id} guardado correctamente")
                                else:
                                    self.logger.error(f"No se encontró título para el documento {doc_id}")
                            except Exception as e:
                                self.logger.error(f"Error al procesar documento: {str(e)}")
                        else:
                            self.logger.info(f"El documento {doc_id} ya existe en la base de datos")
                
                except Exception as e:
                    self.logger.error(f"Error al procesar documento: {str(e)}")
            
        except ET.ParseError as e:
            self.logger.error(f"Error al parsear el XML del sumario: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error general al procesar el sumario: {str(e)}")

    def get_documento_texto(self, url_xml):
        """
        Obtiene el texto completo de un documento BOE a partir de su URL XML
        """
        try:
            response = self.session.get(url_xml, timeout=self.timeout)
            
            if response.status_code == 200:
                # Verificar si la respuesta es XML válido
                if response.text.strip().startswith('<!DOCTYPE html>'):
                    self.logger.error("La respuesta es HTML, no XML. Posible error del servidor.")
                    return None
                
                # Intentar parsear el XML para extraer el texto
                try:
                    root = ET.fromstring(response.text)
                    texto_elem = root.find('.//texto')
                    
                    if texto_elem is not None:
                        return texto_elem.text
                    else:
                        self.logger.error("No se encontró el texto del documento")
                        return None
                except ET.ParseError as e:
                    self.logger.error(f"Error al parsear el XML del documento: {str(e)}")
                    return None
            else:
                self.logger.error(f"Error HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la petición HTTP: {str(e)}")
            return None
