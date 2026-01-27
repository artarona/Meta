# ========== GESTIÓN DE ESTADOS Y SESIONES ==========
"""
Manejo de sesiones de usuario y máquina de estados
"""

import time
from datetime import datetime
from config import Estados, SESSION_TIMEOUT

# ========== ALMACÉN DE SESIONES ==========
# En producción, usar Redis o base de datos
user_sessions = {}

def get_session(phone_number: str) -> dict:
    """Obtiene o crea una sesión para el usuario"""
    now = time.time()

    if phone_number in user_sessions:
        session = user_sessions[phone_number]
        # Verificar si la sesión expiró
        if now - session.get("last_activity", 0) > SESSION_TIMEOUT:
            # Sesión expirada, reiniciar
            session = create_new_session(phone_number)
        else:
            session["last_activity"] = now
    else:
        session = create_new_session(phone_number)

    user_sessions[phone_number] = session
    return session

def create_new_session(phone_number: str) -> dict:
    """Crea una nueva sesión limpia"""
    return {
        "phone": phone_number,
        "estado": Estados.INICIO,
        "created_at": time.time(),
        "last_activity": time.time(),
        "datos": {
            "operacion": None,
            "tipo_inmueble": None,
            "zona": None,
            "zona_nombre": None,
            "ambientes": None,
            "presupuesto": None,
            "presupuesto_rango": None,
            "urgencia": None,
            "caracteristicas": [],
            # Datos de tasación
            "tasacion_direccion": None,
            "tasacion_tipo": None,
            "tasacion_m2": None,
            "tasacion_antiguedad": None,
        },
        "historial": [],  # Historial de interacciones
    }

def update_session(phone_number: str, estado: str = None, datos: dict = None) -> dict:
    """Actualiza el estado y/o datos de una sesión"""
    session = get_session(phone_number)

    if estado:
        # Guardar en historial antes de cambiar
        session["historial"].append({
            "estado_anterior": session["estado"],
            "estado_nuevo": estado,
            "timestamp": datetime.now().isoformat()
        })
        session["estado"] = estado

    if datos:
        session["datos"].update(datos)

    session["last_activity"] = time.time()
    user_sessions[phone_number] = session
    return session

def reset_session(phone_number: str) -> dict:
    """Reinicia la sesión del usuario"""
    session = create_new_session(phone_number)
    user_sessions[phone_number] = session
    return session

def get_all_sessions() -> dict:
    """Retorna todas las sesiones activas (para debug/admin)"""
    return user_sessions

def get_session_summary(phone_number: str) -> str:
    """Genera un resumen de la sesión actual"""
    session = get_session(phone_number)
    datos = session["datos"]

    resumen_partes = []

    if datos["operacion"]:
        resumen_partes.append(f"Operación: {datos['operacion']}")
    if datos["tipo_inmueble"]:
        resumen_partes.append(f"Tipo: {datos['tipo_inmueble']}")
    if datos["zona_nombre"]:
        resumen_partes.append(f"Zona: {datos['zona_nombre']}")
    if datos["ambientes"]:
        resumen_partes.append(f"Ambientes: {datos['ambientes']}")
    if datos["presupuesto_rango"]:
        resumen_partes.append(f"Presupuesto: {datos['presupuesto_rango']}")
    if datos["urgencia"]:
        resumen_partes.append(f"Urgencia: {datos['urgencia']}")
    if datos["caracteristicas"]:
        resumen_partes.append(f"Extras: {', '.join(datos['caracteristicas'])}")

    return "\n".join(resumen_partes) if resumen_partes else "Sin datos aún"

def cleanup_expired_sessions():
    """Limpia sesiones expiradas"""
    now = time.time()
    expired = []

    for phone, session in user_sessions.items():
        if now - session.get("last_activity", 0) > SESSION_TIMEOUT:
            expired.append(phone)

    for phone in expired:
        del user_sessions[phone]

    return len(expired)
