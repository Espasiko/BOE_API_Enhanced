import requests
import logging
from django.core.management.base import BaseCommand, CommandError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from boe_analisis.models_simplified import DocumentoSimplificado as Documento

class Command(BaseCommand):
    help = 'Get new information from BOE using simplified model'
    
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
        Procesa el sumario XML y extrae los documentos usando el modelo simplificado
        """
        try:
            # Parsear el XML del sumario
            root = ET.fromstring(sumario_xml)
            
            # Extraer documentos según la estructura de la API de datos abiertos
            documentos = root.findall('.//data/sumario/diario/seccion/departamento/epigrafe/item')
            
            if not documentos:
                # Intentar con una estructura alternativa
                documentos = root.findall('.//item')
            
            self.logger.info(f"Se encontraron {len(documentos)} documentos en el sumario")
            
            for documento in documentos:
                try:
                    # Extraer el ID del documento
                    id_elemento = documento.find('./identificador')
                    
                    if id_elemento is not None:
                        doc_id = id_elemento.text
                        
                        # Verificar si el documento ya existe en la base de datos
                        if not Documento.objects.filter(identificador=doc_id).exists():
                            self.logger.info(f"Procesando nuevo documento: {doc_id}")
                            
                            try:
                                # Extraer información básica del documento
                                titulo_elem = documento.find('./titulo')
                                url_pdf_elem = documento.find('./url_pdf')
                                url_xml_elem = documento.find('./url_xml')
                                
                                if titulo_elem is not None:
                                    # Crear un nuevo documento con el modelo simplificado
                                    doc = Documento()
                                    doc.identificador = doc_id
                                    doc.titulo = titulo_elem.text if titulo_elem is not None else "Sin título"
                                    doc.url_pdf = url_pdf_elem.text if url_pdf_elem is not None else None
                                    doc.url_xml = url_xml_elem.text if url_xml_elem is not None else None
                                    
                                    # Extraer fecha de publicación del sumario
                                    fecha_str = root.find('.//data/sumario/metadatos/fecha_publicacion')
                                    if fecha_str is not None:
                                        try:
                                            fecha = datetime.strptime(fecha_str.text, '%Y%m%d').date()
                                            doc.fecha_publicacion = fecha
                                        except (ValueError, TypeError):
                                            doc.fecha_publicacion = datetime.now().date()
                                    else:
                                        doc.fecha_publicacion = datetime.now().date()
                                    
                                    # Extraer departamento si está disponible
                                    departamento_elem = documento.find('./departamento')
                                    doc.departamento = departamento_elem.text if departamento_elem is not None else None
                                    
                                    # Extraer materias si están disponibles
                                    materias_elem = documento.find('./materias')
                                    if materias_elem is not None:
                                        materias = []
                                        for materia in materias_elem.findall('./materia'):
                                            if materia.text:
                                                materias.append(materia.text)
                                        doc.materias = ", ".join(materias) if materias else None
                                    
                                    # Por defecto, el documento está vigente
                                    doc.vigente = True
                                    
                                    # Guardar el documento
                                    doc.save()
                                    self.logger.info(f"Documento guardado: {doc_id}")
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
