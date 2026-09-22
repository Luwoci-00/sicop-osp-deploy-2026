# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, date
import random
import math
from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

app = FastAPI(title="SICOP - Salas Penales Puebla")
DB_FILE = Path(__file__).resolve().parent / "sicop_unificado.db"
engine = create_engine(f"sqlite:///{DB_FILE.as_posix()}")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def asegurar_tabla_usuarios():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                nom_usu TEXT PRIMARY KEY,
                contra TEXT,
                nombre TEXT,
                nivel INTEGER,
                idjuzgado TEXT,
                id_ubica TEXT,
                descrip TEXT,
                folio TEXT
            )
        """))
        total = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() or 0
        if total == 0:
            conn.execute(text("""
                INSERT INTO usuarios (nom_usu, contra, nombre, nivel, descrip) VALUES
                ('ADMIN', '00220778', 'PEDRO PABLO NAJERA HUERTA', 6, 'ADMINISTRADOR'),
                ('CLAUDIA', 'LOPEZ', 'OFICIALIA COMUN SALAS PENALES', 1, 'OFICIALIA COMUN SALAS PENALES'),
                ('PENAL', '123', 'OFICIALIA COMUN PENALES', 5, 'OFICIALIA COMUN PENALES')
            """))

asegurar_tabla_usuarios()


def validar_sesion(usuario_cookie: str = None):
    if not usuario_cookie:
        return None
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT nom_usu, nombre, nivel FROM usuarios WHERE UPPER(nom_usu) = UPPER(:u)"), 
            {"u": usuario_cookie}
        ).fetchone()


# --- FUNCIONES DE NORMALIZACIÓN TIPOGRÁFICA ---
def formatear_nombre_sala(sala_id, desc_db):
    if desc_db:
        txt = str(desc_db).strip()
        num = ''.join(filter(str.isdigit, txt))
        if num:
            return f"{num}a. Sala Penal"
        return txt.title()
    if sala_id:
        num_id = ''.join(filter(str.isdigit, str(sala_id)))
        if num_id:
            return f"{num_id}a. Sala Penal"
    return "Sala Penal"


def formatear_nombre_juzgado(juzg_id, desc_db):
    if desc_db:
        txt = str(desc_db).strip()
        if txt.isupper() or not any(c.islower() for c in txt):
            return txt.title()
        return txt
    if juzg_id:
        return f"Juzgado {juzg_id}"
    return "Juzgado de Procedencia"


# --- LOGIN ---
@app.get("/login", response_class=HTMLResponse)
def login_view(error: str = ""):
    msg_error = f'<div class="bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2 rounded mb-4 text-center font-semibold">{error}</div>' if error else ""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SICOP - Iniciar Sesión</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
            input[type="text"] {{ text-transform: uppercase; }}
        </style>
    </head>
    <body class="bg-[#F0F2F5] min-h-screen flex items-center justify-center p-4 antialiased">
        <div class="bg-white border border-gray-300 rounded-lg shadow-xl max-w-md w-full p-8 space-y-6">
            <div class="text-center space-y-2">
                <img src="/static/logo2.png" alt="TSJ Puebla" class="h-14 mx-auto object-contain mb-2" onerror="this.style.display='none'">
                <h1 class="text-sm font-bold text-[#204768] tracking-tight">TRIBUNAL SUPERIOR DE JUSTICIA DE PUEBLA</h1>
                <p class="text-xs text-gray-500 font-medium">Oficialía Común de Salas Penales • SICOP</p>
            </div>

            {msg_error}

            <form action="/login" method="post" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1">USUARIO</label>
                    <input type="text" name="usuario" id="inp_usuario" required autocomplete="username" autofocus 
                           class="w-full text-xs border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-[#204768] focus:ring-1 focus:ring-[#204768] font-mono uppercase">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1">CONTRASEÑA</label>
                    <input type="password" name="password" required autocomplete="current-password" 
                           class="w-full text-xs border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-[#204768] focus:ring-1 focus:ring-[#204768] font-mono">
                </div>
                <button type="submit" class="w-full bg-[#204768] hover:bg-[#183650] text-white text-xs font-bold py-2.5 px-4 rounded shadow transition duration-150">
                    INGRESAR AL SISTEMA
                </button>
            </form>

            <div class="border-t border-gray-200 pt-4 text-center text-[10px] text-gray-400">
                SICOP Puebla v3.5 • Materia Penal
            </div>
        </div>
        <script>
            document.addEventListener('input', function (e) {{
                if (e.target && e.target.type === 'text') {{
                    const s = e.target.selectionStart, end = e.target.selectionEnd;
                    e.target.value = e.target.value.toUpperCase();
                    e.target.setSelectionRange(s, end);
                }}
            }});
        </script>
    </body>
    </html>
    """


@app.post("/login")
def login_action(usuario: str = Form(...), password: str = Form(...)):
    u_limpio = usuario.strip().upper()
    p_limpio = password.strip()

    with engine.connect() as conn:
        usr = conn.execute(
            text("SELECT nom_usu, contra, nombre FROM usuarios WHERE UPPER(TRIM(nom_usu)) = :u"),
            {"u": u_limpio}
        ).fetchone()

    if usr:
        clave_bd = str(usr.contra).strip()
        if clave_bd == p_limpio or clave_bd.upper() == p_limpio.upper():
            resp = RedirectResponse(url="/", status_code=303)
            resp.set_cookie(key="sicop_usr", value=usr.nom_usu.strip().upper(), httponly=True)
            return resp

    return RedirectResponse(url="/login?error=Usuario+o+contrase%C3%B1a+incorrectos", status_code=303)


@app.get("/logout")
def logout_action():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(key="sicop_usr")
    return resp


# --- PANTALLA PRINCIPAL PENAL ---
@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    tipo_busq: str = "NOMBRE", 
    valor_busq: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    pagina: int = 1,
    sicop_usr: str = Cookie(None)
):
    usr_activo = validar_sesion(sicop_usr)
    if not usr_activo:
        return RedirectResponse(url="/login", status_code=303)

    limite = 35
    offset = (pagina - 1) * limite
    filas_html = ""

    with engine.connect() as conn:
        total_expedientes = conn.execute(text("SELECT COUNT(*) FROM apelaciones_penal")).scalar() or 0
        juzgados_pen = conn.execute(text("SELECT id_juzgado, descrip FROM juzgados ORDER BY id_juzgado ASC")).fetchall()

        condiciones = []
        params = {"limite": limite, "offset": offset}

        if valor_busq.strip():
            params["v"] = f"%{valor_busq.strip().upper()}%"
            if tipo_busq == "FOLIO":
                condiciones.append("folio = :vf")
                params["vf"] = valor_busq.strip()
            elif tipo_busq == "PROCESO":
                condiciones.append("(proceso LIKE :v OR (proceso || '/' || anio) LIKE :v)")
            else:
                condiciones.append("UPPER(nombre) LIKE UPPER(:v)")

        if fecha_desde:
            condiciones.append("fecha >= :f_desde")
            params["f_desde"] = fecha_desde
        if fecha_hasta:
            condiciones.append("fecha <= :f_hasta")
            params["f_hasta"] = fecha_hasta

        where_clause = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

        total_res = conn.execute(text(f"SELECT COUNT(*) FROM apelaciones_penal {where_clause}"), params).scalar() or 0

        query = text(f"""
            SELECT a.folio, a.proceso, a.anio, s.descrip AS sala_desc, j.descrip AS juzg_desc,
                   a.nombre, a.delito, a.fecha, a.hora, a.sala, a.juzgado
            FROM apelaciones_penal a
            LEFT JOIN salas s ON a.sala = s.id_sala
            LEFT JOIN juzgados j ON a.juzgado = j.id_juzgado
            {where_clause.replace('folio', 'a.folio').replace('proceso', 'a.proceso').replace('nombre', 'a.nombre').replace('fecha', 'a.fecha')}
            ORDER BY a.fecha DESC, a.folio DESC
            LIMIT :limite OFFSET :offset
        """)
        registros = conn.execute(query, params).fetchall()

        for r in registros:
            delito_txt = r.delito or "—"
            s_desc = formatear_nombre_sala(r.sala, r.sala_desc)
            j_desc = formatear_nombre_juzgado(r.juzgado, r.juzg_desc)
            filas_html += f"""
            <tr onclick="seleccionarFila('{r.folio}', this)" class="border-b border-gray-100 hover:bg-slate-50 transition cursor-pointer text-xs text-gray-700">
                <td class="py-2.5 px-3 font-mono font-bold text-[#204768] truncate">{r.folio}</td>
                <td class="py-2.5 px-2 font-mono truncate">{r.proceso or '—'}</td>
                <td class="py-2.5 px-2 font-mono truncate">{r.anio or '—'}</td>
                <td class="py-2.5 px-3 font-semibold text-slate-800 truncate">{s_desc}</td>
                <td class="py-2.5 px-3 text-gray-600 truncate" title="{j_desc}">{j_desc}</td>
                <td class="py-2.5 px-3 font-medium text-gray-900 truncate" title="{r.nombre or ''}">{r.nombre or '—'}</td>
                <td class="py-2.5 px-3 text-gray-600 align-middle" title="{delito_txt}">
                    <span class="delito-clip">{delito_txt}</span>
                </td>
                <td class="py-2.5 px-2 font-mono text-[11px] text-gray-500 truncate">{r.fecha or '—'}</td>
                <td class="py-2.5 px-2 font-mono text-[11px] text-gray-400 truncate">{r.hora or '—'}</td>
            </tr>
            """

    opt_juzgados_pen = "".join([f"<option value='{j.id_juzgado}'>{j.id_juzgado} {formatear_nombre_juzgado(j.id_juzgado, j.descrip)}</option>" for j in juzgados_pen])

    # CÁLCULOS DE PAGINACIÓN EXACTA
    total_paginas = max(1, math.ceil(total_res / limite))
    inicio_num = min(offset + 1, total_res) if total_res > 0 else 0
    fin_num = min(offset + limite, total_res)
    tiene_prev = pagina > 1
    tiene_next = pagina < total_paginas
    nombre_usuario = usr_activo.nombre if usr_activo.nombre else usr_activo.nom_usu

    # BOTONES DE RETORNO Y AVANCE
    btn_primera = (
        f'<a href="/?tipo_busq={tipo_busq}&valor_busq={valor_busq}&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}&pagina=1" '
        f'class="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-100 text-gray-700 font-semibold transition shadow-xs" title="Volver a la primera página">«« Inicio</a>'
        if tiene_prev else ''
    )

    btn_anterior = (
        f'<a href="/?tipo_busq={tipo_busq}&valor_busq={valor_busq}&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}&pagina={pagina - 1}" '
        f'class="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-100 text-gray-700 font-medium transition">« Anterior</a>'
        if tiene_prev else ''
    )

    btn_siguiente = (
        f'<a href="/?tipo_busq={tipo_busq}&valor_busq={valor_busq}&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}&pagina={pagina + 1}" '
        f'class="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-100 text-gray-700 font-medium transition">Siguiente »</a>'
        if tiene_next else ''
    )

    btn_ultima = (
        f'<a href="/?tipo_busq={tipo_busq}&valor_busq={valor_busq}&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}&pagina={total_paginas}" '
        f'class="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-100 text-gray-700 font-semibold transition shadow-xs" title="Ir a la última página">Final »»</a>'
        if tiene_next else ''
    )

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>TSJ Puebla - Oficialía Común de Salas Penales</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
            input[type="text"], textarea {{ text-transform: uppercase; }}
            table.tabla-fija {{ table-layout: fixed; width: 100%; }}
            tr.selected-row {{ background-color: #EEF2F6 !important; outline: 2px solid #204768; }}
            .delito-clip {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; width: 100%; }}
            tr.selected-row .delito-clip {{ white-space: normal !important; overflow: visible !important; word-break: break-word; font-weight: 500; color: #0f172a; }}
            .custom-scrollbar::-webkit-scrollbar {{ width: 6px; height: 6px; }}
            .custom-scrollbar::-webkit-scrollbar-track {{ background: #f8fafc; }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
        </style>
    </head>
    <body class="bg-[#F8F9FA] min-h-screen text-slate-900 flex flex-col antialiased">

    <!-- BARRA SUPERIOR -->
    <header class="bg-white border-b border-gray-200 px-8 py-3 flex items-center justify-between sticky top-0 z-20 shadow-sm">
        <div class="flex items-center gap-4">
            <img src="/static/logo2.png" alt="Logo TSJ" class="h-9 w-auto object-contain" onerror="this.style.display='none'">
            <div>
                <h1 class="text-xs font-bold tracking-tight text-[#204768]">TRIBUNAL SUPERIOR DE JUSTICIA DEL ESTADO DE PUEBLA</h1>
                <p class="text-[10px] text-gray-400 uppercase tracking-wider">Sistema Integral de Oficialía Común de Salas Penales (SICOP)</p>
            </div>
        </div>

        <div class="flex items-center gap-4">
            <div class="flex items-center gap-2 text-xs font-medium text-gray-700 bg-gray-50 px-3 py-1.5 rounded border border-gray-200">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>OPERADOR: <b>{nombre_usuario.upper()}</b></span>
            </div>
            <a href="/logout" class="inline-flex items-center gap-1.5 text-xs text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 border border-red-200 px-3 py-1.5 rounded transition font-bold" title="Cerrar Sesión">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                <span>SALIR</span>
            </a>
        </div>
    </header>

    <div class="flex flex-1 max-w-[1700px] w-full mx-auto p-4 md:p-6 gap-6 overflow-hidden">
        
        <!-- CONTENIDO PRINCIPAL -->
        <div class="flex-1 flex flex-col gap-4 overflow-hidden">
            <!-- BOTONERA SUPERIOR -->
            <div class="bg-white border border-gray-200 rounded-lg p-3 shadow-sm flex flex-wrap items-center justify-between gap-3">
                <div class="flex flex-wrap items-center gap-2">
                    <button onclick="abrirModal()" class="inline-flex items-center gap-2 bg-[#204768] hover:bg-[#183650] text-white text-xs font-semibold px-4 py-2 rounded shadow-sm transition">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                        <span>ALTA DE TURNO (PENAL)</span>
                    </button>
                    
                    <a href="/reporte_diario" class="inline-flex items-center gap-2 border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold px-4 py-2 rounded transition">
                        <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        <span>REPORTE DIARIO DE INGRESOS</span>
                    </a>

                    <a href="/reporte_entrega" class="inline-flex items-center gap-2 border border-[#204768] bg-[#EEF2F6] hover:bg-[#dbe4ee] text-[#204768] text-xs font-bold px-4 py-2 rounded transition shadow-sm">
                        <svg class="w-3.5 h-3.5 text-[#204768]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                        <span>REPORTE DE ENTREGA A SALAS</span>
                    </a>
                </div>
                
                <div class="text-xs text-gray-500 font-mono">
                    Total Apelaciones: <b class="text-slate-800">{total_expedientes}</b>
                </div>
            </div>

            <!-- BÚSQUEDA Y FILTROS -->
            <section class="bg-white border border-gray-200 rounded-lg p-3 shadow-sm flex flex-wrap items-center justify-between gap-3">
                <form method="get" action="/" class="flex flex-1 flex-wrap items-center gap-3">
                    <span class="text-xs font-bold text-gray-600 uppercase tracking-wide">Buscar:</span>
                    <select name="tipo_busq" class="text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:border-[#204768] font-medium text-gray-700 uppercase">
                        <option value="NOMBRE" {'selected' if tipo_busq=='NOMBRE' else ''}>SENTENCIADO / IMPUTADO</option>
                        <option value="FOLIO" {'selected' if tipo_busq=='FOLIO' else ''}>FOLIO_A</option>
                        <option value="PROCESO" {'selected' if tipo_busq=='PROCESO' else ''}>PROCESO / AÑO</option>
                    </select>
                    <div class="relative flex-1 min-w-[200px] max-w-md">
                        <input type="text" name="valor_busq" value="{valor_busq}" placeholder="Escriba el criterio a consultar..." class="w-full text-xs border border-gray-300 rounded px-3 py-1.5 focus:outline-none focus:border-[#204768] uppercase" autofocus>
                    </div>

                    <div class="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
                        <span>Desde:</span>
                        <input type="date" name="fecha_desde" value="{fecha_desde}" class="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:border-[#204768] font-mono">
                        <span>Hasta:</span>
                        <input type="date" name="fecha_hasta" value="{fecha_hasta}" class="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:border-[#204768] font-mono">
                    </div>

                    <button type="submit" class="bg-[#204768] hover:bg-[#183650] text-white p-2 rounded transition" title="Filtrar">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                    </button>
                    <a href="/" class="text-xs text-gray-500 hover:text-gray-800 px-2 font-medium">Limpiar</a>
                </form>

                <div class="text-xs font-mono text-gray-500 shrink-0">
                    Mostrando: <b>{inicio_num}</b> a <b>{fin_num}</b> de <b>{total_res}</b>
                </div>
            </section>

            <!-- TABLA PRINCIPAL DE APELACIONES -->
            <section class="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden flex-1 flex flex-col min-h-[420px]">
                <div class="overflow-x-auto custom-scrollbar flex-1">
                    <table class="tabla-fija text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-50 border-b border-gray-200 text-[10px] font-bold uppercase tracking-wider text-gray-600 sticky top-0 z-10 shadow-[0_1px_0_rgba(0,0,0,0.05)]">
                                <th class="py-2.5 px-3 w-[70px] font-mono">FOLIO_A</th>
                                <th class="py-2.5 px-2 w-[65px] font-mono">PROCESO</th>
                                <th class="py-2.5 px-2 w-[55px] font-mono">AÑO</th>
                                <th class="py-2.5 px-3 w-[115px]">SALA</th>
                                <th class="py-2.5 px-3 w-[210px]">PROCEDENCIA</th>
                                <th class="py-2.5 px-3 w-[170px]">NOMBRE</th>
                                <th class="py-2.5 px-3">DELITO(S)</th>
                                <th class="py-2.5 px-2 w-[85px] font-mono">FECHA</th>
                                <th class="py-2.5 px-2 w-[70px] font-mono">HORA</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                            {filas_html if filas_html else '<tr><td colspan="9" class="text-center py-12 text-gray-400 text-xs">No se encontraron apelaciones penales con los criterios seleccionados.</td></tr>'}
                        </tbody>
                    </table>
                </div>

                <!-- BARRA DE PAGINACIÓN CON BOTÓN INICIO -->
                <div class="border-t border-gray-200 px-4 py-2.5 bg-gray-50 flex items-center justify-between">
                    <div class="text-xs text-gray-500 font-medium">
                        Página <b class="text-gray-800">{pagina}</b> de <b class="text-gray-800">{total_paginas}</b>
                    </div>
                    <div class="flex items-center gap-1.5">
                        {btn_primera}
                        {btn_anterior}
                        {btn_siguiente}
                        {btn_ultima}
                    </div>
                </div>
            </section>

            <!-- BARRA INFERIOR -->
            <section class="bg-white border border-gray-200 rounded-lg p-3 shadow-sm flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <span class="text-xs font-bold text-gray-700">Folio Seleccionado:</span>
                    <input type="text" id="folio_sel" class="w-24 text-center font-mono text-xs font-bold border border-gray-300 rounded py-1 bg-gray-50 focus:outline-none" readonly placeholder="—">
                    <button onclick="copiarFolio()" class="inline-flex items-center gap-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold px-3 py-1 rounded border border-gray-300 transition" title="Copiar folio al portapapeles">
                        📋 Copiar
                    </button>
                    <span id="msgCopiado" class="text-[10px] text-emerald-600 font-bold opacity-0 transition-opacity duration-300">¡Copiado!</span>
                </div>

                <div class="flex items-center gap-3">
                    <button onclick="imprimirSello()" class="inline-flex items-center gap-2 border border-gray-300 hover:bg-gray-50 text-[#204768] text-xs font-semibold px-4 py-1.5 rounded transition">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4H7v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                        <span>Imprimir Boleta de Turno</span>
                    </button>
                </div>
            </section>
        </div>
    </div>

    <!-- MODAL DE ALTA DE TURNO PENAL -->
    <div id="modalAlta" class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 hidden justify-center items-center p-4 md:p-6">
        <div class="bg-white border border-gray-300 rounded-lg shadow-2xl max-w-5xl w-full h-[90vh] flex flex-col overflow-hidden">
            <div class="border-b border-gray-200 px-6 py-3 flex items-center justify-between bg-white">
                <div class="flex items-center gap-3">
                    <span class="text-[11px] font-bold text-[#204768] bg-[#EEF2F6] px-2 py-0.5 rounded">OFICIALÍA SALAS PENALES</span>
                    <h2 class="text-sm font-bold text-slate-800">ALTA Y ASIGNACIÓN DE TURNO</h2>
                </div>
                <button type="button" onclick="cerrarModal()" class="text-gray-400 hover:text-gray-700 text-xl font-bold leading-none">&times;</button>
            </div>

            <form action="/guardar_turno" method="post" class="flex flex-1 overflow-hidden bg-[#FDFDFD]">
                <div class="flex-[3] space-y-4 p-5 overflow-y-auto">
                    <fieldset class="bg-white border border-gray-200 rounded p-4 space-y-3">
                        <legend class="text-[11px] font-bold text-gray-700 uppercase tracking-wide px-1">1. Proceso de Origen</legend>
                        <div class="grid grid-cols-3 gap-3">
                            <div>
                                <label class="block text-[10px] font-semibold text-gray-600 mb-1">PROCESO *</label>
                                <input type="text" name="proceso" id="inp_proceso" oninput="actualizarPreviewPenal()" required placeholder="Ej. 244" class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-[#204768] focus:outline-none font-mono uppercase">
                            </div>
                            <div>
                                <label class="block text-[10px] font-semibold text-gray-600 mb-1">AÑO *</label>
                                <input type="text" name="anio" id="inp_anio" oninput="actualizarPreviewPenal()" value="2026" required class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-[#204768] focus:outline-none font-mono uppercase">
                            </div>
                            <div>
                                <label class="block text-[10px] font-semibold text-gray-600 mb-1">ACUMULADO</label>
                                <input type="text" name="acum" id="inp_acum" placeholder="TOCA..." class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-[#204768] focus:outline-none font-mono uppercase">
                            </div>
                        </div>
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-600 mb-1">JUZGADO DE PROCEDENCIA *</label>
                            <select name="juzgado" id="inp_juzgado" onchange="actualizarPreviewPenal()" class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white focus:border-[#204768] focus:outline-none uppercase">
                                {opt_juzgados_pen}
                                <option value="OTRO">OTRO / FORÁNEO / SIN ASIGNAR</option>
                            </select>
                        </div>
                    </fieldset>

                    <fieldset class="bg-white border border-gray-200 rounded p-4 space-y-3">
                        <legend class="text-[11px] font-bold text-gray-700 uppercase tracking-wide px-1">2. Resolución Impugnada</legend>
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-[10px] font-semibold text-gray-600 mb-1">TIPO *</label>
                                <div class="flex items-center gap-5 text-xs mt-1.5">
                                    <label class="inline-flex items-center gap-1.5 cursor-pointer font-medium">
                                        <input type="radio" name="tipo_apela" value="S" checked onchange="cambiarTipoPenal('S')" class="text-[#204768]"> 
                                        <span>SENTENCIAS</span>
                                    </label>
                                    <label class="inline-flex items-center gap-1.5 cursor-pointer font-medium">
                                        <input type="radio" name="tipo_apela" value="A" onchange="cambiarTipoPenal('A')" class="text-[#204768]"> 
                                        <span>AUTOS</span>
                                    </label>
                                </div>
                            </div>
                            <div>
                                <label class="block text-[10px] font-semibold text-gray-600 mb-1">CONCEPTO *</label>
                                <select name="concepto" id="selectConcepto" onchange="actualizarPreviewPenal()" required class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white focus:border-[#204768] focus:outline-none uppercase">
                                </select>
                            </div>
                        </div>
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-600 mb-1">FECHA DE RESOLUCIÓN *</label>
                            <input type="date" name="resolucion" required value="{date.today().strftime('%Y-%m-%d')}" class="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-[#204768] focus:outline-none font-mono">
                        </div>
                    </fieldset>

                    <fieldset class="bg-white border border-gray-200 rounded p-4 space-y-3">
                        <legend class="text-[11px] font-bold text-gray-700 uppercase tracking-wide px-1">3. Causa y Partes</legend>
                        <div>
                            <label id="lblNombre" class="block text-[10px] font-semibold text-gray-600 mb-1">SENTENCIADO *</label>
                            <textarea name="nombre" id="inp_nombre" oninput="actualizarPreviewPenal()" required rows="2" placeholder="Nombre completo..." class="w-full text-xs border border-gray-300 rounded p-2 focus:border-[#204768] focus:outline-none uppercase"></textarea>
                        </div>
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-600 mb-1">DELITO(S) *</label>
                            <textarea name="delito" id="inp_delito" oninput="actualizarPreviewPenal()" required rows="2" placeholder="Delito(s) imputados..." class="w-full text-xs border border-gray-300 rounded p-2 focus:border-[#204768] focus:outline-none uppercase"></textarea>
                        </div>
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-600 mb-2">APELANTE</label>
                            <div class="grid grid-cols-2 gap-2 text-xs text-gray-700">
                                <label class="inline-flex items-center gap-2"><input type="checkbox" name="proceado" value="1" class="rounded text-[#204768]"> <span id="lblApelante">SENTENCIADO</span></label>
                                <label class="inline-flex items-center gap-2"><input type="checkbox" name="mp" value="1" class="rounded text-[#204768]"> MINISTERIO PÚBLICO</label>
                                <label class="inline-flex items-center gap-2"><input type="checkbox" name="defensa" value="1" class="rounded text-[#204768]"> DEFENSA</label>
                                <label class="inline-flex items-center gap-2"><input type="checkbox" name="agraviado" value="1" class="rounded text-[#204768]"> VÍCTIMA U OFENDIDO</label>
                            </div>
                        </div>
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-600 mb-1">ANEXOS</label>
                            <textarea name="anexos" rows="2" placeholder="Fojas, cuadernos..." class="w-full text-xs border border-gray-300 rounded p-2 focus:border-[#204768] focus:outline-none uppercase"></textarea>
                        </div>
                    </fieldset>
                </div>

                <section class="w-96 bg-[#FAFBFD] border-l border-gray-200 p-5 flex flex-col justify-between overflow-y-auto">
                    <div class="space-y-4">
                        <div class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Previsualización de Boleta</div>
                        <div class="bg-white border border-gray-300 rounded shadow-sm p-5 text-xs space-y-3 font-serif">
                            <div class="text-center pb-2 border-b border-gray-200">
                                <img src="/static/logo2.png" alt="Logo TSJ" class="h-10 mx-auto object-contain mb-1" onerror="this.style.display='none'">
                                <div class="font-bold text-slate-900 text-[10px] font-sans tracking-wide">TRIBUNAL SUPERIOR DE JUSTICIA</div>
                                <div class="text-[9px] text-gray-500 font-sans uppercase">Oficialía Común de Salas Penales • Puebla</div>
                            </div>
                            <div class="space-y-1.5 text-gray-800 text-[11px]">
                                <div><span class="font-sans font-bold text-[9px] text-gray-400 uppercase">Expediente:</span> <span id="prev_exp" class="font-mono font-bold">—</span></div>
                                <div><span class="font-sans font-bold text-[9px] text-gray-400 uppercase">Procedencia:</span> <span id="prev_juzg" class="font-sans text-gray-700 leading-tight block">—</span></div>
                                <div><span class="font-sans font-bold text-[9px] text-gray-400 uppercase">Tipo/Acto:</span> <span id="prev_tipo" class="font-sans">—</span></div>
                                <div><span class="font-sans font-bold text-[9px] text-gray-400 uppercase">Parte:</span> <span id="prev_nom" class="font-sans font-semibold text-slate-900 block">—</span></div>
                                <div><span class="font-sans font-bold text-[9px] text-gray-400 uppercase">Delito(s):</span> <span id="prev_del" class="font-sans text-gray-600 block">—</span></div>
                            </div>
                            <div class="border border-[#204768] p-2 text-center font-sans bg-[#EEF2F6] rounded mt-2">
                                <div class="text-[9px] uppercase tracking-wider font-semibold text-gray-500">Asignación Judicial</div>
                                <div class="text-xs font-bold text-[#204768] mt-0.5">TURNO A SALAS PENALES</div>
                            </div>
                        </div>
                    </div>
                    <div class="pt-4 border-t border-gray-200 flex flex-col gap-2">
                        <button type="submit" class="w-full bg-[#204768] hover:bg-[#183650] text-white font-semibold py-2.5 px-4 rounded text-xs transition shadow-sm">
                            Guardar y Asignar Sala
                        </button>
                        <button type="button" onclick="cerrarModal()" class="w-full border border-gray-300 hover:bg-gray-100 text-gray-700 font-medium py-2 px-4 rounded text-xs transition">
                            Salir
                        </button>
                    </div>
                </section>
            </form>
        </div>
    </div>

    <!-- MODAL DE VISTA PREVIA E IMPRESIÓN DE BOLETA -->
    <div id="modalBoleta" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 hidden justify-center items-center p-4">
        <div class="bg-white border border-gray-300 rounded-lg shadow-2xl max-w-xl w-full flex flex-col overflow-hidden">
            <div class="border-b border-gray-200 px-5 py-3 flex items-center justify-between bg-gray-50">
                <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wide">Previsualización de Boleta Oficial</h3>
                <button type="button" onclick="cerrarModalBoleta()" class="text-gray-400 hover:text-gray-700 text-xl font-bold leading-none">&times;</button>
            </div>
            <div class="p-4 bg-gray-100 flex justify-center overflow-y-auto max-h-[75vh]">
                <iframe id="iframeBoleta" class="w-[580px] h-[480px] bg-white border border-gray-300 shadow-sm rounded"></iframe>
            </div>
            <div class="border-t border-gray-200 px-5 py-3 bg-white flex justify-end gap-2">
                <button onclick="imprimirIframe()" class="bg-[#204768] hover:bg-[#183650] text-white text-xs font-semibold px-4 py-2 rounded transition shadow-xs">
                    🖨️ Imprimir Boleta
                </button>
                <button onclick="cerrarModalBoleta()" class="border border-gray-300 hover:bg-gray-100 text-gray-700 text-xs font-medium px-4 py-2 rounded transition">
                    Cerrar
                </button>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('input', function (e) {{
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {{
                if (e.target.type === 'text' || e.target.tagName === 'TEXTAREA') {{
                    const s = e.target.selectionStart, end = e.target.selectionEnd;
                    e.target.value = e.target.value.toUpperCase();
                    e.target.setSelectionRange(s, end);
                }}
            }}
        }});

        const conceptosSentencias = ["CONDENATORIA", "ABSOLUTORIA"];
        const conceptosAutos = ["FORMAL PRISION", "LIBERTAD", "NIEGA ORDEN DE APREHENSION", "FIJA/MODIFICA MONTO DE FIANZA"];
        let tipoActual = 'S';

        function cambiarTipoPenal(tipo) {{
            tipoActual = tipo;
            const select = document.getElementById('selectConcepto');
            const lblNombre = document.getElementById('lblNombre');
            const lblApelante = document.getElementById('lblApelante');
            if(!select) return;
            select.innerHTML = '';

            const lista = (tipo === 'S') ? conceptosSentencias : conceptosAutos;
            lista.forEach(opt => {{
                const el = document.createElement('option');
                el.value = opt;
                el.textContent = opt;
                select.appendChild(el);
            }});

            if (tipo === 'S') {{
                lblNombre.textContent = 'SENTENCIADO *';
                lblApelante.textContent = 'SENTENCIADO';
            }} else {{
                lblNombre.textContent = 'IMPUTADO *';
                lblApelante.textContent = 'IMPUTADO';
            }}
            actualizarPreviewPenal();
        }}

        function actualizarPreviewPenal() {{
            const p = document.getElementById('inp_proceso')?.value || '—';
            const a = document.getElementById('inp_anio')?.value || '—';
            const nom = document.getElementById('inp_nombre')?.value || '—';
            const del = document.getElementById('inp_delito')?.value || '—';
            const jSel = document.getElementById('inp_juzgado');
            const juzg = jSel?.options[jSel.selectedIndex] ? jSel.options[jSel.selectedIndex].text : '—';
            const cSel = document.getElementById('selectConcepto');
            const cText = cSel?.options[cSel.selectedIndex] ? cSel.options[cSel.selectedIndex].text : '';

            if(document.getElementById('prev_exp')) document.getElementById('prev_exp').textContent = p + '/' + a;
            if(document.getElementById('prev_juzg')) document.getElementById('prev_juzg').textContent = juzg;
            if(document.getElementById('prev_tipo')) document.getElementById('prev_tipo').textContent = (tipoActual === 'S' ? 'SENTENCIA' : 'AUTO') + ' - ' + cText;
            if(document.getElementById('prev_nom')) document.getElementById('prev_nom').textContent = nom;
            if(document.getElementById('prev_del')) document.getElementById('prev_del').textContent = del;
        }}

        if(document.getElementById('selectConcepto')) {{
            cambiarTipoPenal('S');
        }}

        function abrirModal() {{ 
            const m = document.getElementById('modalAlta');
            m.classList.remove('hidden');
            m.classList.add('flex');
            actualizarPreviewPenal();
        }}
        function cerrarModal() {{ 
            const m = document.getElementById('modalAlta');
            m.classList.add('hidden');
            m.classList.remove('flex');
        }}
        
        function seleccionarFila(folio, tr) {{
            document.querySelectorAll('tbody tr').forEach(r => r.classList.remove('selected-row'));
            tr.classList.add('selected-row');
            document.getElementById('folio_sel').value = folio;
        }}

        function copiarFolio() {{
            const f = document.getElementById('folio_sel').value;
            if(!f || f === '—') return alert('Por favor seleccione primero un expediente de la tabla.');
            
            navigator.clipboard.writeText(f).then(() => {{
                const msg = document.getElementById('msgCopiado');
                if(msg) {{
                    msg.classList.remove('opacity-0');
                    setTimeout(() => {{
                        msg.classList.add('opacity-0');
                    }}, 1500);
                }}
            }});
        }}
        
        function imprimirSello() {{
            const f = document.getElementById('folio_sel').value;
            if(!f || f === '—') return alert('Por favor seleccione primero un expediente de la tabla.');
            
            const modal = document.getElementById('modalBoleta');
            const iframe = document.getElementById('iframeBoleta');
            if(modal && iframe) {{
                iframe.src = '/imprimir_boleta/' + f;
                modal.classList.remove('hidden');
                modal.classList.add('flex');
            }}
        }}

        function cerrarModalBoleta() {{
            const modal = document.getElementById('modalBoleta');
            const iframe = document.getElementById('iframeBoleta');
            if(modal && iframe) {{
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                iframe.src = '';
            }}
        }}

        function imprimirIframe() {{
            const iframe = document.getElementById('iframeBoleta');
            if(iframe && iframe.contentWindow) {{
                iframe.contentWindow.print();
            }}
        }}
    </script>
    </body>
    </html>
    """


# --- GUARDADO TURNO PENAL CON VALIDACIÓN INTELIGENTE ---
@app.post("/guardar_turno", response_class=HTMLResponse)
async def guardar_turno(request: Request, sicop_usr: str = Cookie(None)):
    usr_activo = validar_sesion(sicop_usr)
    if not usr_activo:
        return RedirectResponse(url="/login", status_code=303)

    form_data = await request.form()
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_hoy = ahora.strftime("%H:%M:%S")

    proceso = form_data.get("proceso", "").strip().upper()
    anio = form_data.get("anio", "").strip().upper()
    acum = form_data.get("acum", "").strip().upper()
    juzgado = form_data.get("juzgado", "").strip() or "OTRO"
    tipo_apela = form_data.get("tipo_apela", "S").strip()
    concepto = form_data.get("concepto", "").strip()
    resolucion = form_data.get("resolucion", "").strip()
    nombre = form_data.get("nombre", "").strip().upper()
    delito = form_data.get("delito", "").strip().upper()
    anexos = form_data.get("anexos", "").strip().upper()
    proceado = 1 if form_data.get("proceado") else 0
    mp = 1 if form_data.get("mp") else 0
    defensa = 1 if form_data.get("defensa") else 0
    agraviado = 1 if form_data.get("agraviado") else 0

    caracteres_invalidos = ["", ".", "..", "...", "---", "XXX", "PRUEBA", "TEST", "ASDF", "QWER"]
    
    campos_faltantes = []
    if not proceso or proceso in caracteres_invalidos:
        campos_faltantes.append("Número de Proceso")
    if not anio or anio in caracteres_invalidos:
        campos_faltantes.append("Año del Proceso")
    if not resolucion:
        campos_faltantes.append("Fecha de Resolución")
    if not concepto:
        campos_faltantes.append("Concepto del Acto Impugnado")

    if campos_faltantes:
        errores_txt = "\\n • ".join(campos_faltantes)
        return f"""
        <script>
            alert('ERROR: No es posible dar de alta el expediente porque faltan campos obligatorios:\\n\\n • {errores_txt}');
            window.history.back();
        </script>
        """

    if not nombre or nombre in caracteres_invalidos:
        nombre = "SE IGNORA / RESERVADO"
    if not delito or delito in caracteres_invalidos:
        delito = "NO ESPECIFICADO"

    with engine.begin() as conn:
        q_ant = text("""
            SELECT folio, sala FROM apelaciones_penal
            WHERE (proceso = :p AND anio = :a AND :p != '') OR (UPPER(TRIM(nombre)) = UPPER(TRIM(:n)) AND :n != 'SE IGNORA / RESERVADO')
            ORDER BY fecha DESC, folio DESC LIMIT 1
        """)
        ant = conn.execute(q_ant, {"p": proceso, "a": anio, "n": nombre}).fetchone()
        if ant and ant.sala:
            sala_id = str(ant.sala)
        else:
            cargas = conn.execute(text("SELECT s.id_sala, COUNT(a.folio) AS total FROM salas s LEFT JOIN apelaciones_penal a ON s.id_sala = a.sala GROUP BY s.id_sala ORDER BY total ASC")).fetchall()
            min_c = cargas[0].total
            salas_cands = [str(r.id_sala) for r in cargas if r.total == min_c]
            sala_id = random.choice(salas_cands)

        max_folio = conn.execute(text("SELECT COALESCE(MAX(folio), 0) + 1 FROM apelaciones_penal")).scalar()
        conn.execute(text("""
            INSERT INTO apelaciones_penal (
                folio, proceso, anio, acum, juzgado, tipo_apela,
                tipo, resolucion, nombre, delito, anexos,
                proceado, mp, defensa, agraviado, sala, fecha, hora, estatus
            ) VALUES (
                :folio, :proceso, :anio, :acum, :juzgado, :tipo_apela,
                :tipo, :resolucion, :nombre, :delito, :anexos,
                :proceado, :mp, :defensa, :agraviado, :sala, :fecha, :hora, 'A'
            )
        """), {
            "folio": max_folio, "proceso": proceso, "anio": anio, "acum": acum, "juzgado": juzgado,
            "tipo_apela": tipo_apela, "tipo": concepto, "resolucion": resolucion, "nombre": nombre,
            "delito": delito, "anexos": anexos, "proceado": proceado, "mp": mp, "defensa": defensa,
            "agraviado": agraviado, "sala": sala_id, "fecha": fecha_hoy, "hora": hora_hoy
        })

    return f"""
    <script>
        alert('Apelación registrada con éxito.\\nFolio asignado: {max_folio}\\nTurnado a: SALA {sala_id} PENAL');
        window.location.href = '/?valor_busq={max_folio}&tipo_busq=FOLIO';
    </script>
    """


# --- REPORTE DIARIO DE INGRESOS PENALES ---
@app.get("/reporte_diario", response_class=HTMLResponse)
def reporte_diario(fecha_rep: str = "", sicop_usr: str = Cookie(None)):
    usr_activo = validar_sesion(sicop_usr)
    if not usr_activo:
        return RedirectResponse(url="/login", status_code=303)

    hoy = fecha_rep if fecha_rep else date.today().strftime("%Y-%m-%d")
    filas = ""

    with engine.connect() as conn:
        registros = conn.execute(text("""
            SELECT a.folio, a.hora, j.descrip AS juzg_desc, a.proceso, a.anio, 
                   a.tipo_apela, a.tipo, s.descrip AS sala_desc, a.nombre, a.delito, a.sala, a.juzgado
            FROM apelaciones_penal a
            LEFT JOIN salas s ON a.sala = s.id_sala
            LEFT JOIN juzgados j ON a.juzgado = j.id_juzgado
            WHERE a.fecha = :hoy
            ORDER BY a.folio ASC
        """), {"hoy": hoy}).fetchall()

        for r in registros:
            s_desc = formatear_nombre_sala(r.sala, r.sala_desc)
            j_desc = formatear_nombre_juzgado(r.juzg_desc if hasattr(r, 'juzg_desc') else None, r.juzg_desc)
            t_desc = f"{'SENTENCIA' if r.tipo_apela == 'S' else 'AUTO'} ({r.tipo or ''})"
            filas += f"""
            <tr class="border-b border-gray-200">
                <td class="p-2.5 font-mono font-bold text-[#204768]">{r.folio}</td>
                <td class="p-2.5 font-mono text-gray-500">{r.hora}</td>
                <td class="p-2.5">{j_desc}</td>
                <td class="p-2.5 font-mono">{r.proceso}/{r.anio}</td>
                <td class="p-2.5">{t_desc}</td>
                <td class="p-2.5 font-bold text-slate-900">{s_desc}</td>
                <td class="p-2.5 font-medium">{r.nombre}</td>
                <td class="p-2.5 text-gray-500">{r.delito}</td>
            </tr>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Reporte Diario Penal - {hoy}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>body {{ font-family: 'Inter', sans-serif; }} @media print {{ .no-print {{ display: none; }} }}</style>
    </head>
    <body class="bg-white p-8 text-xs text-slate-900 max-w-6xl mx-auto">
        <div class="flex justify-between items-start border-b border-gray-300 pb-4 mb-6">
            <div class="flex items-center gap-3">
                <img src="/static/logo2.png" style="height: 38px;" onerror="this.style.display='none'">
                <div>
                    <h2 class="text-base font-bold text-[#204768]">TRIBUNAL SUPERIOR DE JUSTICIA DE PUEBLA</h2>
                    <h4 class="text-xs text-gray-500 font-medium">Oficialía Común de Salas Penales — Reporte Diario de Ingresos</h4>
                </div>
            </div>
            <div class="text-right">
                <div class="font-mono text-xs text-gray-600 font-bold">Fecha: {hoy}</div>
                <form method="get" action="/reporte_diario" class="no-print mt-1 flex items-center gap-1">
                    <input type="date" name="fecha_rep" value="{hoy}" class="border border-gray-300 rounded px-1.5 py-0.5 text-[11px] font-mono">
                    <button type="submit" class="bg-slate-200 px-2 py-0.5 rounded text-[11px] font-semibold hover:bg-slate-300">Cambiar</button>
                </form>
            </div>
        </div>
        <div class="no-print flex justify-end gap-3 mb-4">
            <button onclick="window.print()" class="bg-[#204768] hover:bg-[#183650] text-white font-semibold px-3.5 py-1.5 rounded transition">Imprimir Reporte</button>
            <a href="/" class="border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50 font-semibold transition">Volver</a>
        </div>
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="border-b-2 border-[#204768] text-[#204768] font-bold text-[11px]">
                    <th class="p-2.5">Folio</th>
                    <th class="p-2.5">Hora</th>
                    <th class="p-2.5">Procedencia</th>
                    <th class="p-2.5">Expediente</th>
                    <th class="p-2.5">Acto Impugnado</th>
                    <th class="p-2.5">Sala Turnada</th>
                    <th class="p-2.5">Parte Imputada</th>
                    <th class="p-2.5">Delito(s)</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
                {filas if filas else f'<tr><td colspan="8" class="text-center p-8 text-gray-400">Sin apelaciones registradas el {hoy}.</td></tr>'}
            </tbody>
        </table>
    </body>
    </html>
    """


# --- REPORTE DE ENTREGA A SALAS ---
@app.get("/reporte_entrega", response_class=HTMLResponse)
def reporte_entrega(fecha_rep: str = "", sicop_usr: str = Cookie(None)):
    usr_activo = validar_sesion(sicop_usr)
    if not usr_activo:
        return RedirectResponse(url="/login", status_code=303)

    hoy = fecha_rep if fecha_rep else date.today().strftime("%Y-%m-%d")
    filas = ""

    with engine.connect() as conn:
        registros = conn.execute(text("""
            SELECT a.folio, a.hora, j.descrip AS juzg_desc, a.proceso, a.anio, 
                   s.descrip AS sala_desc, a.nombre, a.delito, a.sala, a.juzgado
            FROM apelaciones_penal a
            LEFT JOIN salas s ON a.sala = s.id_sala
            LEFT JOIN juzgados j ON a.juzgado = j.id_juzgado
            WHERE a.fecha = :hoy
            ORDER BY a.sala ASC, a.folio ASC
        """), {"hoy": hoy}).fetchall()

        for r in registros:
            s_desc = formatear_nombre_sala(r.sala, r.sala_desc)
            j_desc = formatear_nombre_juzgado(r.juzgado, r.juzg_desc)
            filas += f"""
            <tr class="border border-slate-300">
                <td class="p-2 border border-slate-300 font-mono font-bold text-center text-[#204768]">{r.folio}</td>
                <td class="p-2 border border-slate-300 font-mono text-center text-gray-500">{r.hora}</td>
                <td class="p-2 border border-slate-300 font-mono font-semibold">{r.proceso}/{r.anio}</td>
                <td class="p-2 border border-slate-300 text-gray-700">{j_desc}</td>
                <td class="p-2 border border-slate-300 font-bold text-slate-900">{r.nombre}</td>
                <td class="p-2 border border-slate-300 text-gray-600">{r.delito}</td>
                <td class="p-2 border border-slate-300 font-bold text-center text-[#204768]">{s_desc}</td>
                <td class="p-2 border border-slate-300 h-12 text-center align-bottom text-[9px] text-gray-400">
                    ___________________<br>Sello y Firma
                </td>
            </tr>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Reporte de Entrega a Salas Penales - {hoy}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            @media print {{ 
                .no-print {{ display: none; }} 
                body {{ padding: 0; margin: 0; }}
            }}
        </style>
    </head>
    <body class="bg-white p-8 text-xs text-slate-900 max-w-7xl mx-auto">
        <div class="flex justify-between items-start border-b border-gray-400 pb-4 mb-4">
            <div class="flex items-center gap-3">
                <img src="/static/logo2.png" style="height: 42px;" onerror="this.style.display='none'">
                <div>
                    <h2 class="text-sm font-bold text-[#204768] tracking-tight">TRIBUNAL SUPERIOR DE JUSTICIA DEL ESTADO DE PUEBLA</h2>
                    <h4 class="text-xs font-semibold text-slate-700">OFICIALÍA COMÚN DE SALAS PENALES — RELACIÓN DE ENTREGA DE TOCAS</h4>
                </div>
            </div>
            <div class="text-right">
                <div class="font-mono text-xs font-bold text-slate-800">FECHA DE CORTE: {hoy}</div>
                <form method="get" action="/reporte_entrega" class="no-print mt-1 flex items-center justify-end gap-1">
                    <input type="date" name="fecha_rep" value="{hoy}" class="border border-gray-300 rounded px-1.5 py-0.5 text-[11px] font-mono">
                    <button type="submit" class="bg-slate-200 px-2 py-0.5 rounded text-[11px] font-semibold hover:bg-slate-300">Cambiar</button>
                </form>
            </div>
        </div>

        <div class="no-print flex justify-end gap-3 mb-4">
            <button onclick="window.print()" class="bg-[#204768] hover:bg-[#183650] text-white font-semibold px-4 py-1.5 rounded transition shadow-sm">
                🖨️ Imprimir Acta de Entrega
            </button>
            <a href="/" class="border border-gray-300 px-3.5 py-1.5 rounded hover:bg-gray-50 font-semibold transition">
                Volver
            </a>
        </div>

        <table class="w-full text-left border-collapse border border-slate-400">
            <thead>
                <tr class="bg-slate-100 text-[#204768] font-bold text-[10px] uppercase tracking-wider">
                    <th class="p-2 border border-slate-400 w-12 text-center">Folio</th>
                    <th class="p-2 border border-slate-400 w-16 text-center">Hora</th>
                    <th class="p-2 border border-slate-400 w-24">Expediente</th>
                    <th class="p-2 border border-slate-400">Juzgado de Procedencia</th>
                    <th class="p-2 border border-slate-400">Sentenciado / Imputado</th>
                    <th class="p-2 border border-slate-400">Delito(s)</th>
                    <th class="p-2 border border-slate-400 w-28 text-center">Sala Turnada</th>
                    <th class="p-2 border border-slate-400 w-40 text-center">Firma / Acuse de Recepción</th>
                </tr>
            </thead>
            <tbody>
                {filas if filas else f'<tr><td colspan="8" class="text-center p-8 text-gray-400">Sin tocas turnadas para entrega física a Salas Penales el {hoy}.</td></tr>'}
            </tbody>
        </table>

        <div class="mt-12 pt-4 flex justify-around text-center text-xs text-gray-700 font-semibold">
            <div class="w-64 border-t border-black pt-2">
                ENTREGA: OFICIALÍA DE SALAS PENALES<br>
                <span class="font-mono text-[10px] text-gray-500 font-normal">Firma del Funcionario</span>
            </div>
            <div class="w-64 border-t border-black pt-2">
                RECIBE: SALA PENAL ASIGNADA<br>
                <span class="font-mono text-[10px] text-gray-500 font-normal">Sello de Recibido y Hora</span>
            </div>
        </div>
    </body>
    </html>
    """


# --- BOLETA OFICIAL PENAL ---
@app.get("/imprimir_boleta/{folio}", response_class=HTMLResponse)
def imprimir_boleta(folio: int, sicop_usr: str = Cookie(None)):
    usr_activo = validar_sesion(sicop_usr)
    if not usr_activo:
        return RedirectResponse(url="/login", status_code=303)

    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT a.*, s.descrip AS desc_sala, j.descrip AS desc_juzg
            FROM apelaciones_penal a
            LEFT JOIN salas s ON a.sala = s.id_sala
            LEFT JOIN juzgados j ON a.juzgado = j.id_juzgado
            WHERE a.folio = :f
        """), {"f": folio}).fetchone()
        
        if not r: 
            return "Folio penal no encontrado"
        
        sala_fmt = formatear_nombre_sala(r.sala, r.desc_sala)
        juzg_fmt = formatear_nombre_juzgado(r.juzgado, r.desc_juzg)
        persona_lbl = "SENTENCIADO" if r.tipo_apela == 'S' else "IMPUTADO"
        cuerpo = f"""
        <b>EXPEDIENTE:</b> {r.proceso}/{r.anio} {f'(Acum: {r.acum})' if r.acum else ''}<br>
        <b>PROCEDENCIA:</b> {juzg_fmt}<br>
        <b>NATURALEZA:</b> {'SENTENCIA' if r.tipo_apela == 'S' else 'AUTO'} - {r.tipo or ''}<br>
        <b>{persona_lbl}:</b> {r.nombre}<br>
        <b>DELITO(S):</b> {r.delito}<br>
        <b>ANEXOS:</b> {r.anexos or 'NINGUNO'}<br>
        <div class="box-dest">{sala_fmt}</div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Boleta Oficial - Folio {r.folio}</title>
        <style>
            body {{ font-family: 'Courier New', Courier, monospace; width: 550px; margin: 20px auto; border: 1.5px solid #000; padding: 16px; background-color: #fff; }}
            .center {{ text-align: center; }}
            .box-dest {{ border: 2px solid #000; font-size: 18px; font-weight: bold; text-align: center; padding: 8px; margin: 12px 0; }}
            @media print {{ .no-print {{ display: none; }} body {{ border: none; margin: 0; width: 100%; }} }}
        </style>
    </head>
    <body>
        <div class="center">
            <img src="/static/logo2.png" style="height: 45px; margin-bottom: 4px;" onerror="this.style.display='none'"><br>
            <b>TRIBUNAL SUPERIOR DE JUSTICIA DE PUEBLA</b><br>
            OFICIALÍA COMÚN DE SALAS PENALES - TURNO DE APELACIÓN
        </div>
        <hr style="border-top: 1px solid #000; margin: 10px 0;">
        <b>FOLIO_A:</b> {r.folio} &nbsp;&nbsp;&nbsp;&nbsp; <b>FECHA/HORA:</b> {r.fecha} {r.hora}<br>
        {cuerpo}
        <br><br>
        <div style="display: flex; justify-content: space-between; text-align: center; font-size: 11px;">
            <div style="border-top: 1px solid #000; width: 42%;">RECIBIÓ OFICIALÍA</div>
            <div style="border-top: 1px solid #000; width: 42%;">RECIBIÓ {sala_fmt.upper()}</div>
        </div>
    </body>
    </html>
    """