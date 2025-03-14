import os
import sqlite3
import datetime
from pathlib import Path

def verificar_documentos_sqlite(fecha_str=None):
    """
    Verifica el estado de los documentos en la base de datos SQLite para una fecha específica
    
    Args:
        fecha_str: Fecha en formato YYYY-MM-DD (si es None, se usa la fecha actual)
    """
    try:
        # Usar la fecha proporcionada o la fecha actual
        if fecha_str:
            fecha = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = datetime.datetime.now().date()
        
        print(f"\nVerificando documentos para la fecha: {fecha}")
        
        # Encontrar la base de datos SQLite
        db_path = Path("boe/boe.db")
        if not db_path.exists():
            print(f"No se encontró la base de datos en {db_path}")
            return
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Convertir fecha a formato SQLite (YYYY-MM-DD)
        fecha_sqlite = fecha.strftime('%Y-%m-%d')
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM boe_analisis_documentosimplificado 
            WHERE fecha_publicacion = ?
        """, (fecha_sqlite,))
        total_docs = cursor.fetchone()[0]
        
        if total_docs == 0:
            print(f"No se encontraron documentos para la fecha {fecha}")
            return
        
        # Documentos con texto
        cursor.execute("""
            SELECT COUNT(*) 
            FROM boe_analisis_documentosimplificado 
            WHERE fecha_publicacion = ? 
            AND texto IS NOT NULL 
            AND texto != ''
        """, (fecha_sqlite,))
        docs_con_texto = cursor.fetchone()[0]
        
        docs_sin_texto = total_docs - docs_con_texto
        
        print(f"Total de documentos: {total_docs}")
        if total_docs > 0:
            print(f"Documentos con texto: {docs_con_texto} ({docs_con_texto/total_docs*100:.1f}%)")
            print(f"Documentos sin texto: {docs_sin_texto} ({docs_sin_texto/total_docs*100:.1f}%)")
        
        # Mostrar departamentos
        print("\nDocumentos por departamento:")
        cursor.execute("""
            SELECT departamento, COUNT(*) as total
            FROM boe_analisis_documentosimplificado 
            WHERE fecha_publicacion = ?
            GROUP BY departamento
            ORDER BY total DESC
        """, (fecha_sqlite,))
        
        departamentos = cursor.fetchall()
        
        for dept_row in departamentos:
            dept_name = dept_row[0] or "Sin departamento"
            count = dept_row[1]
            
            # Documentos con texto por departamento
            cursor.execute("""
                SELECT COUNT(*) 
                FROM boe_analisis_documentosimplificado 
                WHERE fecha_publicacion = ? 
                AND departamento = ?
                AND texto IS NOT NULL 
                AND texto != ''
            """, (fecha_sqlite, dept_row[0]))
            
            count_con_texto = cursor.fetchone()[0]
            
            print(f"- {dept_name}: {count} documentos ({count_con_texto} con texto)")
        
        # Mostrar algunos ejemplos de documentos
        print("\nEjemplos de documentos:")
        cursor.execute("""
            SELECT identificador, titulo, departamento, url_xml, texto
            FROM boe_analisis_documentosimplificado 
            WHERE fecha_publicacion = ?
            ORDER BY RANDOM()
            LIMIT 5
        """, (fecha_sqlite,))
        
        documentos = cursor.fetchall()
        
        for i, doc in enumerate(documentos):
            identificador, titulo, departamento, url_xml, texto = doc
            
            print(f"\n{i+1}. {identificador} - {titulo[:100]}...")
            print(f"   Departamento: {departamento or 'No especificado'}")
            print(f"   URL XML: {url_xml or 'No disponible'}")
            
            if texto:
                # Mostrar solo los primeros 150 caracteres del texto
                texto_preview = texto[:150].replace('\n', ' ').strip()
                print(f"   Texto: {texto_preview}...")
                print(f"   Longitud del texto: {len(texto)} caracteres")
            else:
                print("   Texto: No disponible")
        
        # Cerrar conexión
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Verificar el estado de los documentos en la base de datos SQLite')
    parser.add_argument('--fecha', type=str, help='Fecha en formato YYYY-MM-DD (por defecto: fecha actual)')
    
    args = parser.parse_args()
    
    # Ejecutar verificación
    verificar_documentos_sqlite(fecha_str=args.fecha)
