# -*- coding: utf-8 -*-
# generacion de archivo dump sql para postgresql
# tribunal superior de justicia de puebla

from pathlib import Path
import sqlite3

RUTA_BASE = Path(r"C:\Users\sahel\Documentos\SICOP OSP")
DB_SQLITE = RUTA_BASE / "sicop_unificado.db"
DUMP_SALIDA = RUTA_BASE / "dump_postgres.sql"

# tablas oficiales de materia penal a exportar
TABLAS = [
    "salas",
    "juzgados",
    "delitos",
    "usuarios",
    "apelaciones_penal"
]

print("generando archivo dump para postgresql...")

conn = sqlite3.connect(DB_SQLITE)
cursor = conn.cursor()

# mapear tipos de datos de sqlite hacia postgresql
def mapear_tipo(tipo_sqlite: str) -> str:
    t = tipo_sqlite.upper()
    if "INT" in t:
        return "BIGINT"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "DOUBLE PRECISION"
    return "TEXT"

# escapar cadenas de texto y comillas simples para sql
def escapar_cadena(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    val_str = str(val).replace("'", "''")
    return f"'{val_str}'"

with open(DUMP_SALIDA, "w", encoding="utf-8") as f:
    f.write("-- ========================================================\n")
    f.write("-- dump oficial sicop - poder judicial del estado de puebla\n")
    f.write("-- destino: postgresql 14 / 15 / 16\n")
    f.write("-- ========================================================\n\n")
    f.write("SET statement_timeout = 0;\n")
    f.write("SET client_encoding = 'UTF8';\n")
    f.write("SET standard_conforming_strings = on;\n\n")

    for tabla in TABLAS:
        cursor.execute(f"PRAGMA table_info({tabla})")
        cols_info = cursor.fetchall()
        
        if not cols_info:
            continue

        nombres_cols = [c[1] for c in cols_info]
        definicion_cols = [f'    "{c[1]}" {mapear_tipo(c[2])}' for c in cols_info]
        
        print(f"exportando tabla: {tabla}...")
        f.write(f'DROP TABLE IF EXISTS "{tabla}" CASCADE;\n')
        f.write(f'CREATE TABLE "{tabla}" (\n')
        f.write(",\n".join(definicion_cols))
        f.write("\n);\n\n")

        cursor.execute(f"SELECT * FROM {tabla}")
        filas = cursor.fetchall()

        if not filas:
            continue

        # insertar por lotes para optimizar memoria
        chunk_size = 500
        cols_str = ", ".join([f'"{c}"' for c in nombres_cols])
        
        for i in range(0, len(filas), chunk_size):
            lote = filas[i:i + chunk_size]
            filas_insert = []
            for row in lote:
                valores = [escapar_cadena(elem) for elem in row]
                filas_insert.append(f"({', '.join(valores)})")
            
            f.write(f'INSERT INTO "{tabla}" ({cols_str}) VALUES\n')
            f.write(",\n".join(filas_insert) + ";\n")
        
        f.write("\n")
        print(f"  reg: {tabla}: {len(filas)} registros escritos.")

conn.close()

print("\n" + "=" * 60)
print("dump sql generado exitosamente")
print(f"archivo listo en: {DUMP_SALIDA}")
print("=" * 60)
