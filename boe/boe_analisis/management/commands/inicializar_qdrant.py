"""
Comando para inicializar Qdrant e indexar documentos del BOE.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from boe_analisis.utils_qdrant import QdrantBOE, get_qdrant_client

class Command(BaseCommand):
    help = 'Inicializa la colección de Qdrant e indexa documentos del BOE'
    
    def __init__(self):
        super(Command, self).__init__()
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--recrear',
            action='store_true',
            help='Recrear la colección si ya existe'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Límite de documentos a indexar'
        )
        
    def handle(self, *args, **options):
        recrear = options.get('recrear', False)
        limite = options.get('limite')
        
        try:
            # Obtener cliente de Qdrant
            qdrant = get_qdrant_client()
            
            # Crear colección
            self.stdout.write(self.style.NOTICE("Creando colección en Qdrant..."))
            if qdrant.crear_coleccion(recrear=recrear):
                self.stdout.write(self.style.SUCCESS("Colección creada exitosamente"))
            else:
                self.stdout.write(self.style.ERROR("Error al crear la colección"))
                return
                
            # Indexar documentos
            self.stdout.write(self.style.NOTICE(f"Indexando documentos (límite: {limite if limite else 'sin límite'})..."))
            stats = qdrant.indexar_documentos(limit=limite)
            
            if "error" in stats:
                self.stdout.write(self.style.ERROR(f"Error al indexar documentos: {stats['error']}"))
                return
                
            # Mostrar estadísticas
            self.stdout.write(self.style.SUCCESS(
                f"Indexación completada. "
                f"Total: {stats['total']}, "
                f"Exitosos: {stats['exitosos']}, "
                f"Fallidos: {stats['fallidos']}"
            ))
            
            # Obtener estadísticas de la colección
            self.stdout.write(self.style.NOTICE("Obteniendo estadísticas de la colección..."))
            estadisticas = qdrant.obtener_estadisticas()
            
            if "error" in estadisticas:
                self.stdout.write(self.style.ERROR(f"Error al obtener estadísticas: {estadisticas['error']}"))
                return
                
            self.stdout.write(self.style.SUCCESS(
                f"Estadísticas de la colección: "
                f"Vectores: {estadisticas['vectores']}, "
                f"Puntos: {estadisticas['puntos']}, "
                f"Segmentos: {estadisticas['segmentos']}, "
                f"Estado: {estadisticas['status']}"
            ))
            
        except Exception as e:
            self.logger.error(f"Error inesperado: {str(e)}")
            raise CommandError(f"Error inesperado: {str(e)}")
