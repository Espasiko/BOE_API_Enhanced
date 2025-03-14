from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Count, Q

from boe_analisis.models_alertas import AlertaUsuario, NotificacionAlerta
import logging
from datetime import timedelta

# Configurar logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envía notificaciones programadas a los usuarios según la frecuencia configurada en sus alertas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar-envio',
            action='store_true',
            help='Forzar el envío de notificaciones independientemente de la frecuencia configurada'
        )
        parser.add_argument(
            '--usuario-id',
            type=int,
            help='ID de un usuario específico para enviar sus notificaciones'
        )

    def handle(self, *args, **options):
        forzar_envio = options['forzar_envio']
        usuario_id = options['usuario_id']
        
        # Fecha actual
        ahora = timezone.now()
        
        # Obtener alertas activas
        alertas = AlertaUsuario.objects.filter(activa=True)
        
        if usuario_id:
            alertas = alertas.filter(usuario_id=usuario_id)
            if not alertas:
                self.stdout.write(self.style.ERROR(f'No se encontraron alertas activas para el usuario con ID {usuario_id}'))
                return
        
        if not alertas:
            self.stdout.write(self.style.WARNING('No hay alertas activas para procesar'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Procesando {alertas.count()} alertas activas'))
        
        # Contador de emails enviados
        emails_enviados = 0
        
        # Procesar cada alerta
        for alerta in alertas:
            # Verificar si el usuario tiene habilitadas las notificaciones por email
            if not alerta.usuario.perfil.recibir_alertas_email:
                self.stdout.write(f'Usuario {alerta.usuario.username} no tiene habilitadas las notificaciones por email')
                continue
            
            # Verificar si hay notificaciones pendientes para esta alerta
            notificaciones = NotificacionAlerta.objects.filter(
                alerta=alerta,
                estado='pendiente'
            )
            
            if not notificaciones:
                self.stdout.write(f'No hay notificaciones pendientes para la alerta: {alerta.nombre}')
                continue
            
            # Verificar si es momento de enviar según la frecuencia configurada
            enviar = forzar_envio
            
            if not enviar:
                # Obtener la última notificación enviada para esta alerta
                ultima_enviada = NotificacionAlerta.objects.filter(
                    alerta=alerta,
                    fecha_envio__isnull=False
                ).order_by('-fecha_envio').first()
                
                if not ultima_enviada:
                    # Si nunca se ha enviado, enviar ahora
                    enviar = True
                else:
                    # Calcular si ha pasado el tiempo según la frecuencia
                    if alerta.frecuencia == 1:  # Inmediata
                        enviar = True
                    elif alerta.frecuencia == 7:  # Semanal
                        enviar = (ahora - ultima_enviada.fecha_envio) >= timedelta(days=7)
                    elif alerta.frecuencia == 30:  # Mensual
                        enviar = (ahora - ultima_enviada.fecha_envio) >= timedelta(days=30)
            
            if enviar:
                try:
                    # Enviar email con resumen de notificaciones
                    self._enviar_email_resumen(alerta, notificaciones, ahora)
                    
                    # Actualizar las notificaciones como enviadas
                    notificaciones.update(
                        fecha_envio=ahora
                    )
                    
                    emails_enviados += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'Email enviado para la alerta {alerta.nombre} con {notificaciones.count()} notificaciones'
                    ))
                except Exception as e:
                    logger.error(f"Error al enviar email para alerta {alerta.id}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'Error al enviar email: {str(e)}'))
        
        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS(
            f'Proceso completado: {emails_enviados} emails enviados'
        ))
    
    def _enviar_email_resumen(self, alerta, notificaciones, fecha_envio):
        """Envía un email con un resumen de las notificaciones pendientes"""
        usuario = alerta.usuario
        
        # Agrupar notificaciones por relevancia
        alta_relevancia = notificaciones.filter(relevancia__gte=75).order_by('-relevancia')
        media_relevancia = notificaciones.filter(relevancia__gte=50, relevancia__lt=75).order_by('-relevancia')
        baja_relevancia = notificaciones.filter(relevancia__lt=50).order_by('-relevancia')
        
        # Preparar el contexto para la plantilla
        context = {
            'usuario': usuario,
            'alerta': alerta,
            'notificaciones': notificaciones,
            'alta_relevancia': alta_relevancia,
            'media_relevancia': media_relevancia,
            'baja_relevancia': baja_relevancia,
            'fecha_envio': fecha_envio,
            'total_notificaciones': notificaciones.count(),
        }
        
        # Determinar el tipo de frecuencia para el asunto
        if alerta.frecuencia == 1:
            frecuencia_texto = "inmediata"
        elif alerta.frecuencia == 7:
            frecuencia_texto = "semanal"
        else:
            frecuencia_texto = "mensual"
        
        # Renderizar el contenido del email
        html_message = render_to_string('boe_analisis/emails/resumen_notificaciones.html', context)
        plain_message = render_to_string('boe_analisis/emails/resumen_notificaciones_texto.html', context)
        
        # Enviar el email
        send_mail(
            subject=f'BOE Alertas - Resumen {frecuencia_texto} de "{alerta.nombre}" ({notificaciones.count()} documentos)',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Registrar en el log
        logger.info(f"Email de resumen enviado a {usuario.email} para la alerta {alerta.id} con {notificaciones.count()} notificaciones")
