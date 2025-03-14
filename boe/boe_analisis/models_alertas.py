# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
import datetime

class PerfilUsuario(models.Model):
    """
    Perfil extendido del usuario con información adicional
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    organizacion = models.CharField(max_length=100, blank=True, null=True)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    recibir_alertas_email = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

class CategoriaAlerta(models.Model):
    """
    Categorías predefinidas para las alertas
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    palabras_clave = models.TextField(blank=True, null=True, help_text="Palabras clave separadas por comas")
    color = models.CharField(max_length=20, blank=True, null=True, help_text="Código de color en formato hexadecimal")
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = "Categoría de Alerta"
        verbose_name_plural = "Categorías de Alertas"

class AlertaUsuario(models.Model):
    """
    Configuración de alertas personalizadas por usuario
    """
    FRECUENCIA_CHOICES = [
        (1, 'Inmediata'),
        (7, 'Semanal'),
        (30, 'Mensual'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alertas')
    nombre = models.CharField(max_length=100)
    palabras_clave = models.TextField(help_text="Palabras clave separadas por comas")
    categorias = models.ManyToManyField(CategoriaAlerta, blank=True, related_name='alertas')
    departamentos = models.TextField(blank=True, null=True, help_text="Departamentos separados por comas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)
    frecuencia = models.IntegerField(choices=FRECUENCIA_CHOICES, default=1)
    umbral_relevancia = models.FloatField(default=0.5, help_text="Umbral mínimo de relevancia (0-1)")
    
    def __str__(self):
        return f"Alerta '{self.nombre}' de {self.usuario.username}"
    
    class Meta:
        verbose_name = "Alerta de Usuario"
        verbose_name_plural = "Alertas de Usuarios"

class NotificacionAlerta(models.Model):
    """
    Notificaciones generadas para los usuarios
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('leida', 'Leída'),
        ('archivada', 'Archivada'),
    ]
    
    alerta = models.ForeignKey(AlertaUsuario, on_delete=models.CASCADE, related_name='notificaciones')
    documento = models.CharField(max_length=20)  # Identificador del documento
    titulo_documento = models.TextField()
    fecha_documento = models.DateField()
    fecha_notificacion = models.DateTimeField(auto_now_add=True)
    relevancia = models.FloatField(default=0.0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    resumen = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Notificación para {self.alerta.usuario.username}: {self.titulo_documento[:50]}..."
    
    class Meta:
        verbose_name = "Notificación de Alerta"
        verbose_name_plural = "Notificaciones de Alertas"
        ordering = ['-fecha_notificacion']
