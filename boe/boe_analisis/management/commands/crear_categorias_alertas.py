from django.core.management.base import BaseCommand
from boe_analisis.models_alertas import CategoriaAlerta

class Command(BaseCommand):
    help = 'Crea categorías predefinidas para las alertas del BOE'

    def handle(self, *args, **options):
        # Lista de categorías a crear
        categorias = [
            {
                'nombre': 'Subvenciones',
                'descripcion': 'Ayudas, subvenciones y financiación pública',
                'palabras_clave': 'subvención, ayuda, financiación, convocatoria, beca, subsidio',
                'color': '#28a745'  # Verde
            },
            {
                'nombre': 'Contratación',
                'descripcion': 'Licitaciones, contratos públicos y concursos',
                'palabras_clave': 'licitación, contrato, concurso, adjudicación, pliego',
                'color': '#007bff'  # Azul
            },
            {
                'nombre': 'Legislación',
                'descripcion': 'Leyes, decretos y normativa legal',
                'palabras_clave': 'ley, decreto, real decreto, orden, normativa, reglamento',
                'color': '#dc3545'  # Rojo
            },
            {
                'nombre': 'Empleo Público',
                'descripcion': 'Oposiciones, concursos y empleo en el sector público',
                'palabras_clave': 'oposición, plaza, funcionario, empleo público, concurso, bolsa',
                'color': '#6f42c1'  # Púrpura
            },
            {
                'nombre': 'Fiscal',
                'descripcion': 'Impuestos, tributos y normativa fiscal',
                'palabras_clave': 'impuesto, tributo, fiscal, IRPF, IVA, hacienda',
                'color': '#fd7e14'  # Naranja
            },
            {
                'nombre': 'Laboral',
                'descripcion': 'Normativa laboral, convenios y relaciones laborales',
                'palabras_clave': 'convenio colectivo, laboral, trabajador, salario, jornada',
                'color': '#20c997'  # Verde azulado
            },
            {
                'nombre': 'Educación',
                'descripcion': 'Normativa educativa, becas y formación',
                'palabras_clave': 'educación, universidad, escuela, formación, beca, estudiante',
                'color': '#ffc107'  # Amarillo
            },
            {
                'nombre': 'Sanidad',
                'descripcion': 'Normativa sanitaria y salud pública',
                'palabras_clave': 'sanidad, salud, hospital, médico, farmacia, sanitario',
                'color': '#17a2b8'  # Cian
            },
            {
                'nombre': 'Medio Ambiente',
                'descripcion': 'Normativa medioambiental y sostenibilidad',
                'palabras_clave': 'medio ambiente, ecológico, sostenible, contaminación, residuo',
                'color': '#4caf50'  # Verde claro
            },
            {
                'nombre': 'Tecnología',
                'descripcion': 'Normativa tecnológica, digital y telecomunicaciones',
                'palabras_clave': 'tecnología, digital, informática, telecomunicaciones, internet',
                'color': '#9c27b0'  # Morado
            }
        ]

        # Contador para las categorías creadas y actualizadas
        creadas = 0
        actualizadas = 0

        # Crear o actualizar cada categoría
        for categoria_data in categorias:
            categoria, created = CategoriaAlerta.objects.update_or_create(
                nombre=categoria_data['nombre'],
                defaults={
                    'descripcion': categoria_data['descripcion'],
                    'palabras_clave': categoria_data['palabras_clave'],
                    'color': categoria_data['color']
                }
            )

            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f'Categoría creada: {categoria.nombre}'))
            else:
                actualizadas += 1
                self.stdout.write(self.style.WARNING(f'Categoría actualizada: {categoria.nombre}'))

        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS(
            f'Proceso completado: {creadas} categorías creadas, {actualizadas} categorías actualizadas'
        ))
