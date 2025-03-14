"""
Comando para buscar documentos en Qdrant utilizando búsqueda semántica.
"""

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from boe_analisis.utils_qdrant import QdrantBOE, get_qdrant_client

class Command(BaseCommand):
    help = 'Busca documentos en Qdrant utilizando búsqueda semántica'
    
    def __init__(self):
        super(Command, self).__init__()
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def add_arguments(self, parser):
        parser.add_argument(
            'texto',
            type=str,
            help='Texto para buscar documentos similares'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=10,
            help='Número máximo de resultados'
        )
        parser.add_argument(
            '--umbral',
            type=float,
            default=0.7,
            help='Umbral mínimo de similitud (0-1)'
        )
        parser.add_argument(
            '--departamento',
            type=str,
            help='Filtrar por departamento'
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=None,
            help='Filtrar por documentos publicados en los últimos N días'
        )
        
    def handle(self, *args, **options):
        texto = options['texto']
        limite = options['limite']
        umbral = options['umbral']
        departamento = options.get('departamento')
        dias = options.get('dias')
        
        try:
            # Preparar filtros
            filtros = {}
            
            if departamento:
                filtros['departamento'] = departamento
                
            if dias:
                fecha_desde = datetime.now().date() - timedelta(days=dias)
                filtros['fecha_desde'] = fecha_desde
            
            # Obtener cliente de Qdrant
            qdrant = get_qdrant_client()
            
            # Realizar búsqueda
            self.stdout.write(self.style.NOTICE(f"Buscando documentos similares a: '{texto}'..."))
            resultados = qdrant.buscar_similares(
                texto=texto,
                limit=limite,
                score_threshold=umbral,
                filtros=filtros
            )
            
            if not resultados:
                self.stdout.write(self.style.WARNING("No se encontraron documentos similares"))
                return
                
            # Mostrar resultados
            self.stdout.write(self.style.SUCCESS(f"Se encontraron {len(resultados)} documentos similares:"))
            
            for i, resultado in enumerate(resultados, 1):
                self.stdout.write(self.style.NOTICE(f"\n{i}. {resultado['identificador']} - Score: {resultado['score']:.4f}"))
                self.stdout.write(f"   Título: {resultado['titulo']}")
                self.stdout.write(f"   Fecha: {resultado['fecha_publicacion']}")
                self.stdout.write(f"   Departamento: {resultado['departamento']}")
                self.stdout.write(f"   Palabras clave: {resultado['palabras_clave']}")
                self.stdout.write(f"   URL PDF: {resultado['url_pdf']}")
            
        except Exception as e:
            self.logger.error(f"Error inesperado: {str(e)}")
            raise CommandError(f"Error inesperado: {str(e)}")
