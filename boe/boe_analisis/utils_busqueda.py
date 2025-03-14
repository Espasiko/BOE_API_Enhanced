"""
Utilidades para mejorar la búsqueda de documentos
"""
import re
from django.db.models import Q
import Levenshtein

def normalizar_texto(texto):
    """
    Normaliza el texto para búsquedas: elimina acentos, convierte a minúsculas, etc.
    
    Args:
        texto (str): Texto a normalizar
        
    Returns:
        str: Texto normalizado
    """
    if not texto:
        return ""
    
    # Convertir a minúsculas
    texto = texto.lower()
    
    # Reemplazar caracteres acentuados
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
        'ñ': 'n'
    }
    
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    
    # Eliminar caracteres especiales
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto

def busqueda_tolerante(queryset, campo, texto):
    """
    Realiza una búsqueda tolerante a errores usando la distancia de Levenshtein
    
    Args:
        queryset: QuerySet de Django a filtrar
        campo (str): Nombre del campo donde buscar
        texto (str): Texto a buscar
        
    Returns:
        QuerySet: Resultados filtrados
    """
    if not texto:
        return queryset
    
    # Normalizar el texto de búsqueda
    texto_normalizado = normalizar_texto(texto)
    
    # Primero intentamos una búsqueda exacta (más rápida)
    resultados_exactos = queryset.filter(**{f"{campo}__icontains": texto})
    
    if resultados_exactos.exists():
        return resultados_exactos
    
    # Si no hay resultados exactos, hacemos una búsqueda por palabras
    # Dividimos el texto en palabras
    palabras = texto_normalizado.split()
    
    # Creamos una consulta que busque documentos que contengan al menos una de las palabras
    consulta = Q()
    for palabra in palabras:
        if len(palabra) > 2:  # Solo consideramos palabras con más de 2 caracteres
            consulta |= Q(**{f"{campo}__icontains": palabra})
    
    # Ejecutamos la consulta
    resultados = queryset.filter(consulta)
    
    # Si aún no hay resultados, usamos Levenshtein para búsqueda aproximada
    if not resultados.exists() and len(texto_normalizado) > 3:
        # Obtener todos los documentos para comparación (esto puede ser costoso en bases de datos grandes)
        # En una base de datos grande, deberías limitar esto a un subconjunto relevante
        todos_documentos = queryset.all()
        ids_similares = []
        
        # Umbral de similitud (ajustar según necesidad)
        umbral_similitud = 0.7
        
        for doc in todos_documentos:
            # Obtener el valor del campo para comparar
            valor_campo = getattr(doc, campo, '')
            if valor_campo:
                # Normalizar para comparación
                valor_normalizado = normalizar_texto(valor_campo)
                
                # Calcular ratio de similitud con Levenshtein
                similitud = Levenshtein.ratio(texto_normalizado, valor_normalizado)
                
                # También probar con cada palabra individual
                for palabra in palabras:
                    if len(palabra) > 3:  # Solo palabras significativas
                        # Buscar la palabra en el texto completo
                        if palabra in valor_normalizado:
                            similitud = max(similitud, 0.8)  # Dar alta similitud si contiene la palabra
                        else:
                            # Buscar palabras similares
                            for palabra_doc in valor_normalizado.split():
                                if len(palabra_doc) > 3:
                                    sim_palabra = Levenshtein.ratio(palabra, palabra_doc)
                                    similitud = max(similitud, sim_palabra)
                
                # Si la similitud supera el umbral, incluir en resultados
                if similitud >= umbral_similitud:
                    ids_similares.append(doc.pk)
        
        # Filtrar el queryset original con los IDs encontrados
        if ids_similares:
            # Usar __in para filtrar por múltiples IDs
            resultados = queryset.filter(pk__in=ids_similares)
    
    return resultados

def busqueda_multiple_campos(queryset, campos, texto):
    """
    Realiza una búsqueda en múltiples campos
    
    Args:
        queryset: QuerySet de Django a filtrar
        campos (list): Lista de nombres de campos donde buscar
        texto (str): Texto a buscar
        
    Returns:
        QuerySet: Resultados filtrados
    """
    if not texto or not campos:
        return queryset
    
    # Normalizar el texto de búsqueda
    texto_normalizado = normalizar_texto(texto)
    palabras = texto_normalizado.split()
    
    # Primero intentamos una búsqueda exacta (más rápida)
    consulta_exacta = Q()
    for campo in campos:
        consulta_exacta |= Q(**{f"{campo}__icontains": texto})
    
    resultados_exactos = queryset.filter(consulta_exacta)
    
    if resultados_exactos.exists():
        return resultados_exactos
    
    # Si no hay resultados exactos, buscamos por palabras individuales
    consulta = Q()
    for palabra in palabras:
        if len(palabra) > 2:  # Solo consideramos palabras con más de 2 caracteres
            for campo in campos:
                consulta |= Q(**{f"{campo}__icontains": palabra})
    
    resultados = queryset.filter(consulta)
    
    # Si aún no hay resultados, usar Levenshtein para cada campo
    if not resultados.exists() and len(texto_normalizado) > 3:
        ids_similares = set()
        
        for campo in campos:
            # Usar la función de búsqueda tolerante para cada campo
            resultados_campo = busqueda_tolerante(queryset, campo, texto)
            for doc in resultados_campo:
                ids_similares.add(doc.pk)
        
        if ids_similares:
            resultados = queryset.filter(pk__in=ids_similares)
    
    return resultados
