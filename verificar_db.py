import os
import sqlite3
from pathlib import Path

def verificar_base_datos():
    # Buscar la base de datos
    posibles_rutas = [
        "boe/boe.db",
        "boe.db",
        "boe/db.sqlite3",
        "db.sqlite3"
    ]
    
    db_path = None
    for ruta in posibles_rutas:
        if Path(ruta).exists():
            db_path = ruta
            break
    
    if not db_path:
        print("No se encontró la base de datos en ninguna de las rutas esperadas.")
        return
    
    print(f"Base de datos encontrada en: {db_path}")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = [x[0] for x in cursor.fetchall()]
    
    print("\nTablas en la base de datos:")
    for tabla in tablas:
        print(f"- {tabla}")
    
    # Examinar la tabla de documentos simplificados
    tabla_documentos = "boe_analisis_documentosimplificado"
    
    if tabla_documentos not in tablas:
        print(f"\nNo se encontró la tabla {tabla_documentos} en la base de datos.")
        conn.close()
        return
    
    print(f"\nExaminando tabla: {tabla_documentos}")
    
    # Obtener estructura de la tabla
    cursor.execute(f"PRAGMA table_info({tabla_documentos})")
    columnas = cursor.fetchall()
    
    print("\nColumnas de la tabla:")
    for col in columnas:
        print(f"- {col[1]} ({col[2]})")
    
    # Contar registros
    cursor.execute(f"SELECT COUNT(*) FROM {tabla_documentos}")
    count = cursor.fetchone()[0]
    print(f"\nNúmero total de registros: {count}")
    
    # Verificar si existe la columna fecha_publicacion
    columna_fecha = None
    for col in columnas:
        if "fecha" in col[1].lower():
            columna_fecha = col[1]
            break
    
    if not columna_fecha:
        print("\nNo se encontró una columna de fecha en la tabla.")
        conn.close()
        return
    
    print(f"\nColumna de fecha encontrada: {columna_fecha}")
    
    # Obtener fechas disponibles
    cursor.execute(f"SELECT DISTINCT {columna_fecha} FROM {tabla_documentos} ORDER BY {columna_fecha} DESC LIMIT 10")
    fechas = cursor.fetchall()
    
    print("\nÚltimas 10 fechas disponibles:")
    for fecha in fechas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla_documentos} WHERE {columna_fecha} = ?", (fecha[0],))
        num_docs = cursor.fetchone()[0]
        print(f"- {fecha[0]}: {num_docs} documentos")
    
    # Cerrar conexión
    conn.close()

if __name__ == "__main__":
    verificar_base_datos()
