import logging
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.utils_boe import obtener_sumario_boe, obtener_texto_documento, extraer_palabras_clave
from datetime import datetime
from tqdm import tqdm
import requests

class Command(BaseCommand):
    help = 'Carga el sumario del BOE para una fecha específica y guarda los documentos en la base de datos'
    
    def __init__(self):
        super(Command, self).__init__()
        self.timeout = 60
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            default=None,
            help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)'
        )
        parser.add_argument(
            '--con-texto',
            action='store_true',
            help='Obtener también el texto completo de los documentos'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Limitar el número de documentos a procesar'
        )
    
    def handle(self, *args, **options):
        fecha_str = options['fecha']
        con_texto = options['con_texto']
        limite = options['limite']
        
        try:
            # Usar la fecha proporcionada o la fecha actual
            if fecha_str:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                fecha = datetime.now().date()
            
            self.stdout.write(self.style.SUCCESS(f"Cargando sumario del BOE para la fecha: {fecha}"))
            
            # Obtener el sumario del BOE
            sumario_xml = obtener_sumario_boe(fecha, self.timeout)
            
            if not sumario_xml:
                self.stdout.write(self.style.ERROR(f"No se pudo obtener el sumario del BOE para la fecha {fecha}"))
                return
            
            # Parsear el XML
            try:
                root = ET.fromstring(sumario_xml)
            except ET.ParseError as e:
                self.stdout.write(self.style.ERROR(f"Error al parsear el XML: {str(e)}"))
                return
            
            # Extraer los documentos del sumario (elementos 'item')
            documentos_xml = []
            
            # Buscar todos los elementos 'item' en el XML
            for item in root.findall('.//item'):
                # Verificar que el item tiene identificador y título
                identificador = item.find('identificador')
                titulo = item.find('titulo')
                if identificador is not None and identificador.text and titulo is not None and titulo.text:
                    documentos_xml.append(item)
            
            if not documentos_xml:
                self.stdout.write(self.style.WARNING(f"No se encontraron documentos válidos en el sumario para la fecha {fecha}"))
                return
            
            self.stdout.write(f"Se encontraron {len(documentos_xml)} documentos válidos en el sumario")
            
            # Limitar la cantidad de documentos si se especifica
            if limite and limite > 0:
                documentos_xml = documentos_xml[:limite]
                self.stdout.write(f"Limitando a {limite} documentos")
            
            # Contador de documentos procesados
            creados = 0
            actualizados = 0
            errores = 0
            
            # Procesar cada documento con barra de progreso
            for i, doc_xml in enumerate(tqdm(documentos_xml, desc="Procesando documentos")):
                try:
                    # Extraer información básica
                    identificador = doc_xml.find('identificador').text
                    titulo = doc_xml.find('titulo').text
                    
                    # URLs pueden tener diferentes nombres en el XML
                    url_pdf = None
                    url_xml = None
                    
                    # Buscar URL del PDF
                    pdf_elem = doc_xml.find('url_pdf')
                    if pdf_elem is not None and pdf_elem.text:
                        # Asegurarse de que la URL sea absoluta
                        if pdf_elem.text.startswith('http'):
                            url_pdf = pdf_elem.text
                        else:
                            url_pdf = f"https://www.boe.es{pdf_elem.text}"
                    
                    # Buscar URL del XML
                    xml_elem = doc_xml.find('url_xml')
                    if xml_elem is not None and xml_elem.text:
                        # Asegurarse de que la URL sea absoluta
                        if xml_elem.text.startswith('http'):
                            url_xml = xml_elem.text
                        else:
                            url_xml = f"https://www.boe.es{xml_elem.text}"
                    
                    # Intentar extraer el departamento utilizando la estructura del XML
                    # En lugar de usar getparent(), vamos a buscar el departamento en todo el árbol
                    departamento = "No especificado"
                    
                    # Buscar todos los departamentos en el XML
                    for dept in root.findall('.//departamento'):
                        # Verificar si este departamento contiene nuestro item
                        for item in dept.findall('.//item'):
                            id_elem = item.find('identificador')
                            if id_elem is not None and id_elem.text == identificador:
                                # Encontramos el departamento correcto
                                nombre_attr = dept.get('nombre')
                                if nombre_attr:
                                    departamento = nombre_attr
                                break
                    
                    # Verificar si el documento ya existe
                    doc_existente = DocumentoSimplificado.objects.filter(identificador=identificador).first()
                    
                    if doc_existente:
                        # Actualizar documento existente
                        doc_existente.titulo = titulo
                        doc_existente.url_pdf = url_pdf
                        doc_existente.url_xml = url_xml
                        doc_existente.departamento = departamento
                        
                        # Obtener texto completo si se solicita
                        if con_texto and url_xml and (not doc_existente.texto or doc_existente.texto == ''):
                            texto = self.obtener_texto_completo(url_xml)
                            if texto:
                                doc_existente.texto = texto
                                self.logger.info(f"Texto actualizado para {identificador}: {len(texto)} caracteres")
                        
                        # Guardar cambios
                        doc_existente.save()
                        actualizados += 1
                        self.logger.info(f"Documento actualizado: {identificador}")
                    else:
                        # Crear nuevo documento
                        nuevo_doc = DocumentoSimplificado(
                            identificador=identificador,
                            fecha_publicacion=fecha,
                            titulo=titulo,
                            url_pdf=url_pdf,
                            url_xml=url_xml,
                            departamento=departamento
                        )
                        
                        # Obtener texto completo si se solicita
                        if con_texto and url_xml:
                            texto = self.obtener_texto_completo(url_xml)
                            if texto:
                                nuevo_doc.texto = texto
                                self.logger.info(f"Texto obtenido para {identificador}: {len(texto)} caracteres")
                        
                        # Guardar nuevo documento
                        nuevo_doc.save()
                        creados += 1
                        self.logger.info(f"Documento creado: {identificador}")
                    
                except Exception as e:
                    errores += 1
                    self.logger.error(f"Error al procesar documento {identificador if 'identificador' in locals() else i+1}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f"Error al procesar documento {identificador if 'identificador' in locals() else i+1}: {str(e)}"))
            
            # Mostrar resumen
            self.logger.info(f"Proceso completado. Documentos creados: {creados}, actualizados: {actualizados}, errores: {errores}")
            self.stdout.write(self.style.SUCCESS(f"Proceso completado. Documentos creados: {creados}, actualizados: {actualizados}, errores: {errores}"))
            
            # Mostrar estadísticas finales
            total_docs = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha).count()
            docs_con_texto = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha, 
                texto__isnull=False
            ).exclude(texto='').count()
            
            docs_sin_texto = total_docs - docs_con_texto
            
            self.stdout.write(f"\nEstadísticas finales para {fecha}:")
            self.stdout.write(f"Total de documentos: {total_docs}")
            if total_docs > 0:
                self.stdout.write(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs*100:.1f}%)")
                self.stdout.write(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs*100:.1f}%)")
            
        except Exception as e:
            self.logger.error(f"Error general: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
    
    def obtener_texto_completo(self, url_xml):
        """
        Obtiene el texto completo de un documento a partir de su URL XML
        """
        try:
            # Obtener el XML del documento
            response = requests.get(url_xml, timeout=self.timeout)
            if response.status_code != 200:
                self.logger.warning(f"Error al obtener el XML del documento: {response.status_code}")
                return None
            
            # Parsear el XML
            root = ET.fromstring(response.content)
            
            # Buscar el elemento 'texto'
            texto_elem = root.find('.//texto')
            if texto_elem is None:
                self.logger.warning(f"No se encontró el elemento 'texto' en el XML")
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
            self.logger.error(f"Error al obtener el texto completo: {str(e)}")
            return None
