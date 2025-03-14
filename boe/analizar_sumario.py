import os
import sys
import django
import xml.etree.ElementTree as ET
from datetime import datetime

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boe.settings')
django.setup()

from boe_analisis.utils_boe import obtener_sumario_boe

def analizar_sumario(fecha_str):
    print(f"Analizando sumario del BOE para la fecha: {fecha_str}")
    
    # Convertir la cadena de fecha en un objeto datetime.date
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    # Obtener el sumario
    sumario_xml = obtener_sumario_boe(fecha)
    
    if not sumario_xml:
        print("No se pudo obtener el sumario")
        return
    
    # Guardar el XML en un archivo para análisis
    with open('sumario.xml', 'w', encoding='utf-8') as f:
        f.write(sumario_xml)
    
    print(f"Sumario guardado en 'sumario.xml'")
    
    # Parsear el XML
    try:
        root = ET.fromstring(sumario_xml)
        print(f"Etiqueta raíz: {root.tag}")
        
        # Mostrar los primeros niveles de la estructura
        print("\nPrimeros hijos de la raíz:")
        for i, child in enumerate(root):
            if i < 5:  # Limitar a los primeros 5 para no saturar la salida
                print(f"  - {child.tag}")
        
        # Buscar elementos 'item' o similares que puedan contener documentos
        print("\nBuscando elementos de tipo 'item'...")
        items = root.findall('.//item')
        if items:
            print(f"Se encontraron {len(items)} elementos 'item'")
            
            # Analizar el primer item para ver su estructura
            print("\nEstructura del primer item:")
            for elem in items[0]:
                print(f"  - {elem.tag}: {elem.text if elem.text else '[vacío]'}")
        else:
            print("No se encontraron elementos 'item'")
            
            # Intentar encontrar otros elementos que puedan contener documentos
            print("\nBuscando otros elementos que puedan contener documentos...")
            for tag in ['documento', 'doc', 'diario', 'seccion', 'departamento']:
                elements = root.findall(f'.//{tag}')
                if elements:
                    print(f"Se encontraron {len(elements)} elementos '{tag}'")
                    
                    # Mostrar la estructura del primer elemento
                    print(f"\nEstructura del primer elemento '{tag}':")
                    for elem in elements[0]:
                        print(f"  - {elem.tag}: {elem.text if elem.text else '[vacío]'}")
                    break
        
    except ET.ParseError as e:
        print(f"Error al parsear el XML: {str(e)}")

if __name__ == "__main__":
    fecha = "2025-03-10"
    analizar_sumario(fecha)
