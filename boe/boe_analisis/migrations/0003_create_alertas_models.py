from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('boe_analisis', '0002_create_simplified_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaAlerta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Categoría de Alerta',
                'verbose_name_plural': 'Categorías de Alertas',
            },
        ),
        migrations.CreateModel(
            name='PerfilUsuario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telefono', models.CharField(blank=True, max_length=15, null=True)),
                ('organizacion', models.CharField(blank=True, max_length=100, null=True)),
                ('cargo', models.CharField(blank=True, max_length=100, null=True)),
                ('sector', models.CharField(blank=True, max_length=100, null=True)),
                ('recibir_alertas_email', models.BooleanField(default=True)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Perfil de Usuario',
                'verbose_name_plural': 'Perfiles de Usuarios',
            },
        ),
        migrations.CreateModel(
            name='AlertaUsuario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('palabras_clave', models.TextField(help_text='Palabras clave separadas por comas')),
                ('departamentos', models.TextField(blank=True, help_text='Departamentos separados por comas', null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('activa', models.BooleanField(default=True)),
                ('frecuencia', models.IntegerField(choices=[(1, 'Inmediata'), (7, 'Semanal'), (30, 'Mensual')], default=1)),
                ('umbral_relevancia', models.FloatField(default=0.5, help_text='Umbral mínimo de relevancia (0-1)')),
                ('categorias', models.ManyToManyField(blank=True, related_name='alertas', to='boe_analisis.CategoriaAlerta')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Alerta de Usuario',
                'verbose_name_plural': 'Alertas de Usuarios',
            },
        ),
        migrations.CreateModel(
            name='NotificacionAlerta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('documento', models.CharField(max_length=20)),
                ('titulo_documento', models.TextField()),
                ('fecha_documento', models.DateField()),
                ('fecha_notificacion', models.DateTimeField(auto_now_add=True)),
                ('relevancia', models.FloatField(default=0.0)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('enviada', 'Enviada'), ('leida', 'Leída'), ('archivada', 'Archivada')], default='pendiente', max_length=20)),
                ('resumen', models.TextField(blank=True, null=True)),
                ('alerta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='boe_analisis.AlertaUsuario')),
            ],
            options={
                'verbose_name': 'Notificación de Alerta',
                'verbose_name_plural': 'Notificaciones de Alertas',
                'ordering': ['-fecha_notificacion'],
            },
        ),
    ]
