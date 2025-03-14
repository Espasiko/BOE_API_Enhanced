from tastypie.resources import ModelResource
from tastypie import fields
from boe_analisis.models import *
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from django.db.models import Q
import datetime

class MyModelResource(ModelResource):
    def determine_format(self, request):
        return 'application/json'

class DiarioResource(MyModelResource):
    class Meta:
        queryset = Diario.objects.all()
        resource_name = 'diario'
        filtering = {
            'nombre': ALL,
        }

class DepartamentoResource(MyModelResource):
    class Meta:
        queryset = Departamento.objects.all()
        resource_name = 'departamento'
        filtering = {
            'nombre': ALL,
        }

class MateriaResource(MyModelResource):
    class Meta:
        queryset = Materia.objects.all()
        resource_name = 'materia'
        filtering = {
            'titulo': ALL,
        }

class RangoResource(MyModelResource):
    class Meta:
        queryset = Rango.objects.all()
        resource_name = 'rango'
        filtering = {
            'nombre': ALL,
        }

class PartidoResource(MyModelResource):
    class Meta:
        queryset = Partido.objects.all()
        resource_name = 'partido'
        filtering = {
            'nombre': ALL,
        }

class LegislaturaResource(MyModelResource):
    partido = fields.ForeignKey('boe_analisis.api.PartidoResource', 'partido', null=True)

    class Meta:
        queryset = Legislatura.objects.all()
        resource_name = 'legislatura'
        filtering = {
            'presidente': ALL,
            'inicio': ALL,
            'fin': ALL,
            'partido': ALL_WITH_RELATIONS,
        }

class Estado_consolidacionResource(MyModelResource):
    class Meta:
        queryset = Estado_consolidacion.objects.all()
        resource_name = 'estado_consolidacion'
        filtering = {
            'nombre': ALL,
        }

class Origen_legislativoResource(MyModelResource):
    class Meta:
        queryset = Origen_legislativo.objects.all()
        resource_name = 'origen_legislativo'
        filtering = {
            'nombre': ALL,
        }

class DocumentoResource(MyModelResource):
    departamento = fields.ForeignKey(DepartamentoResource, 'departamento', null=True)
    rango = fields.ForeignKey(RangoResource, 'rango', null=True)
    estado_consolidacion = fields.ForeignKey(Estado_consolidacionResource, 'estado_consolidacion', null=True)
    origen_legislativo = fields.ForeignKey(Origen_legislativoResource, 'origen_legislativo', null=True)
    materias = fields.ManyToManyField(MateriaResource, 'materias', null=True)
    diario = fields.ForeignKey(DiarioResource, 'diario', null=True)
    legislatura = fields.ForeignKey(LegislaturaResource, 'legislatura', null=True)

    class Meta:
        queryset = Documento.objects.exclude(url_xml=None).order_by('fecha_publicacion')
        resource_name = 'documento'
        filtering = {
            'identificador': ALL,
            'fecha_publicacion': ALL,
            'fecha_disposicion': ALL,
            'titulo': ALL,
            'texto': ALL,
            'url_pdf': ALL,
            'url_xml': ALL,
            'seccion': ALL,
            'departamento': ALL_WITH_RELATIONS,
            'rango': ALL_WITH_RELATIONS,
            'estado_consolidacion': ALL_WITH_RELATIONS,
            'origen_legislativo': ALL_WITH_RELATIONS,
            'materias': ALL_WITH_RELATIONS,
            'diario': ALL_WITH_RELATIONS,
            'legislatura': ALL_WITH_RELATIONS,
        }

    def build_filters(self, filters=None, **kwargs):
        if filters is None:
            filters = {}

        orm_filters = super().build_filters(filters)

        if 'q' in filters:
            query = filters['q']
            qset = (
                Q(titulo__icontains=query) |
                Q(texto__icontains=query)
            )
            orm_filters['custom'] = qset

        return orm_filters

    def apply_filters(self, request, applicable_filters):
        if 'custom' in applicable_filters:
            custom = applicable_filters.pop('custom')
        else:
            custom = None

        semi_filtered = super().apply_filters(request, applicable_filters)

        return semi_filtered.filter(custom) if custom else semi_filtered

class BOEResource(DocumentoResource):
    class Meta:
        queryset = Documento.objects.exclude(url_xml=None).filter(diario__nombre='BOE').order_by('fecha_publicacion')
        resource_name = 'boe'
        filtering = {
            'identificador': ALL,
            'fecha_publicacion': ALL,
            'fecha_disposicion': ALL,
            'titulo': ALL,
            'texto': ALL,
            'url_pdf': ALL,
            'url_xml': ALL,
            'seccion': ALL,
            'departamento': ALL_WITH_RELATIONS,
            'rango': ALL_WITH_RELATIONS,
            'estado_consolidacion': ALL_WITH_RELATIONS,
            'origen_legislativo': ALL_WITH_RELATIONS,
            'materias': ALL_WITH_RELATIONS,
            'diario': ALL_WITH_RELATIONS,
            'legislatura': ALL_WITH_RELATIONS,
        }

class PalabraResource(MyModelResource):
    class Meta:
        queryset = Palabra.objects.all()
        resource_name = 'palabra'
        filtering = {
            'texto': ALL,
        }

class ReferenciaResource(MyModelResource):
    referencia = fields.ForeignKey(DocumentoResource, 'referencia')
    palabra = fields.ForeignKey(PalabraResource, 'palabra')
    documento = fields.ForeignKey(DocumentoResource, 'documento')

    class Meta:
        queryset = Referencia.objects.all()
        resource_name = 'referencia'
        filtering = {
            'referencia': ALL_WITH_RELATIONS,
            'palabra': ALL_WITH_RELATIONS,
            'documento': ALL_WITH_RELATIONS,
        }

class NotaResource(MyModelResource):
    documento = fields.ForeignKey(DocumentoResource, 'documento')

    class Meta:
        queryset = Nota.objects.all()
        resource_name = 'nota'
        filtering = {
            'texto': ALL,
            'documento': ALL_WITH_RELATIONS,
        }

class AlertaResource(MyModelResource):
    documento = fields.ForeignKey(DocumentoResource, 'documento')

    class Meta:
        queryset = Alerta.objects.all()
        resource_name = 'alerta'
        filtering = {
            'texto': ALL,
            'documento': ALL_WITH_RELATIONS,
        }

from django.http import JsonResponse
from tastypie.resources import Resource
from .utils_qdrant import QdrantBOE
from .models_simplified import DocumentoSimplificado
from tastypie.authorization import Authorization

class BusquedaSemanticaResource(Resource):
    """
    Recurso para realizar búsquedas semánticas en documentos del BOE utilizando Qdrant.
    Permite a las IAs y otros sistemas realizar búsquedas por similitud conceptual.
    """
    class Meta:
        resource_name = 'busqueda_semantica'
        allowed_methods = ['get']
        authorization = Authorization()
        
    def obj_get_list(self, bundle, **kwargs):
        # Este método no se utiliza pero debe implementarse
        return []
        
    def get_list(self, request, **kwargs):
        # Obtener parámetros de búsqueda
        query = request.GET.get('q', '')
        departamento = request.GET.get('departamento', '')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        limite = request.GET.get('limite', '10')
        umbral = request.GET.get('umbral', '0.3')
        
        # Validar parámetros
        try:
            limite = int(limite)
            if limite < 1 or limite > 100:
                limite = 10
        except ValueError:
            limite = 10
            
        try:
            umbral = float(umbral)
            if umbral < 0 or umbral > 1:
                umbral = 0.3
        except ValueError:
            umbral = 0.3
            
        # Verificar que hay una consulta
        if not query:
            return self.create_response(request, {
                'success': False,
                'error': 'Se requiere un término de búsqueda (parámetro q)'
            })
            
        # Preparar filtros para Qdrant
        filtros = {}
        if departamento:
            filtros['departamento'] = departamento
        
        if fecha_desde:
            try:
                filtros['fecha_desde'] = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                filtros['fecha_hasta'] = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Realizar búsqueda semántica
        try:
            qdrant_client = QdrantBOE()
            resultados_qdrant = qdrant_client.buscar_similares(
                query, 
                limit=limite, 
                score_threshold=umbral, 
                filtros=filtros
            )
            
            # Formatear resultados
            documentos = []
            for resultado in resultados_qdrant:
                # Obtener documento completo de la base de datos
                try:
                    doc_id = resultado.get('identificador')
                    doc = DocumentoSimplificado.objects.get(identificador=doc_id)
                    
                    # Crear objeto de documento con los datos relevantes
                    documento = {
                        'identificador': doc.identificador,
                        'titulo': doc.titulo,
                        'fecha_publicacion': doc.fecha_publicacion.strftime('%Y-%m-%d'),
                        'departamento': doc.departamento,
                        'materias': doc.materias,
                        'url_pdf': doc.url_pdf,
                        'url_xml': doc.url_xml,
                        'score': resultado.get('score', 0),  # Puntuación de similitud
                    }
                    documentos.append(documento)
                except DocumentoSimplificado.DoesNotExist:
                    # Si el documento no existe en la base de datos, usar solo los datos de Qdrant
                    documentos.append(resultado)
            
            return self.create_response(request, {
                'success': True,
                'query': query,
                'total': len(documentos),
                'resultados': documentos
            })
            
        except Exception as e:
            return self.create_response(request, {
                'success': False,
                'error': f'Error al realizar la búsqueda semántica: {str(e)}'
            })
