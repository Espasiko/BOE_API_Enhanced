from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from boe_analisis.models_simplified import DocumentoSimplificado
from boe_analisis.models_alertas import AlertaUsuario, NotificacionAlerta, CategoriaAlerta
import re
import logging
from datetime import timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        parser.add_argument(
            '--categorias',
            action='store_true',
            help='Incluir coincidencias por categorías de alertas'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        enviar_email = options['enviar_email']
        alerta_id = options['alerta_id']
        usuario_id = options['usuario_id']
        usar_categorias = options['categorias']
        
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
        
        # Cargar categorías si se van a usar
        categorias_dict = {}
        if usar_categorias:
            for categoria in CategoriaAlerta.objects.all():
                if categoria.palabras_clave:
                    palabras = [p.strip().lower() for p in categoria.palabras_clave.split(',') if p.strip()]
                    categorias_dict[categoria.id] = palabras
            
            self.stdout.write(self.style.SUCCESS(f'Cargadas {len(categorias_dict)} categorías con palabras clave'))
        
        # Contador de notificaciones creadas
        notificaciones_creadas = 0
        emails_enviados = 0
        
        # Procesar cada alerta
        for alerta in alertas:
            self.stdout.write(f'Procesando alerta: {alerta.nombre} (Usuario: {alerta.usuario.username})')
            
            # Obtener palabras clave de la alerta
            palabras_clave = [palabra.strip().lower() for palabra in alerta.palabras_clave.split(',') if palabra.strip()]
            
            # Añadir palabras clave de las categorías asociadas a la alerta
            if usar_categorias:
                for categoria in alerta.categorias.all():
                    if categoria.id in categorias_dict:
                        palabras_clave.extend(categorias_dict[categoria.id])
                
                # Eliminar duplicados
                palabras_clave = list(set(palabras_clave))
            
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
                        # También buscar por código de departamento si es un número
                        if dep.isdigit():
                            q_departamentos |= Q(codigo_departamento=dep)
                    
                    docs_filtrados = docs_filtrados.filter(q_departamentos)
            
            # Buscar coincidencias en los documentos filtrados
            for documento in docs_filtrados:
                # Verificar si ya existe una notificación para esta alerta y documento
                if NotificacionAlerta.objects.filter(alerta=alerta, documento=documento.identificador).exists():
                    continue
                
                # Preparar el texto completo para buscar coincidencias
                texto_completo = self._preparar_texto_documento(documento)
                
                # Calcular relevancia basada en coincidencias de palabras clave
                coincidencias, palabras_encontradas = self._calcular_coincidencias(texto_completo, palabras_clave)
                
                # Si no hay coincidencias, pasar al siguiente documento
                if not coincidencias:
                    continue
                
                # Calcular relevancia
                relevancia = self._calcular_relevancia(coincidencias, palabras_encontradas, palabras_clave)
                
                # Si la relevancia supera el umbral, crear notificación
                if relevancia >= alerta.umbral_relevancia:
                    # Crear la notificación
                    notificacion = self._crear_notificacion(alerta, documento, relevancia, palabras_encontradas)
                    
                    notificaciones_creadas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  Notificación creada: {documento.identificador} - Relevancia: {relevancia:.2f}'
                    ))
                    
                    # Enviar email si está habilitado y el usuario tiene habilitadas las notificaciones por email
                    if enviar_email and hasattr(alerta.usuario, 'perfil') and alerta.usuario.perfil.recibir_alertas_email:
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
    
    def _preparar_texto_documento(self, documento):
        """
        Prepara el texto completo del documento para buscar coincidencias
        """
        texto_completo = f"{documento.titulo.lower()} "
        
        if documento.texto:
            texto_completo += f"{documento.texto.lower()} "
        
        if documento.departamento:
            texto_completo += f"{documento.departamento.lower()} "
        
        if documento.materias:
            texto_completo += f"{documento.materias.lower()} "
        
        if documento.palabras_clave:
            texto_completo += f"{documento.palabras_clave.lower()} "
            
        return texto_completo
    
    def _calcular_coincidencias(self, texto_completo, palabras_clave):
        """
        Calcula las coincidencias de palabras clave en el texto
        """
        coincidencias = 0
        palabras_encontradas = set()
        
        for palabra in palabras_clave:
            if len(palabra) < 3:  # Ignorar palabras muy cortas
                continue
                
            # Usar expresión regular para encontrar palabras completas
            patron = r'\b' + re.escape(palabra) + r'\b'
            if re.search(patron, texto_completo):
                num_coincidencias = len(re.findall(patron, texto_completo))
                coincidencias += num_coincidencias
                palabras_encontradas.add(palabra)
                
        return coincidencias, palabras_encontradas
    
    def _calcular_relevancia(self, coincidencias, palabras_encontradas, palabras_clave):
        """
        Calcula la relevancia del documento para la alerta
        """
        # Fórmula mejorada: considera tanto el número de palabras clave distintas que coinciden
        # como el número total de coincidencias
        factor_palabras_distintas = len(palabras_encontradas) / len(palabras_clave)
        factor_frecuencia = min(1.0, coincidencias / (len(palabras_clave) * 3))
        
        # Combinar ambos factores (70% importancia a palabras distintas, 30% a frecuencia)
        relevancia = (factor_palabras_distintas * 0.7) + (factor_frecuencia * 0.3)
        
        return relevancia
    
    def _crear_notificacion(self, alerta, documento, relevancia, palabras_encontradas):
        """
        Crea una notificación para la alerta y el documento
        """
        return NotificacionAlerta.objects.create(
            alerta=alerta,
            documento=documento.identificador,
            titulo_documento=documento.titulo,
            fecha_documento=documento.fecha_publicacion,
            relevancia=relevancia,
            estado='pendiente',
            resumen=f"Palabras clave encontradas: {', '.join(palabras_encontradas)}"
        )
    
    def _enviar_email_notificacion(self, notificacion):
        """Envía un email de notificación al usuario"""
        usuario = notificacion.alerta.usuario
        documento_id = notificacion.documento
        
        # Construir URL del documento
        url_documento = f"https://www.boe.es/diario_boe/txt.php?id={documento_id}"
        
        # Preparar el contexto para la plantilla
        context = {
            'usuario': usuario,
            'alerta': notificacion.alerta,
            'notificacion': notificacion,
            'url_documento': url_documento,
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
