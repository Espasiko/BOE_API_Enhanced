#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import sys

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

# Importar el modelo simplificado
from boe_analisis.models_simplified import DocumentoSimplificado as Documento

def consultar_documentos():
    """
    Consulta los documentos almacenados en la base de datos simplificada
    """
    print("\n===== Consultando documentos en la base de datos simplificada =====")
    
    # Contar documentos
    total_documentos = Documento.objects.count()
    print(f"Total de documentos: {total_documentos}")
    
    # Mostrar los primeros 5 documentos
    if total_documentos > 0:
        print("\nPrimeros 5 documentos:")
        documentos = Documento.objects.all().order_by('-fecha_publicacion')[:5]
        
        for i, doc in enumerate(documentos, 1):
            print(f"\n{i}. {doc.identificador}")
            print(f"   Título: {doc.titulo[:100]}...")
            print(f"   Fecha: {doc.fecha_publicacion}")
            print(f"   Departamento: {doc.departamento or 'No especificado'}")
            print(f"   Materias: {doc.materias or 'No especificadas'}")
            print(f"   Vigente: {'Sí' if doc.vigente else 'No'}")
            print(f"   URL PDF: {doc.url_pdf or 'No disponible'}")
    else:
        print("No hay documentos en la base de datos.")

def buscar_por_texto(texto):
    """
    Busca documentos que contengan el texto especificado en el título
    """
    print(f"\n===== Buscando documentos que contengan '{texto}' =====")
    
    documentos = Documento.objects.filter(titulo__icontains=texto).order_by('-fecha_publicacion')
    total = documentos.count()
    
    print(f"Se encontraron {total} documentos")
    
    for i, doc in enumerate(documentos[:5], 1):
        print(f"\n{i}. {doc.identificador}")
        print(f"   Título: {doc.titulo[:100]}...")
        print(f"   Fecha: {doc.fecha_publicacion}")
    
    if total > 5:
        print(f"\n... y {total - 5} documentos más.")

def buscar_por_fecha(fecha):
    """
    Busca documentos publicados en la fecha especificada (formato: YYYY-MM-DD)
    """
    print(f"\n===== Buscando documentos publicados el {fecha} =====")
    
    documentos = Documento.objects.filter(fecha_publicacion=fecha).order_by('-fecha_publicacion')
    total = documentos.count()
    
    print(f"Se encontraron {total} documentos")
    
    for i, doc in enumerate(documentos[:5], 1):
        print(f"\n{i}. {doc.identificador}")
        print(f"   Título: {doc.titulo[:100]}...")
        print(f"   Departamento: {doc.departamento or 'No especificado'}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--texto" and len(sys.argv) > 2:
            buscar_por_texto(sys.argv[2])
        elif sys.argv[1] == "--fecha" and len(sys.argv) > 2:
            buscar_por_fecha(sys.argv[2])
        else:
            print("Uso: python consultar_db_simplified.py [--texto TEXTO | --fecha YYYY-MM-DD]")
    else:
        consultar_documentos()
