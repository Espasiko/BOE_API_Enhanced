"""
Script para instalar las dependencias de IA y ejecutar el procesamiento
"""
import os
import sys
import subprocess
import argparse

def instalar_dependencias():
    """Instala las dependencias necesarias para el procesamiento de IA"""
    print("Instalando dependencias de IA...")
    
    # Lista de paquetes necesarios
    paquetes = [
        "transformers==4.38.0",
        "torch==2.2.0",
        "sentencepiece==0.1.99"
    ]
    
    # Instalar cada paquete
    for paquete in paquetes:
        print(f"Instalando {paquete}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", paquete])
    
    print("Dependencias instaladas correctamente.")

def procesar_documentos(limit=50, force=False):
    """Ejecuta el procesamiento de documentos con IA"""
    print(f"Procesando documentos con IA (límite: {limit}, forzar: {force})...")
    
    # Construir comando
    cmd = [sys.executable, "manage.py", "procesar_ia", f"--limit={limit}"]
    if force:
        cmd.append("--force")
    
    # Ejecutar comando
    subprocess.check_call(cmd)

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Instalación y procesamiento de IA para BOE Alertas")
    parser.add_argument("--no-install", action="store_true", help="Omitir la instalación de dependencias")
    parser.add_argument("--limit", type=int, default=50, help="Número máximo de documentos a procesar")
    parser.add_argument("--force", action="store_true", help="Procesar incluso documentos ya procesados")
    
    args = parser.parse_args()
    
    if not args.no_install:
        instalar_dependencias()
    
    procesar_documentos(args.limit, args.force)
    
    print("Proceso completado con éxito.")

if __name__ == "__main__":
    main()
