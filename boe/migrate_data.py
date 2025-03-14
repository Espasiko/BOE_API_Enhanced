#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import sys

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar los modelos
from boe_analisis.models import Documento as OldDocumento
from boe_analisis.models_simplified import DocumentoSimplificado as NewDocumento

def migrate_documents():
    """Migra los documentos del modelo antiguo al nuevo modelo simplificado"""
    print("Iniciando migración de documentos...")
    
    # Obtener todos los documentos del modelo antiguo
    old_documents = OldDocumento.objects.all()
    count = old_documents.count()
    print(f"Se encontraron {count} documentos para migrar")
    
    # Migrar cada documento
    migrated = 0
    for old_doc in old_documents:
        try:
            # Crear el nuevo documento con los campos simplificados
            new_doc = NewDocumento(
                identificador=old_doc.identificador,
                fecha_publicacion=old_doc.fecha_publicacion,
                titulo=old_doc.titulo,
                texto=old_doc.texto,
                url_pdf=old_doc.url_pdf,
                url_xml=old_doc.url_xml,
                vigente=not (old_doc.vigencia_agotada or False if old_doc.vigencia_agotada is None else old_doc.vigencia_agotada),
                departamento=old_doc.departamento.nombre if old_doc.departamento else None,
                materias=", ".join([m.titulo for m in old_doc.materias.all()]) if old_doc.materias.exists() else None
            )
            
            # Verificar si el documento ya existe en la base de datos simplificada
            if not NewDocumento.objects.filter(identificador=old_doc.identificador).exists():
                new_doc.save()
                migrated += 1
                
                if migrated % 100 == 0:
                    print(f"Migrados {migrated} de {count} documentos")
            else:
                print(f"El documento {old_doc.identificador} ya existe en la base de datos simplificada")
                
        except Exception as e:
            print(f"Error migrando documento {old_doc.identificador}: {str(e)}")
    
    print(f"Migración completada. Se migraron {migrated} de {count} documentos")

if __name__ == "__main__":
    migrate_documents()
