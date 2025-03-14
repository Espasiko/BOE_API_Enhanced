# -*- coding: utf-8 -*-
from django.db import models
import datetime

# Modelo simplificado para BOE_API
# Basado en el plan de simplificación acordado

class DocumentoSimplificado(models.Model):
    """
    Modelo simplificado de Documento que contiene solo los campos esenciales.
    Elimina las relaciones complejas y se centra en la información clave.
    """
    identificador = models.CharField(max_length=20, primary_key=True)
    fecha_publicacion = models.DateField()
    titulo = models.TextField()
    texto = models.TextField(null=True, blank=True)
    url_pdf = models.URLField(max_length=500, null=True, blank=True)
    url_xml = models.URLField(max_length=500, null=True, blank=True)
    
    # Campo para indicar si el documento está vigente
    vigente = models.BooleanField(default=True)
    
    # Campos opcionales que pueden ser útiles pero no esenciales
    departamento = models.CharField(max_length=200, null=True, blank=True)
    codigo_departamento = models.CharField(max_length=20, null=True, blank=True)  # Código numérico del departamento
    materias = models.TextField(null=True, blank=True)  # Almacenará materias como texto separado por comas
    palabras_clave = models.TextField(null=True, blank=True)  # Almacenará palabras clave como texto separado por comas
    
    def __str__(self):
        return f"{self.identificador} - {self.titulo[:100]}"

    class Meta:
        ordering = ['-fecha_publicacion']
        verbose_name = "Documento Simplificado"
        verbose_name_plural = "Documentos Simplificados"
        db_table = 'boe_analisis_documentosimplificado'  # Nombre de la tabla que coincide con la migración

# La tabla de alertas se implementará en una fase posterior
"""
class AlertaUsuario(models.Model):
    usuario_id = models.CharField(max_length=100)
    palabras_clave = models.TextField()  # Almacenará palabras clave separadas por comas
    materias = models.TextField(null=True, blank=True)  # Almacenará materias separadas por comas
    frecuencia_alertas = models.IntegerField(default=1)  # 1: Inmediato, 7: Semanal
    
    def __str__(self):
        return f"Alerta para {self.usuario_id}"
    
    class Meta:
        verbose_name = "Alerta de Usuario"
        verbose_name_plural = "Alertas de Usuarios"
"""
