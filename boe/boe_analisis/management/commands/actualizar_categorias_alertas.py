import logging
from collections import Counter
from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.models_alertas import CategoriaAlerta

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Actualiza automáticamente las palabras clave de las categorías de alertas basándose en documentos recientes'

    def __init__(self):
        super(Command, self).__init__()
        # Asegurarse de que los recursos de NLTK estén disponibles
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            self.stdout.write('Descargando recursos de NLTK necesarios...')
            nltk.download('punkt')
            nltk.download('stopwords')
        
        # Cargar stopwords en español
        self.stopwords = set(stopwords.words('spanish'))
        # Añadir stopwords adicionales específicas para documentos del BOE
        self.stopwords.update(['mediante', 'según', 'artículo', 'ley', 'real', 'decreto', 
                              'orden', 'resolución', 'disposición', 'anexo', 'boletín', 
                              'oficial', 'estado', 'publicado', 'publicada'])

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de días hacia atrás para analizar documentos (por defecto: 30)'
        )
        parser.add_argument(
            '--min-frecuencia',
            type=int,
            default=3,
            help='Frecuencia mínima para considerar una palabra clave (por defecto: 3)'
        )
        parser.add_argument(
            '--max-palabras',
            type=int,
            default=20,
            help='Número máximo de palabras clave por categoría (por defecto: 20)'
        )
        parser.add_argument(
            '--categoria-id',
            type=int,
            help='ID de una categoría específica para actualizar'
        )
        parser.add_argument(
            '--solo-sugerir',
            action='store_true',
            help='Solo mostrar sugerencias sin actualizar las categorías'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        min_frecuencia = options['min_frecuencia']
        max_palabras = options['max_palabras']
        categoria_id = options['categoria_id']
        solo_sugerir = options['solo_sugerir']
        
        # Fecha de inicio para la búsqueda de documentos
        fecha_inicio = timezone.now().date() - timedelta(days=dias)
        
        # Obtener documentos recientes
        documentos = DocumentoSimplificado.objects.filter(
            fecha_publicacion__gte=fecha_inicio
        )
        
        if not documentos:
            self.stdout.write(self.style.WARNING(
                f'No se encontraron documentos publicados en los últimos {dias} días'
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f'Analizando {documentos.count()} documentos publicados desde {fecha_inicio.strftime("%d/%m/%Y")}'
        ))
        
        # Filtrar categorías si se especificó una ID
        categorias = CategoriaAlerta.objects.all()
        if categoria_id:
            categorias = categorias.filter(id=categoria_id)
            if not categorias:
                self.stdout.write(self.style.ERROR(f'No se encontró la categoría con ID {categoria_id}'))
                return
        
        # Analizar documentos por departamento para cada categoría
        for categoria in categorias:
            self.stdout.write(f'Procesando categoría: {categoria.nombre}')
            
            # Extraer palabras clave actuales
            palabras_actuales = []
            if categoria.palabras_clave:
                palabras_actuales = [p.strip().lower() for p in categoria.palabras_clave.split(',') if p.strip()]
            
            # Determinar departamentos relacionados con la categoría
            departamentos_relacionados = self._obtener_departamentos_relacionados(categoria)
            
            if departamentos_relacionados:
                self.stdout.write(f'  Departamentos relacionados: {", ".join(departamentos_relacionados[:3])}{"..." if len(departamentos_relacionados) > 3 else ""}')
                
                # Filtrar documentos por departamentos relacionados
                q_filter = Q()
                for dep in departamentos_relacionados:
                    q_filter |= Q(departamento__icontains=dep)
                
                docs_filtrados = documentos.filter(q_filter)
                
                if not docs_filtrados:
                    self.stdout.write(self.style.WARNING(f'  No se encontraron documentos para los departamentos relacionados'))
                    continue
                
                self.stdout.write(f'  Analizando {docs_filtrados.count()} documentos relacionados')
                
                # Extraer términos relevantes
                palabras_clave_sugeridas = self._extraer_terminos_relevantes(
                    docs_filtrados, 
                    min_frecuencia=min_frecuencia,
                    max_palabras=max_palabras
                )
                
                # Combinar palabras clave actuales con las nuevas sugeridas
                palabras_combinadas = set(palabras_actuales)
                palabras_nuevas = []
                
                for palabra in palabras_clave_sugeridas:
                    if palabra not in palabras_combinadas:
                        palabras_combinadas.add(palabra)
                        palabras_nuevas.append(palabra)
                
                # Limitar al número máximo de palabras
                palabras_combinadas = list(palabras_combinadas)[:max_palabras]
                
                # Mostrar sugerencias
                if palabras_nuevas:
                    self.stdout.write(self.style.SUCCESS(f'  Nuevas palabras clave sugeridas: {", ".join(palabras_nuevas)}'))
                else:
                    self.stdout.write(f'  No se encontraron nuevas palabras clave relevantes')
                
                # Actualizar la categoría si no es solo sugerencia
                if not solo_sugerir and palabras_nuevas:
                    categoria.palabras_clave = ", ".join(palabras_combinadas)
                    categoria.save()
                    self.stdout.write(self.style.SUCCESS(f'  Categoría actualizada con {len(palabras_nuevas)} nuevas palabras clave'))
            else:
                self.stdout.write(self.style.WARNING(f'  No se pudieron determinar departamentos relacionados'))
        
        self.stdout.write(self.style.SUCCESS('Proceso completado'))

    def _obtener_departamentos_relacionados(self, categoria):
        """
        Determina qué departamentos están relacionados con una categoría
        basándose en su nombre y descripción
        """
        nombre_categoria = categoria.nombre.lower()
        
        # Mapeo de términos comunes a departamentos
        mapeo_departamentos = {
            'economía': ['economía', 'hacienda', 'financiero', 'fiscal', 'tributario'],
            'educación': ['educación', 'universidades', 'ciencia', 'formación'],
            'sanidad': ['sanidad', 'salud', 'consumo'],
            'justicia': ['justicia', 'judicial', 'tribunales'],
            'trabajo': ['trabajo', 'empleo', 'seguridad social', 'laboral'],
            'interior': ['interior', 'seguridad', 'policía', 'guardia civil'],
            'defensa': ['defensa', 'fuerzas armadas', 'militar'],
            'agricultura': ['agricultura', 'pesca', 'alimentación', 'rural'],
            'industria': ['industria', 'comercio', 'turismo'],
            'transporte': ['transporte', 'movilidad', 'infraestructuras'],
            'medio ambiente': ['medio ambiente', 'ecológico', 'transición ecológica'],
            'vivienda': ['vivienda', 'urbanismo', 'territorial'],
            'cultura': ['cultura', 'deporte'],
            'igualdad': ['igualdad', 'inclusión', 'diversidad'],
            'asuntos exteriores': ['asuntos exteriores', 'cooperación', 'unión europea'],
            'presidencia': ['presidencia', 'gobierno'],
            'digital': ['digital', 'telecomunicaciones', 'tecnología']
        }
        
        # Buscar coincidencias en el nombre y descripción de la categoría
        departamentos = []
        
        for dept, terminos in mapeo_departamentos.items():
            for termino in terminos:
                if termino in nombre_categoria or (categoria.descripcion and termino in categoria.descripcion.lower()):
                    departamentos.append(dept)
                    break
        
        # Si no se encontraron coincidencias, usar todos los departamentos
        if not departamentos:
            departamentos = list(mapeo_departamentos.keys())
        
        return departamentos

    def _extraer_terminos_relevantes(self, documentos, min_frecuencia=3, max_palabras=20):
        """
        Extrae términos relevantes de un conjunto de documentos
        """
        # Contador para todas las palabras
        contador_palabras = Counter()
        
        # Patrones para identificar términos legales específicos
        patrones_terminos = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Nombres propios (ej. "Consejo Superior")
            r'\b[A-Za-z]+\s+de\s+[A-Za-z]+\b',  # Frases con "de" (ej. "Ministerio de Hacienda")
            r'\b[A-Za-z]+\s+[A-Za-z]+\s+[A-Za-z]+\b',  # Frases de tres palabras
            r'\b[A-Za-z]+\s+[0-9]+/[0-9]+\b',  # Referencias a leyes (ej. "Ley 7/2021")
        ]
        
        # Procesar cada documento
        for doc in documentos:
            texto = f"{doc.titulo} {doc.materias if doc.materias else ''}"
            
            # Añadir texto completo si está disponible (limitado para eficiencia)
            if doc.texto:
                texto += f" {doc.texto[:5000]}"
            
            # Normalizar texto
            texto = texto.lower()
            
            # Tokenizar y filtrar stopwords
            tokens = word_tokenize(texto, language='spanish')
            tokens_filtrados = [t for t in tokens if t.isalpha() and len(t) > 3 and t not in self.stopwords]
            
            # Contar palabras individuales
            contador_palabras.update(tokens_filtrados)
            
            # Extraer términos específicos usando patrones
            for patron in patrones_terminos:
                terminos = re.findall(patron, texto)
                contador_palabras.update([t.lower() for t in terminos])
        
        # Filtrar por frecuencia mínima y ordenar por frecuencia
        palabras_frecuentes = [palabra for palabra, freq in contador_palabras.most_common(max_palabras * 2) 
                              if freq >= min_frecuencia]
        
        # Eliminar palabras demasiado genéricas o poco informativas
        palabras_filtradas = []
        for palabra in palabras_frecuentes:
            # Evitar palabras muy cortas o muy largas
            if 4 <= len(palabra) <= 30:
                palabras_filtradas.append(palabra)
            
            # Limitar al máximo de palabras
            if len(palabras_filtradas) >= max_palabras:
                break
        
        return palabras_filtradas
