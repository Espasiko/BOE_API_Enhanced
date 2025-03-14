import logging
from django.core.management.base import BaseCommand
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.utils_boe import obtener_texto_documento
from datetime import datetime

class Command(BaseCommand):
    help = 'Actualiza los textos completos de los documentos del BOE para una fecha específica'
    
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
            default='2025-03-10',
            help='Fecha en formato YYYY-MM-DD (por defecto: 2025-03-10)'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar la actualización de todos los documentos, incluso los que ya tienen texto'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Limitar el número de documentos a procesar'
        )
    
    def handle(self, *args, **options):
        fecha_str = options['fecha']
        forzar = options['forzar']
        limite = options['limite']
        
        try:
            # Convertir string a fecha
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            self.stdout.write(self.style.SUCCESS(f"Actualizando textos de documentos para la fecha: {fecha}"))
            
            # Obtener documentos para la fecha especificada
            if forzar:
                # Si se fuerza, actualizar todos los documentos de la fecha
                documentos = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha)
                self.stdout.write(f"Se actualizarán todos los documentos ({documentos.count()}) para la fecha {fecha}")
            else:
                # Si no se fuerza, actualizar solo los documentos sin texto
                documentos = DocumentoSimplificado.objects.filter(
                    fecha_publicacion=fecha
                ).filter(
                    texto__isnull=True
                ) | DocumentoSimplificado.objects.filter(
                    fecha_publicacion=fecha, 
                    texto=''
                )
                self.stdout.write(f"Se encontraron {documentos.count()} documentos sin texto para la fecha {fecha}")
            
            # Limitar la cantidad de documentos si se especifica
            if limite and limite > 0:
                documentos = documentos[:limite]
                self.stdout.write(f"Limitando a {limite} documentos")
            
            # Contador de documentos actualizados
            actualizados = 0
            errores = 0
            
            # Procesar cada documento
            total = documentos.count()
            for i, documento in enumerate(documentos):
                try:
                    # Mostrar progreso
                    self.stdout.write(f"Procesando documento {i+1}/{total}: {documento.identificador}")
                    
                    # Solo actualizar si hay URL XML disponible
                    if documento.url_xml:
                        # Obtener texto completo del documento
                        texto = obtener_texto_documento(documento.url_xml, self.timeout)
                        
                        if texto and (not documento.texto or documento.texto != texto):
                            # Guardar el texto en el documento
                            documento.texto = texto
                            documento.save(update_fields=['texto'])
                            actualizados += 1
                            self.logger.info(f"Documento {documento.identificador} actualizado con {len(texto)} caracteres")
                            self.stdout.write(self.style.SUCCESS(f"Documento {documento.identificador} actualizado con {len(texto)} caracteres"))
                        elif not texto:
                            self.logger.warning(f"No se pudo obtener texto para el documento {documento.identificador}")
                            self.stdout.write(self.style.WARNING(f"No se pudo obtener texto para el documento {documento.identificador}"))
                    else:
                        self.logger.warning(f"El documento {documento.identificador} no tiene URL XML")
                        self.stdout.write(self.style.WARNING(f"El documento {documento.identificador} no tiene URL XML"))
                        
                except Exception as e:
                    errores += 1
                    self.logger.error(f"Error al procesar documento {documento.identificador}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f"Error al procesar documento {documento.identificador}: {str(e)}"))
            
            # Mostrar resumen
            self.logger.info(f"Proceso completado. Se actualizaron {actualizados} documentos. Errores: {errores}")
            self.stdout.write(self.style.SUCCESS(f"Proceso completado. Se actualizaron {actualizados} documentos. Errores: {errores}"))
            
            # Mostrar estadísticas finales
            docs_con_texto = DocumentoSimplificado.objects.filter(
                fecha_publicacion=fecha, 
                texto__isnull=False
            ).exclude(texto='').count()
            
            total_docs = DocumentoSimplificado.objects.filter(fecha_publicacion=fecha).count()
            docs_sin_texto = total_docs - docs_con_texto
            
            self.stdout.write(f"\nEstadísticas finales para {fecha}:")
            self.stdout.write(f"Total de documentos: {total_docs}")
            if total_docs > 0:
                self.stdout.write(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs*100:.1f}%)")
                self.stdout.write(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs*100:.1f}%)")
            
        except Exception as e:
            self.logger.error(f"Error general: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
