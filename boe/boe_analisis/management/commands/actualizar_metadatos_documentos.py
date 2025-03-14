import logging
from django.core.management.base import BaseCommand
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.models_alertas import CategoriaAlerta
from boe_analisis.utils_boe import extraer_palabras_clave, extraer_codigo_departamento, obtener_texto_documento
import re

class Command(BaseCommand):
    help = 'Actualiza los metadatos (materias, palabras clave, departamentos) de los documentos existentes'
    
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
        parser.add_argument(
            '--actualizar-texto',
            action='store_true',
            help='Actualizar el texto completo de los documentos que no lo tengan'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar la actualización de todos los documentos, incluso los que ya tienen datos'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Limitar el número de documentos a procesar'
        )
    
    def handle(self, *args, **options):
        actualizar_texto = options['actualizar_texto']
        forzar = options['forzar']
        limite = options['limite']
        
        # Obtener documentos que necesitan actualización
        if forzar:
            documentos = DocumentoSimplificado.objects.all()
            self.logger.info(f"Se actualizarán todos los documentos ({documentos.count()})")
        else:
            # Filtrar documentos sin palabras clave o materias
            documentos = DocumentoSimplificado.objects.filter(
                palabras_clave__isnull=True
            ) | DocumentoSimplificado.objects.filter(
                palabras_clave=''
            ) | DocumentoSimplificado.objects.filter(
                materias__isnull=True
            ) | DocumentoSimplificado.objects.filter(
                materias=''
            )
            self.logger.info(f"Se encontraron {documentos.count()} documentos sin metadatos completos")
        
        # Limitar la cantidad de documentos si se especifica
        if limite and limite > 0:
            documentos = documentos[:limite]
            self.logger.info(f"Limitando a {limite} documentos")
        
        # Contador de documentos actualizados
        actualizados = 0
        
        # Procesar cada documento
        for documento in documentos:
            try:
                cambios = []
                
                # 1. Normalizar departamento
                if documento.departamento:
                    departamento_normalizado = self._normalizar_departamento(documento.departamento)
                    if departamento_normalizado != documento.departamento:
                        documento.departamento = departamento_normalizado
                        cambios.append('departamento')
                
                # 2. Actualizar código de departamento si es necesario
                if (not documento.codigo_departamento or forzar) and documento.departamento:
                    codigo = extraer_codigo_departamento(documento.departamento)
                    if codigo and codigo != documento.codigo_departamento:
                        documento.codigo_departamento = codigo
                        cambios.append('codigo_departamento')
                
                # 3. Obtener texto completo si no existe y se ha solicitado
                if actualizar_texto and (not documento.texto or forzar) and documento.url_xml:
                    texto = obtener_texto_documento(documento.url_xml, self.timeout)
                    if texto and texto != documento.texto:
                        documento.texto = texto
                        cambios.append('texto')
                
                # 4. Extraer palabras clave
                if not documento.palabras_clave or forzar:
                    palabras_clave = extraer_palabras_clave(
                        documento.titulo, 
                        documento.texto if documento.texto else '',
                        self.categorias_alertas
                    )
                    if palabras_clave:
                        documento.palabras_clave = ", ".join(palabras_clave)
                        cambios.append('palabras_clave')
                
                # 5. Extraer materias de los metadatos XML si no existen
                # Esto se haría idealmente con una llamada a la API, pero por ahora
                # usaremos las palabras clave como materias si no hay materias definidas
                if not documento.materias or forzar:
                    if documento.palabras_clave:
                        documento.materias = documento.palabras_clave
                        cambios.append('materias')
                
                # Guardar cambios si se hicieron modificaciones
                if cambios:
                    documento.save(update_fields=cambios)
                    actualizados += 1
                    self.logger.info(f"Documento {documento.identificador} actualizado. Campos: {', '.join(cambios)}")
                
            except Exception as e:
                self.logger.error(f"Error al procesar documento {documento.identificador}: {str(e)}")
        
        self.logger.info(f"Proceso completado. Se actualizaron {actualizados} documentos.")
        self.stdout.write(self.style.SUCCESS(f"Se actualizaron {actualizados} documentos."))
