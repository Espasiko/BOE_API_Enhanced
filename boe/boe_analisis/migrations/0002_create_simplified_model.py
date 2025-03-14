from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('boe_analisis', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentoSimplificado',
            fields=[
                ('identificador', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('fecha_publicacion', models.DateField()),
                ('titulo', models.TextField()),
                ('texto', models.TextField(blank=True, null=True)),
                ('url_pdf', models.URLField(blank=True, max_length=500, null=True)),
                ('url_xml', models.URLField(blank=True, max_length=500, null=True)),
                ('vigente', models.BooleanField(default=True)),
                ('departamento', models.CharField(blank=True, max_length=200, null=True)),
                ('materias', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Documento Simplificado',
                'verbose_name_plural': 'Documentos Simplificados',
                'ordering': ['-fecha_publicacion'],
            },
        ),
    ]
