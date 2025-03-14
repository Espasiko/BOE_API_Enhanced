from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from boe_analisis.models import DocumentoSimplificado
from boe_analisis.models_alertas import AlertaUsuario, NotificacionAlerta
import re
import logging
from datetime import timedelta

# Configurar logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Procesa las alertas de usuarios y genera notificaciones para documentos relevantes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=1,
            help='Número de días hacia atrás para buscar documentos (por defecto: 1)'
        )
        parser.add_argument(
            '--enviar-email',
            action='store_true',
            help='Enviar notificaciones por email a los usuarios'
        )
        parser.add_argument(
            '--alerta-id',
            type=int,
            help='ID de una alerta específica para procesar'
        )
        parser.add_argument(
            '--usuario-id',
            type=int,
            help='ID de un usuario específico para procesar sus alertas'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        enviar_email = options['enviar_email']
        alerta_id = options['alerta_id']
        usuario_id = options['usuario_id']
        
        # Fecha de inicio para la búsqueda de documentos
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
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
            f'Procesando {documentos.count()} documentos publicados desde {fecha_inicio.strftime("%d/%m/%Y")}'
        ))
        
        # Filtrar alertas según los parámetros
        alertas = AlertaUsuario.objects.filter(activa=True)
        
        if alerta_id:
            alertas = alertas.filter(id=alerta_id)
            if not alertas:
                self.stdout.write(self.style.ERROR(f'No se encontró la alerta con ID {alerta_id}'))
                return
        
        if usuario_id:
            alertas = alertas.filter(usuario_id=usuario_id)
            if not alertas:
                self.stdout.write(self.style.ERROR(f'No se encontraron alertas activas para el usuario con ID {usuario_id}'))
                return
        
        if not alertas:
            self.stdout.write(self.style.WARNING('No hay alertas activas para procesar'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Procesando {alertas.count()} alertas activas'))
        
        # Contador de notificaciones creadas
        notificaciones_creadas = 0
        emails_enviados = 0
        
        # Procesar cada alerta
        for alerta in alertas:
            self.stdout.write(f'Procesando alerta: {alerta.nombre} (Usuario: {alerta.usuario.username})')
            
            # Obtener palabras clave de la alerta
            palabras_clave = [palabra.strip().lower() for palabra in alerta.palabras_clave.split(',') if palabra.strip()]
            
            if not palabras_clave:
                self.stdout.write(self.style.WARNING(f'  La alerta {alerta.id} no tiene palabras clave definidas'))
                continue
            
            # Filtrar documentos por departamentos si están especificados
            docs_filtrados = documentos
            if alerta.departamentos:
                departamentos = [dep.strip().lower() for dep in alerta.departamentos.split(',') if dep.strip()]
                if departamentos:
                    # Crear filtro OR para departamentos
                    q_departamentos = Q()
                    for dep in departamentos:
                        q_departamentos |= Q(departamento__icontains=dep)
                    
                    docs_filtrados = docs_filtrados.filter(q_departamentos)
            
            # Buscar coincidencias en los documentos filtrados
            for documento in docs_filtrados:
                # Verificar si ya existe una notificación para esta alerta y documento
                if NotificacionAlerta.objects.filter(alerta=alerta, documento=documento.identificador).exists():
                    continue
                
                # Calcular relevancia basada en coincidencias de palabras clave
                texto_completo = (
                    f"{documento.titulo.lower()} {documento.texto.lower()} "
                    f"{documento.departamento.lower()} {documento.rango.lower()} "
                    f"{documento.materias.lower()}"
                )
                
                coincidencias = 0
                for palabra in palabras_clave:
                    # Usar expresión regular para encontrar palabras completas
                    patron = r'\b' + re.escape(palabra) + r'\b'
                    if re.search(patron, texto_completo):
                        coincidencias += len(re.findall(patron, texto_completo))
                
                # Calcular un valor de relevancia entre 0 y 1
                relevancia = min(1.0, coincidencias / (len(palabras_clave) * 2))
                
                # Si la relevancia supera el umbral, crear notificación
                if relevancia >= alerta.umbral_relevancia:
                    # Crear la notificación
                    notificacion = NotificacionAlerta.objects.create(
                        alerta=alerta,
                        documento=documento.identificador,
                        titulo_documento=documento.titulo,
                        url_documento=f"https://www.boe.es/diario_boe/txt.php?id={documento.identificador}",
                        relevancia=relevancia * 100,  # Guardar como porcentaje
                        fecha_creacion=timezone.now(),
                        estado='pendiente'
                    )
                    
                    notificaciones_creadas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  Notificación creada: {documento.identificador} - Relevancia: {relevancia:.2f}'
                    ))
                    
                    # Enviar email si está habilitado y el usuario tiene habilitadas las notificaciones por email
                    if enviar_email and alerta.usuario.perfil.recibir_alertas_email:
                        try:
                            self._enviar_email_notificacion(notificacion)
                            emails_enviados += 1
                        except Exception as e:
                            logger.error(f"Error al enviar email: {str(e)}")
                            self.stdout.write(self.style.ERROR(f'  Error al enviar email: {str(e)}'))
        
        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS(
            f'Proceso completado: {notificaciones_creadas} notificaciones creadas'
        ))
        
        if enviar_email:
            self.stdout.write(self.style.SUCCESS(
                f'Emails enviados: {emails_enviados}'
            ))
    
    def _enviar_email_notificacion(self, notificacion):
        """Envía un email de notificación al usuario"""
        usuario = notificacion.alerta.usuario
        documento_id = notificacion.documento
        
        # Preparar el contexto para la plantilla
        context = {
            'usuario': usuario,
            'alerta': notificacion.alerta,
            'notificacion': notificacion,
            'url_documento': notificacion.url_documento,
        }
        
        # Renderizar el contenido del email
        html_message = render_to_string('boe_analisis/emails/notificacion_alerta.html', context)
        plain_message = render_to_string('boe_analisis/emails/notificacion_alerta_texto.html', context)
        
        # Enviar el email
        send_mail(
            subject=f'BOE Alertas - Nuevo documento relevante: {documento_id}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Registrar en el log
        logger.info(f"Email enviado a {usuario.email} para la notificación {notificacion.id}")
