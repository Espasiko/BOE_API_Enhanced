# -*- coding: utf-8 -*-
from django.db import models
import datetime

# Create your models here.
class GetOrNoneManager(models.Manager):
    """Adds get_or_none method to objects
    """
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None


class CodigoTitulo(models.Model):
    codigo = models.CharField(max_length=10)
    titulo = models.CharField(max_length=4000, null=True)

    class Meta:
        abstract = True
        unique_together = (('codigo', 'titulo'),)

class Diario(models.Model):
    nombre = models.CharField(max_length=50)
    def __str__(self):
        return self.nombre

class Departamento(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre

class Materia(models.Model):
    titulo = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self):
        return self.titulo

class Rango(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre

class Partido(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre

class Legislatura(models.Model):
    presidente = models.CharField(max_length=200)
    inicio = models.DateField()
    fin = models.DateField(null=True, blank=True)
    partido = models.ForeignKey(Partido, on_delete=models.SET_NULL, null=True)
    def __str__(self):
        return f"{self.presidente} ({self.inicio.year}-{self.fin.year if self.fin else 'actualidad'})"

class Estado_consolidacion(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre

class Origen_legislativo(models.Model):
    nombre = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre

class Documento(models.Model):
    identificador = models.CharField(max_length=20)
    diario = models.ForeignKey(Diario, on_delete=models.SET_NULL, null=True, related_name='diarios_documento')
    fecha_publicacion = models.DateField()
    fecha_disposicion = models.DateField(null=True, blank=True)
    titulo = models.TextField()
    texto = models.TextField(null=True, blank=True)
    url_pdf = models.URLField(max_length=500, null=True, blank=True)
    url_xml = models.URLField(max_length=500, null=True, blank=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, related_name='departamentos_documento')
    rango = models.ForeignKey(Rango, on_delete=models.SET_NULL, null=True, related_name='rangos_documento')
    estado_consolidacion = models.ForeignKey(Estado_consolidacion, on_delete=models.SET_NULL, null=True, related_name='estados_consolidacion_documento')
    origen_legislativo = models.ForeignKey(Origen_legislativo, on_delete=models.SET_NULL, null=True, related_name='origenes_legislativos_documento')
    materias = models.ManyToManyField(Materia, blank=True, related_name='materias_documento')
    legislatura = models.ForeignKey(Legislatura, on_delete=models.SET_NULL, null=True, related_name='legislaturas_documento')
    seccion = models.CharField(max_length=10, null=True, blank=True)
    numero = models.CharField(max_length=10, null=True, blank=True)
    pagina_inicial = models.IntegerField(null=True, blank=True)
    pagina_final = models.IntegerField(null=True, blank=True)
    vigencia_agotada = models.BooleanField(null=True, blank=True)
    judicialmente_anulada = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.identificador} - {self.titulo[:100]}"

    class Meta:
        ordering = ['-fecha_publicacion']

class Nota(models.Model):
    texto = models.TextField()
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='notas_documento')
    def __str__(self):
        return self.texto[:100]

class Alerta(models.Model):
    texto = models.TextField()
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='alertas_documento')
    def __str__(self):
        return self.texto[:100]

class Palabra(models.Model):
    texto = models.CharField(max_length=200)
    def __str__(self):
        return self.texto

class Referencia(models.Model):
    referencia = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='referencias_entrantes_documento')
    palabra = models.ForeignKey(Palabra, on_delete=models.CASCADE)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='referencias_salientes_documento')
    def __str__(self):
        return f"{self.documento.identificador} -> {self.referencia.identificador}"

class Modalidad(CodigoTitulo):
    class Meta:
        ordering = ['codigo']

class Tipo(CodigoTitulo):
    class Meta:
        ordering = ['codigo']

class Tramitacion(CodigoTitulo):
    class Meta:
        ordering = ['codigo']

class Procedimiento(CodigoTitulo):
    class Meta:
        ordering = ['codigo']

class Precio(CodigoTitulo):
    class Meta:
        ordering = ['codigo']

class DocumentoAnuncio(Documento):
    modalidad = models.ForeignKey(Modalidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='modalidades_documento')
    tipo = models.ForeignKey(Tipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='tipos_documento')
    tramitacion = models.ForeignKey(Tramitacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='tramitaciones_documento')
    fecha_presentacion_ofertas = models.CharField(max_length=4000, null=True, blank=True)
    fecha_apertura_ofertas = models.CharField(max_length=4000, null=True, blank=True)
    precio = models.ForeignKey(Precio, on_delete=models.SET_NULL, null=True, blank=True, related_name='precios_documento')
    importe = models.DecimalField(decimal_places=2, max_digits=1000, null=True, blank=True)
    ambito_geografico = models.CharField(max_length=4000, null=True, blank=True)
    materias_anuncio = models.CharField(max_length=4000, null=True, blank=True)
    materias_cpv = models.CharField(max_length=4000, null=True, blank=True)
    observaciones = models.CharField(max_length=4000, null=True, blank=True)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
