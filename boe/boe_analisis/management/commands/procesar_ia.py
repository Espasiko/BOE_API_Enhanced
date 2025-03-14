"""
Comando para procesar documentos con IA
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from boe_analisis.models_alertas import NotificacionAlerta
from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.services_ia import ServicioIA
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Procesa documentos con IA para generar resúmenes y clasificaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Número máximo de documentos a procesar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Procesar incluso documentos ya procesados'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS(f'Iniciando procesamiento de IA para {limit} documentos'))
        
        # Obtener notificaciones sin resumen
        query = NotificacionAlerta.objects.all()
        if not force:
            query = query.filter(Q(resumen__isnull=True) | Q(resumen=''))
        
        notificaciones = query.order_by('-fecha_notificacion')[:limit]
        
        count = 0
        for notificacion in notificaciones:
            try:
                # Obtener documento completo
                documento = DocumentoSimplificado.objects.filter(
                    identificador=notificacion.documento
                ).first()
                
                if not documento:
                    self.stdout.write(self.style.WARNING(
                        f'No se encontró el documento {notificacion.documento}'
                    ))
                    continue
                
                # Texto para procesar (combinamos título y texto)
                texto_completo = f"{documento.titulo}\n\n{documento.texto}"
                
                # Generar resumen
                resumen = ServicioIA.resumir_documento(texto_completo)
                
                # Calcular relevancia más precisa
                relevancia = ServicioIA.calcular_relevancia(
                    texto_completo, 
                    notificacion.alerta.palabras_clave
                )
                
                # Actualizar notificación
                notificacion.resumen = resumen
                notificacion.relevancia = relevancia
                notificacion.save()
                
                count += 1
                
                self.stdout.write(self.style.SUCCESS(
                    f'Procesado documento {notificacion.documento} - Relevancia: {relevancia:.2f}'
                ))
                
            except Exception as e:
                logger.error(f"Error procesando documento {notificacion.documento}: {str(e)}")
                self.stdout.write(self.style.ERROR(
                    f'Error procesando documento {notificacion.documento}: {str(e)}'
                ))
        
        self.stdout.write(self.style.SUCCESS(f'Procesamiento completado. {count} documentos actualizados'))
