import logging
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from boe_analisis.models_simplified import DocumentoSimplificado as Documento
from boe_analisis.models_alertas import CategoriaAlerta
from boe_analisis.utils_boe import (
    obtener_sumario_boe, 
    obtener_texto_documento, 
    extraer_codigo_departamento,
    extraer_palabras_clave
)

class Command(BaseCommand):
    help = 'Obtiene nueva información del BOE usando el modelo simplificado y actualiza materias y palabras clave'
    
    def __init__(self):
        super(Command, self).__init__()
        self.timeout = 30
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        # Cargar categorías de alertas para extraer palabras clave
        self.categorias_alertas = self._cargar_categorias_alertas()
        # Mapa de normalización de departamentos
        self.mapa_departamentos = self._crear_mapa_departamentos()
        
    def _cargar_categorias_alertas(self):
        """
        Carga las categorías de alertas y sus palabras clave para usarlas en la extracción
        """
        categorias = {}
        for categoria in CategoriaAlerta.objects.all():
            if categoria.palabras_clave:
                palabras = [p.strip().lower() for p in categoria.palabras_clave.split(',')]
                categorias[categoria.nombre] = palabras
        
        self.logger.info(f"Se cargaron {len(categorias)} categorías de alertas con palabras clave")
        return categorias
    
    def _crear_mapa_departamentos(self):
        """
        Crea un mapa para normalizar los nombres de departamentos
        """
        # Patrones comunes y sus normalizaciones
        return {
            r'ministerio\s+de\s+hacienda.*': 'Ministerio de Hacienda',
            r'ministerio\s+de\s+cultura.*': 'Ministerio de Cultura',
            r'ministerio\s+de\s+educaci[oó]n.*': 'Ministerio de Educación',
            r'ministerio\s+de\s+trabajo.*': 'Ministerio de Trabajo',
            r'ministerio\s+de\s+justicia.*': 'Ministerio de Justicia',
            r'ministerio\s+de\s+sanidad.*': 'Ministerio de Sanidad',
            r'ministerio\s+de\s+interior.*': 'Ministerio del Interior',
            r'ministerio\s+de\s+defensa.*': 'Ministerio de Defensa',
            r'ministerio\s+de\s+econom[ií]a.*': 'Ministerio de Economía',
            r'ministerio\s+de\s+industria.*': 'Ministerio de Industria',
            r'ministerio\s+de\s+ciencia.*': 'Ministerio de Ciencia',
            r'ministerio\s+de\s+agricultura.*': 'Ministerio de Agricultura',
            r'ministerio\s+de\s+transporte.*': 'Ministerio de Transportes',
            r'ministerio\s+de\s+asuntos\s+exteriores.*': 'Ministerio de Asuntos Exteriores',
            r'ministerio\s+de\s+transici[oó]n\s+ecol[oó]gica.*': 'Ministerio de Transición Ecológica',
            r'ministerio\s+de\s+igualdad.*': 'Ministerio de Igualdad',
            r'ministerio\s+de\s+inclusi[oó]n.*': 'Ministerio de Inclusión',
            r'ministerio\s+de\s+universidades.*': 'Ministerio de Universidades',
            r'ministerio\s+de\s+consumo.*': 'Ministerio de Consumo',
            r'ministerio\s+de\s+derechos\s+sociales.*': 'Ministerio de Derechos Sociales',
            r'ministerio\s+de\s+pol[ií]tica\s+territorial.*': 'Ministerio de Política Territorial',
            r'banco\s+de\s+espa[ñn]a.*': 'Banco de España',
            r'universidad.*': 'Universidades',
            r'cortes\s+generales.*': 'Cortes Generales',
            r'tribunal\s+constitucional.*': 'Tribunal Constitucional',
            r'tribunal\s+supremo.*': 'Tribunal Supremo',
            r'tribunal\s+de\s+cuentas.*': 'Tribunal de Cuentas',
            r'consejo\s+general\s+del\s+poder\s+judicial.*': 'Consejo General del Poder Judicial',
            r'junta\s+electoral\s+central.*': 'Junta Electoral Central',
            r'comisi[oó]n\s+nacional.*': 'Comisión Nacional',
        }
    
    def _normalizar_departamento(self, departamento):
        """
        Normaliza el nombre del departamento para evitar duplicados
        """
        if not departamento:
            return None
            
        departamento_lower = departamento.lower()
        
        for patron, normalizacion in self.mapa_departamentos.items():
            if re.search(patron, departamento_lower):
                return normalizacion
                
        return departamento
        
    def add_arguments(self, parser):
        parser.add_argument('--days', action='store', dest='days', default=1, type=int,
                            help='Número de días a obtener')
        parser.add_argument('--start', action='store', dest='start', default=None, type=str,
                            help='Fecha de inicio (formato: YYYY-MM-DD)')
        parser.add_argument('--update-existing', action='store_true', dest='update_existing',
                            help='Actualizar documentos existentes con nuevas materias y palabras clave')
    
    def handle(self, *args, **options):
        days = options['days']
        start = options['start']
        update_existing = options['update_existing']
        
        if start:
            try:
                d = datetime.strptime(start, '%Y-%m-%d')
            except ValueError:
                self.logger.error("Formato de fecha incorrecto. Debe ser YYYY-MM-DD")
                return
        else:
            d = datetime.now()
        
        self.logger.info(f"Obteniendo información del BOE para {days} días a partir de {d.strftime('%Y-%m-%d')}")
        
        if update_existing:
            self.logger.info("Se actualizarán los documentos existentes con nuevas materias y palabras clave")
            self._actualizar_documentos_existentes()
        
        for i in range(days):
            current_date = d - timedelta(days=i)
            self.logger.info(f"Procesando fecha: {current_date.strftime('%Y-%m-%d')}")
            
            # Intentar obtener el sumario
            sumario_xml = obtener_sumario_boe(current_date, self.timeout)
            
            if sumario_xml:
                self.logger.info("Sumario obtenido correctamente. Procesando documentos...")
                self.process_sumario(sumario_xml)
            else:
                self.logger.error(f"No se pudo obtener el sumario para la fecha {current_date.strftime('%Y-%m-%d')}")
    
    def _actualizar_documentos_existentes(self):
        """
        Actualiza los documentos existentes que no tienen palabras clave o materias
        """
        # Obtener documentos sin palabras clave
        docs_sin_palabras_clave = Documento.objects.filter(palabras_clave__isnull=True) | Documento.objects.filter(palabras_clave='')
        self.logger.info(f"Se encontraron {docs_sin_palabras_clave.count()} documentos sin palabras clave")
        
        for doc in docs_sin_palabras_clave:
            palabras_clave = extraer_palabras_clave(doc.titulo, doc.texto if doc.texto else '', self.categorias_alertas)
            if palabras_clave:
                doc.palabras_clave = ", ".join(palabras_clave)
                doc.save(update_fields=['palabras_clave'])
                self.logger.info(f"Actualizadas palabras clave para documento {doc.identificador}")
        
        # Obtener documentos sin código de departamento
        docs_sin_codigo = Documento.objects.filter(codigo_departamento__isnull=True) | Documento.objects.filter(codigo_departamento='')
        self.logger.info(f"Se encontraron {docs_sin_codigo.count()} documentos sin código de departamento")
        
        for doc in docs_sin_codigo:
            if doc.departamento:
                codigo = extraer_codigo_departamento(doc.departamento)
                if codigo:
                    doc.codigo_departamento = codigo
                    doc.save(update_fields=['codigo_departamento'])
                    self.logger.info(f"Actualizado código de departamento para documento {doc.identificador}")
    
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
                        doc_existente = Documento.objects.filter(identificador=doc_id).first()
                        
                        if not doc_existente:
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
                                    if departamento_elem is not None:
                                        doc.departamento = self._normalizar_departamento(departamento_elem.text)
                                        # Extraer código de departamento
                                        doc.codigo_departamento = extraer_codigo_departamento(doc.departamento)
                                    
                                    # Extraer materias si están disponibles
                                    materias_elem = documento.find('./materias')
                                    if materias_elem is not None:
                                        materias = []
                                        for materia in materias_elem.findall('./materia'):
                                            if materia.text:
                                                materias.append(materia.text)
                                        doc.materias = ", ".join(materias) if materias else None
                                    
                                    # Obtener texto completo si está disponible
                                    if doc.url_xml:
                                        doc.texto = obtener_texto_documento(doc.url_xml, self.timeout)
                                    
                                    # Extraer palabras clave
                                    palabras_clave = extraer_palabras_clave(doc.titulo, doc.texto if doc.texto else '', self.categorias_alertas)
                                    if palabras_clave:
                                        doc.palabras_clave = ", ".join(palabras_clave)
                                    
                                    # Usar palabras clave como materias si no hay materias definidas
                                    if not doc.materias and doc.palabras_clave:
                                        doc.materias = doc.palabras_clave
                                    
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
                            
                            # Si se ha solicitado actualizar documentos existentes
                            if not doc_existente.palabras_clave or not doc_existente.materias or not doc_existente.codigo_departamento:
                                self.logger.info(f"Actualizando información para documento existente: {doc_id}")
                                
                                # Actualizar materias si no existen
                                if not doc_existente.materias:
                                    materias_elem = documento.find('./materias')
                                    if materias_elem is not None:
                                        materias = []
                                        for materia in materias_elem.findall('./materia'):
                                            if materia.text:
                                                materias.append(materia.text)
                                        doc_existente.materias = ", ".join(materias) if materias else None
                                
                                # Actualizar código de departamento si no existe
                                if not doc_existente.codigo_departamento and doc_existente.departamento:
                                    doc_existente.codigo_departamento = extraer_codigo_departamento(doc_existente.departamento)
                                
                                # Actualizar palabras clave si no existen
                                if not doc_existente.palabras_clave:
                                    # Obtener texto si no existe
                                    if not doc_existente.texto and doc_existente.url_xml:
                                        doc_existente.texto = obtener_texto_documento(doc_existente.url_xml, self.timeout)
                                    
                                    palabras_clave = extraer_palabras_clave(
                                        doc_existente.titulo, 
                                        doc_existente.texto if doc_existente.texto else '',
                                        self.categorias_alertas
                                    )
                                    if palabras_clave:
                                        doc_existente.palabras_clave = ", ".join(palabras_clave)
                                    
                                    # Usar palabras clave como materias si no hay materias definidas
                                    if not doc_existente.materias and doc_existente.palabras_clave:
                                        doc_existente.materias = doc_existente.palabras_clave
                                
                                # Guardar cambios
                                doc_existente.save()
                                self.logger.info(f"Documento actualizado: {doc_id}")
                
                except Exception as e:
                    self.logger.error(f"Error al procesar documento: {str(e)}")
            
        except ET.ParseError as e:
            self.logger.error(f"Error al parsear el XML del sumario: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error general al procesar el sumario: {str(e)}")
