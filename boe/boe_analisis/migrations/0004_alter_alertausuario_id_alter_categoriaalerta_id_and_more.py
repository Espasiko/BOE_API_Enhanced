# Generated by Django 5.1.7 on 2025-03-08 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boe_analisis', '0003_create_alertas_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alertausuario',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='categoriaalerta',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='notificacionalerta',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='perfilusuario',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterModelTable(
            name='documentosimplificado',
            table='boe_analisis_documentosimplificado',
        ),
    ]
