# -*- coding: utf-8 -*-
# consolidacion y migracion de oficialia de salas penales
# tribunal superior de justicia de puebla

from pathlib import Path
from dbfread import DBF
from sqlalchemy import create_engine
import pandas as pd

# definir ruta base y conexion a sqlite local
RUTA_BASE = Path(r"C:\Users\sahel\Documentos\SICOP OSP")
DB_OUT = RUTA_BASE / "sicop_unificado.db"
engine = create_engine(f"sqlite:///{DB_OUT.as_posix()}")

carpetas = sorted([d for d in RUTA_BASE.iterdir() if d.is_dir()])

print("iniciando consolidacion exclusiva de materia penal...")

# cargar catalogos penales de referencia desde dbf
carpeta_ref = RUTA_BASE / "sicop"
catalogos_penal = {
    "salas": "salas.dbf",
    "juzgados": "juzgados.dbf",
    "delitos": "delitos.dbf"
}

for tabla_dest, archivo in catalogos_penal.items():
    ruta_f = carpeta_ref / archivo
    if ruta_f.exists():
        df_cat = pd.DataFrame(iter(DBF(str(ruta_f), encoding="cp1252", ignore_missing_memofile=True, load=True)))
        df_cat.columns = [c.lower().replace("año", "anio") for c in df_cat.columns]
        df_cat.to_sql(tabla_dest, con=engine, if_exists="replace", index=False)
        print(f"  catalogo [{tabla_dest}] cargado ({len(df_cat)} registros).")

# migrar tabla de usuarios desde acceso.dbf
f_acceso = carpeta_ref / "acceso.dbf" if (carpeta_ref / "acceso.dbf").exists() else carpeta_ref / "Acceso.dbf"
if f_acceso.exists():
    df_usr = pd.DataFrame(iter(DBF(str(f_acceso), encoding="cp1252", ignore_missing_memofile=True, load=True)))
    df_usr.columns = [c.lower() for c in df_usr.columns]
    df_usr.to_sql("usuarios", con=engine, if_exists="replace", index=False)
    print(f"  usuarios cargados desde acceso.dbf ({len(df_usr)} cuentas).")

# consolidacion de apelaciones penales (tocas)
filas_penal = []
for c in carpetas:
    f_dbf = c / "apelaciones.dbf"
    if f_dbf.exists():
        try:
            for row in DBF(str(f_dbf), encoding="cp1252", ignore_missing_memofile=True, load=False):
                filas_penal.append(dict(row))
        except Exception:
            pass

df_penal = pd.DataFrame(filas_penal)
df_penal.columns = [col.lower().replace("año", "anio") for col in df_penal.columns]

# regla de proteccion juridica: filtrar unicamente basura sintetica de prueba
def es_basura_real(row):
    p = str(row.get("proceso") or "").strip().upper()
    a = str(row.get("anio") or "").strip().upper()
    n = str(row.get("nombre") or "").strip().upper()
    d = str(row.get("delito") or "").strip().upper()
    f = str(row.get("folio") or "").strip()
    
    # registro totalmente vacio o solo puntos
    if (p in ["", "."]) and (n in ["", "."]) and (d in ["", "."]):
        return True
    
    # palabras explicitas de prueba del programador
    palabras_test = ["PRUEBA", "TEST", "ASDF", "QWER", "1111111112222222", "0000"]
    for t in palabras_test:
        if t in p or t in n or t in d:
            return True
            
    # folios cero de calibracion
    if f == "0" and (p in ["", ".", "0000"] or n in ["", ".", "PRUEBA"]):
        return True
        
    return False

# aplicar filtro selectivo
mascara_basura = df_penal.apply(es_basura_real, axis=1)
df_penal = df_penal[~mascara_basura]

# deduplicar protegiendo causas legitimas
cols_dedup_penal = [c for c in ["folio", "proceso", "anio", "nombre", "delito"] if c in df_penal.columns]
if cols_dedup_penal:
    df_penal = df_penal.drop_duplicates(subset=cols_dedup_penal, keep="first")

# guardar resultados limpios en sqlite
df_penal.to_sql("apelaciones_penal", con=engine, if_exists="replace", index=False)

print("\n" + "=" * 60)
print(f"total registros penales consolidados y protegidos: {len(df_penal)}")
print(f"base de datos generada en: {DB_OUT}")
print("=" * 60)
