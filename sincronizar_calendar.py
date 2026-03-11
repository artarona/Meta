# -*- coding: utf-8 -*-
"""
sincronizar_calendar.py
=======================
Sincroniza las citas de PostgreSQL con Google Calendar.

Uso:
    python sincronizar_calendar.py

Que hace:
  1. Lee todas las citas activas (no canceladas) de la DB
  2. Busca en Google Calendar si ya existe un evento para cada cita
     (usando extendedProperties.private.cita_id)
  3. Si NO existe -> lo crea
  4. Si YA existe -> lo verifica
  5. Muestra resumen final
"""

import io
import os
import sys
import time
from datetime import datetime, timedelta

# Forzar UTF-8 en la consola de Windows para evitar UnicodeEncodeError
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

# ── Google Calendar ───────────────────────────────────────────────────────────
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES               = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "google_calendar_key.json"
CALENDAR_ID          = "rentaloficinas@gmail.com"
TIMEZONE             = "America/Argentina/Buenos_Aires"

# ── PostgreSQL ────────────────────────────────────────────────────────────────
try:
    import psycopg2
except ImportError:
    print("[ERROR] psycopg2 no instalado. Ejecuta: pip install psycopg2-binary")
    sys.exit(1)


# =============================================================================
# HELPERS
# =============================================================================

def get_calendar_service():
    """Devuelve el servicio autenticado de Google Calendar.
    Compatible con local (JSON file) y Render (GOOGLE_CALENDAR_KEY_B64 env var).
    """
    import json, base64 as b64
    creds_data = None

    # Opcion 1: archivo local
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            with open(SERVICE_ACCOUNT_FILE, "r") as f:
                creds_data = json.load(f)
        except Exception as e:
            print(f"[WARN] No se pudo leer {SERVICE_ACCOUNT_FILE}: {e}")

    # Opcion 2: variable de entorno base64 (Render)
    if not creds_data:
        key_b64 = os.environ.get("GOOGLE_CALENDAR_KEY_B64")
        if key_b64:
            try:
                creds_data = json.loads(b64.b64decode(key_b64).decode("utf-8"))
            except Exception as e:
                print(f"[ERROR] No se pudo decodificar GOOGLE_CALENDAR_KEY_B64: {e}")
                sys.exit(1)

    if not creds_data:
        print(f"[ERROR] No se encontro {SERVICE_ACCOUNT_FILE} ni la variable GOOGLE_CALENDAR_KEY_B64")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_info(
        creds_data, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_db_connection(max_retries=5):
    """Obtiene conexión a PostgreSQL con reintentos y sanitización de URL"""
    import re
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL no encontrada en .env")
        sys.exit(1)

    # Extraer estrictamente la URL
    match = re.search(r'(postgres|postgresql)://\S+', database_url)
    if match:
        database_url = match.group(0).strip()
    else:
        print(f"[ERROR] No se pudo encontrar una URL de DB en: {database_url}")
        sys.exit(1)
        
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                database_url,
                sslmode='require',
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                options='-c statement_timeout=30000'
            )
            return conn
            
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            error_str = str(e)
            if "SSL connection has been closed unexpectedly" in error_str or "connection to server at" in error_str:
                print(f"[WARN] Error de conexión (Intento {i+1}/{max_retries}): {error_str}")
                if i < max_retries - 1:
                    time.sleep(2)
                    continue
            print(f"[ERROR] Error fatal conectando a PostgreSQL: {e}")
            break
        except Exception as e:
            print(f"[ERROR] Error inesperado conectando a PostgreSQL: {e}")
            break
            
    sys.exit(1)


def fetch_citas_activas(conn):
    """Obtiene todas las citas activas (no canceladas) con fecha y hora."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, nombre, email, telefono,
                   fecha_cita, hora_cita, propiedad_id, estado, notas
            FROM citas
            WHERE estado IS DISTINCT FROM 'cancelada'
              AND fecha_cita IS NOT NULL
              AND hora_cita IS NOT NULL
            ORDER BY fecha_cita, hora_cita
        """)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_event_body(cita: dict) -> dict:
    """Construye el body del evento de Google Calendar."""
    fecha    = cita["fecha_cita"]   # objeto date
    hora_str = cita["hora_cita"]    # "HH:MM"
    nombre   = cita.get("nombre")   or "Sin nombre"
    tel      = cita.get("telefono") or "Sin telefono"
    prop     = cita.get("propiedad_id") or "Sin propiedad"
    estado   = cita.get("estado")   or "pendiente"
    notas    = cita.get("notas")    or ""
    cita_id  = cita["id"]

    hora_h, hora_m = map(int, hora_str.split(":"))
    dt_start = datetime(fecha.year, fecha.month, fecha.day, hora_h, hora_m)
    dt_end   = dt_start + timedelta(hours=1)

    descripcion = (
        f"Cliente: {nombre}\n"
        f"Telefono: {tel}\n"
        f"Propiedad: {prop}\n"
        f"Estado: {estado}\n"
    )
    if notas:
        descripcion += f"Notas: {notas}\n"
    descripcion += f"\n[cita_id: {cita_id}]"

    return {
        "summary": f"Visita - {nombre} - {prop}",
        "description": descripcion,
        "start": {
            "dateTime": dt_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": dt_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": TIMEZONE,
        },
        "extendedProperties": {
            "private": {
                "cita_id": str(cita_id),
                "fuente":   "dante_bot"
            }
        },
    }


def find_existing_event(service, cita_id: int):
    """
    Busca en Google Calendar si ya existe un evento para la cita.
    Usa extendedProperties.private.cita_id como identificador unico.
    """
    try:
        result = service.events().list(
            calendarId=CALENDAR_ID,
            privateExtendedProperty=f"cita_id={cita_id}",
            singleEvents=True,
            maxResults=5,
        ).execute()
        items = result.get("items", [])
        return items[0] if items else None
    except Exception as e:
        print(f"  [WARN] Error buscando evento para cita {cita_id}: {e}")
        return None


def create_event(service, body: dict) -> dict:
    """Crea un evento en Google Calendar."""
    return service.events().insert(
        calendarId=CALENDAR_ID,
        body=body
    ).execute()


# =============================================================================
# MAIN
# =============================================================================

def main():
    sep = "=" * 60
    print(sep)
    print("SINCRONIZACION CITAS -> GOOGLE CALENDAR")
    print(f"Calendario: {CALENDAR_ID}")
    print(sep)

    # 1. Conectar
    print("\n[INFO] Conectando a PostgreSQL y Google Calendar...")
    conn    = get_db_connection()
    service = get_calendar_service()
    print("[OK] Conexiones establecidas")

    # 2. Obtener citas
    citas = fetch_citas_activas(conn)
    conn.close()
    print(f"\n[INFO] Citas activas en DB: {len(citas)}")

    if not citas:
        print("\n[AVISO] No hay citas activas para sincronizar.")
        return

    # 3. Procesar
    print("\n" + "-" * 60)
    stats = {"creadas": 0, "ya_existian": 0, "errores": 0}

    for cita in citas:
        cita_id = cita["id"]
        nombre  = cita.get("nombre") or "Sin nombre"
        fecha   = cita["fecha_cita"]
        hora    = cita["hora_cita"]
        prop    = cita.get("propiedad_id") or "?"

        print(f"\n[>>] Cita #{cita_id} | {nombre} | {fecha} {hora} | {prop}")

        try:
            existing = find_existing_event(service, cita_id)

            if existing:
                event_url = existing.get("htmlLink", "(sin URL)")
                print(f"  [OK] Ya existe en Calendar -> {event_url}")
                stats["ya_existian"] += 1
            else:
                body    = build_event_body(cita)
                created = create_event(service, body)
                print(f"  [CREADO] -> {created.get('htmlLink', '(sin URL)')}")
                stats["creadas"] += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            stats["errores"] += 1

    # 4. Resumen
    total = stats["creadas"] + stats["ya_existian"] + stats["errores"]
    print("\n" + sep)
    print("RESUMEN")
    print(f"  Eventos creados:    {stats['creadas']}")
    print(f"  Ya existian:        {stats['ya_existian']}")
    print(f"  Errores:            {stats['errores']}")
    print(f"  Total procesadas:   {total} / {len(citas)}")
    print(sep)

    if stats["errores"] == 0:
        print("\n[OK] Sincronizacion completada sin errores.")
    else:
        print("\n[AVISO] Hubo errores. Revisa los detalles arriba.")


if __name__ == "__main__":
    main()
