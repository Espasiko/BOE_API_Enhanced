import requests
import logging
from datetime import datetime
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def probar_url(url, headers, descripcion):
    """Prueba una URL específica y muestra los resultados"""
    try:
        logging.info(f"\n\n===== Probando {descripcion} =====")
        logging.info(f"URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        
        logging.info(f"Código de estado: {response.status_code}")
        logging.info(f"Tipo de contenido: {response.headers.get('Content-Type', 'No especificado')}")
        
        if response.status_code == 200:
            # Verificar si es XML o HTML
            if response.text.strip().startswith('<!DOCTYPE html>'):
                logging.warning("La respuesta es HTML, no XML")
                logging.info(f"Primeros 300 caracteres: {response.text[:300]}")
                return False, None
            elif '<sumario>' in response.text or '<documento>' in response.text:
                logging.info("¡ÉXITO! La respuesta parece ser XML válido")
                logging.info(f"Primeros 300 caracteres: {response.text[:300]}")
                return True, response.text
            else:
                logging.warning("La respuesta no parece contener XML de BOE válido")
                logging.info(f"Primeros 300 caracteres: {response.text[:300]}")
                return False, None
        else:
            logging.error(f"Error HTTP {response.status_code}")
            logging.info(f"Primeros 300 caracteres: {response.text[:300]}")
            return False, None
    except Exception as e:
        logging.error(f"Error en la petición: {str(e)}")
        return False, None

def test_boe_connection():
    # Fecha específica en formato YYYYMMDD
    fecha = "20250307"  # 7 de marzo de 2025
    
    # Headers para todas las peticiones
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/xml, text/xml',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # Lista de URLs a probar
    urls = [
        {
            "url": f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}",
            "descripcion": "API de datos abiertos"
        },
        {
            "url": f"https://www.boe.es/boe/dias/{fecha[:4]}/{fecha[4:6]}/{fecha[6:]}/index.xml",
            "descripcion": "Formato con días"
        },
        {
            "url": f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{fecha}",
            "descripcion": "Formato con PHP"
        },
        {
            "url": f"https://boe.es/diario_boe/xml.php?id=BOE-S-{fecha}",
            "descripcion": "Formato sin www"
        },
        {
            "url": f"https://www.boe.es/api/boe/sumario/{fecha}",
            "descripcion": "API directa"
        },
        {
            "url": f"https://boe.es/api/boe/sumario/{fecha}",
            "descripcion": "API directa sin www"
        },
        {
            "url": f"https://www.boe.es/diario_boe/sumario.php?fecha={fecha[:4]}/{fecha[4:6]}/{fecha[6:]}&pub=BOE",
            "descripcion": "Sumario PHP con fecha formateada"
        }
    ]
    
    # Probar cada URL
    resultados_exitosos = []
    
    for url_info in urls:
        exito, contenido = probar_url(url_info["url"], headers, url_info["descripcion"])
        if exito and contenido:
            resultados_exitosos.append({
                "url": url_info["url"],
                "descripcion": url_info["descripcion"],
                "contenido": contenido
            })
    
    # Mostrar resumen de resultados
    logging.info("\n\n===== RESUMEN DE RESULTADOS =====")
    if resultados_exitosos:
        logging.info(f"Se encontraron {len(resultados_exitosos)} URLs que funcionan correctamente:")
        for i, resultado in enumerate(resultados_exitosos, 1):
            logging.info(f"{i}. {resultado['descripcion']}: {resultado['url']}")
            
            # Guardar el primer resultado exitoso
            if i == 1:
                archivo = f"sumario_boe_{fecha}.xml"
                with open(archivo, "w", encoding="utf-8") as f:
                    f.write(resultado['contenido'])
                logging.info(f"Se ha guardado el primer resultado exitoso en {archivo}")
    else:
        logging.error("No se encontró ninguna URL que funcione correctamente.")
        logging.info("Sugerencias:")
        logging.info("1. Verificar si el BOE de hoy está disponible")
        logging.info("2. Comprobar la conexión a Internet")
        logging.info("3. Verificar si la API del BOE ha cambiado")

if __name__ == "__main__":
    test_boe_connection()
