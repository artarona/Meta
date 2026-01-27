# ========== MANEJADORES DE ESTADOS ==========
"""
Lógica de procesamiento para cada estado del flujo
"""

from config import (
    Estados, OPERACIONES, TIPOS_INMUEBLE, ZONAS, AMBIENTES,
    PRESUPUESTO_COMPRA, PRESUPUESTO_ALQUILER, URGENCIA, CARACTERISTICAS
)
from states import get_session, update_session, reset_session, get_session_summary
from messages import (
    msg_bienvenida, msg_operacion_seleccionada, msg_tipo_seleccionado,
    msg_zona_seleccionada, msg_zona_otra, msg_ambientes_seleccionados,
    msg_presupuesto_seleccionado, msg_urgencia_seleccionada, msg_resumen,
    msg_confirmacion_final, msg_opcion_invalida, msg_error_generico,
    msg_ayuda, msg_agente_humano,
    msg_tasacion_inicio, msg_tasacion_tipo, msg_tasacion_m2,
    msg_tasacion_antiguedad, msg_tasacion_resumen
)

def procesar_mensaje(phone_number: str, mensaje: str) -> str:
    """
    Procesa un mensaje entrante y retorna la respuesta apropiada.
    Este es el punto de entrada principal del flujo conversacional.
    """
    mensaje = mensaje.strip()
    mensaje_lower = mensaje.lower()

    # ========== COMANDOS GLOBALES ==========
    if mensaje_lower in ["hola", "hi", "hello", "inicio", "empezar", "start"]:
        reset_session(phone_number)
        return msg_bienvenida()

    if mensaje_lower in ["reiniciar", "reset", "volver"]:
        reset_session(phone_number)
        return "🔄 Sesión reiniciada.\n\n" + msg_bienvenida()

    if mensaje_lower in ["ayuda", "help", "?"]:
        return msg_ayuda()

    if mensaje_lower in ["agente", "humano", "persona", "asesor"]:
        update_session(phone_number, estado=Estados.AGENTE_HUMANO)
        return msg_agente_humano()

    if mensaje_lower in ["estado", "status", "mi busqueda"]:
        resumen = get_session_summary(phone_number)
        return f"📋 *Tu búsqueda actual:*\n\n{resumen}"

    # ========== OBTENER SESIÓN Y ESTADO ==========
    session = get_session(phone_number)
    estado_actual = session["estado"]

    # ========== ENRUTAR SEGÚN ESTADO ==========
    handlers = {
        Estados.INICIO: handle_inicio,
        Estados.OPERACION: handle_operacion,
        Estados.TIPO_INMUEBLE: handle_tipo_inmueble,
        Estados.ZONA: handle_zona,
        Estados.ZONA_OTRA: handle_zona_otra,
        Estados.AMBIENTES: handle_ambientes,
        Estados.PRESUPUESTO: handle_presupuesto,
        Estados.URGENCIA: handle_urgencia,
        Estados.CARACTERISTICAS: handle_caracteristicas,
        Estados.RESUMEN: handle_resumen,
        Estados.CONFIRMACION: handle_confirmacion,
        # Tasación
        Estados.TASACION_DIRECCION: handle_tasacion_direccion,
        Estados.TASACION_TIPO: handle_tasacion_tipo,
        Estados.TASACION_M2: handle_tasacion_m2,
        Estados.TASACION_ANTIGUEDAD: handle_tasacion_antiguedad,
        Estados.TASACION_RESUMEN: handle_tasacion_resumen,
        # Finalizados
        Estados.FINALIZADO: handle_finalizado,
        Estados.AGENTE_HUMANO: handle_agente_humano,
    }

    handler = handlers.get(estado_actual, handle_default)
    return handler(phone_number, mensaje, session)

# ========== HANDLERS INDIVIDUALES ==========

def handle_inicio(phone_number: str, mensaje: str, session: dict) -> str:
    """Estado inicial - mostrar bienvenida y esperar operación"""
    update_session(phone_number, estado=Estados.OPERACION)
    return msg_bienvenida()

def handle_operacion(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de operación"""
    mensaje = mensaje.strip()

    if mensaje not in OPERACIONES:
        return msg_opcion_invalida("1-4")

    operacion = OPERACIONES[mensaje]

    # Si es tasación, ir a flujo especial
    if operacion["id"] == "tasacion":
        update_session(
            phone_number,
            estado=Estados.TASACION_DIRECCION,
            datos={"operacion": operacion["nombre"]}
        )
        return msg_tasacion_inicio()

    # Guardar operación y avanzar a tipo de inmueble
    update_session(
        phone_number,
        estado=Estados.TIPO_INMUEBLE,
        datos={"operacion": operacion["nombre"]}
    )
    return msg_operacion_seleccionada(operacion)

def handle_tipo_inmueble(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de tipo de inmueble"""
    mensaje = mensaje.strip()

    if mensaje not in TIPOS_INMUEBLE:
        return msg_opcion_invalida("1-5")

    tipo = TIPOS_INMUEBLE[mensaje]
    update_session(
        phone_number,
        estado=Estados.ZONA,
        datos={"tipo_inmueble": tipo["nombre"]}
    )
    return msg_tipo_seleccionado(tipo)

def handle_zona(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de zona"""
    mensaje = mensaje.strip()

    if mensaje not in ZONAS:
        return msg_opcion_invalida("1-9")

    zona = ZONAS[mensaje]

    # Si elige "Otra zona", pedir que especifique
    if zona["id"] == "otra":
        update_session(phone_number, estado=Estados.ZONA_OTRA)
        return msg_zona_otra()

    tipo_inmueble = session["datos"].get("tipo_inmueble", "").lower()

    update_session(
        phone_number,
        estado=Estados.AMBIENTES,
        datos={"zona": zona["id"], "zona_nombre": zona["nombre"]}
    )
    return msg_zona_seleccionada(zona["nombre"], tipo_inmueble)

def handle_zona_otra(phone_number: str, mensaje: str, session: dict) -> str:
    """Capturar zona personalizada"""
    zona_custom = mensaje.strip().title()

    if len(zona_custom) < 3:
        return "⚠️ Por favor, escribí el nombre del barrio o zona."

    tipo_inmueble = session["datos"].get("tipo_inmueble", "").lower()

    update_session(
        phone_number,
        estado=Estados.AMBIENTES,
        datos={"zona": "otra", "zona_nombre": zona_custom}
    )
    return msg_zona_seleccionada(zona_custom, tipo_inmueble)

def handle_ambientes(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de ambientes"""
    mensaje = mensaje.strip()

    if mensaje not in AMBIENTES:
        return msg_opcion_invalida("1-4")

    ambiente = AMBIENTES[mensaje]
    operacion = session["datos"].get("operacion", "").lower()
    es_compra = "compra" in operacion

    update_session(
        phone_number,
        estado=Estados.PRESUPUESTO,
        datos={"ambientes": ambiente["nombre"]}
    )
    return msg_ambientes_seleccionados(ambiente["nombre"], es_compra)

def handle_presupuesto(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de presupuesto"""
    mensaje = mensaje.strip()
    operacion = session["datos"].get("operacion", "").lower()
    es_compra = "compra" in operacion

    presupuestos = PRESUPUESTO_COMPRA if es_compra else PRESUPUESTO_ALQUILER

    if mensaje not in presupuestos:
        return msg_opcion_invalida("1-5" if es_compra else "1-4")

    presupuesto = presupuestos[mensaje]
    update_session(
        phone_number,
        estado=Estados.URGENCIA,
        datos={
            "presupuesto": presupuesto["id"],
            "presupuesto_rango": presupuesto["nombre"]
        }
    )
    return msg_presupuesto_seleccionado(presupuesto["nombre"])

def handle_urgencia(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de urgencia"""
    mensaje = mensaje.strip()

    if mensaje not in URGENCIA:
        return msg_opcion_invalida("1-4")

    urgencia = URGENCIA[mensaje]
    update_session(
        phone_number,
        estado=Estados.CARACTERISTICAS,
        datos={"urgencia": urgencia["nombre"]}
    )
    return msg_urgencia_seleccionada(urgencia["nombre"])

def handle_caracteristicas(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar selección de características (puede ser múltiple)"""
    mensaje = mensaje.strip().replace(" ", "")

    # Parsear múltiples opciones (ej: "1,3,4" o "1 3 4" o "134")
    opciones = []
    if "," in mensaje:
        opciones = [x.strip() for x in mensaje.split(",")]
    elif len(mensaje) > 1 and mensaje.isdigit():
        opciones = list(mensaje)
    else:
        opciones = [mensaje]

    # Validar opciones
    caracteristicas_seleccionadas = []
    for opcion in opciones:
        if opcion == "0":
            caracteristicas_seleccionadas = []
            break
        if opcion in CARACTERISTICAS:
            caracteristicas_seleccionadas.append(CARACTERISTICAS[opcion]["nombre"])

    update_session(
        phone_number,
        estado=Estados.RESUMEN,
        datos={"caracteristicas": caracteristicas_seleccionadas}
    )

    # Obtener datos actualizados para el resumen
    session = get_session(phone_number)
    return msg_resumen(session["datos"])

def handle_resumen(phone_number: str, mensaje: str, session: dict) -> str:
    """Procesar confirmación del resumen"""
    mensaje = mensaje.strip()

    if mensaje == "1":
        # Confirmar y finalizar
        update_session(phone_number, estado=Estados.FINALIZADO)
        # Aquí podrías guardar en base de datos / CRM
        guardar_lead(session)
        return msg_confirmacion_final()

    elif mensaje == "2":
        # Modificar - volver al inicio del flujo
        update_session(phone_number, estado=Estados.OPERACION)
        return "✏️ Vamos a modificar tu búsqueda.\n\n" + msg_bienvenida()

    elif mensaje == "3":
        # Empezar de nuevo
        reset_session(phone_number)
        return "🔄 Empezamos de nuevo.\n\n" + msg_bienvenida()

    return msg_opcion_invalida("1-3")

def handle_confirmacion(phone_number: str, mensaje: str, session: dict) -> str:
    """Confirmación final"""
    return msg_confirmacion_final()

# ========== HANDLERS DE TASACIÓN ==========

def handle_tasacion_direccion(phone_number: str, mensaje: str, session: dict) -> str:
    """Capturar dirección para tasación"""
    direccion = mensaje.strip()

    if len(direccion) < 10:
        return "⚠️ Por favor, escribí la dirección completa (calle, número, barrio)."

    update_session(
        phone_number,
        estado=Estados.TASACION_TIPO,
        datos={"tasacion_direccion": direccion}
    )
    return msg_tasacion_tipo()

def handle_tasacion_tipo(phone_number: str, mensaje: str, session: dict) -> str:
    """Tipo de propiedad para tasación"""
    tipos = {"1": "Departamento", "2": "Casa", "3": "PH", "4": "Local comercial", "5": "Oficina", "6": "Terreno"}
    mensaje = mensaje.strip()

    if mensaje not in tipos:
        return msg_opcion_invalida("1-6")

    update_session(
        phone_number,
        estado=Estados.TASACION_M2,
        datos={"tasacion_tipo": tipos[mensaje]}
    )
    return msg_tasacion_m2()

def handle_tasacion_m2(phone_number: str, mensaje: str, session: dict) -> str:
    """Metros cuadrados para tasación"""
    mensaje = mensaje.strip().replace("m2", "").replace("m²", "").strip()

    try:
        m2 = int(mensaje)
        if m2 < 10 or m2 > 50000:
            return "⚠️ Por favor, ingresá un número válido de metros cuadrados."
    except ValueError:
        return "⚠️ Por favor, escribí solo el número (ej: 65)."

    update_session(
        phone_number,
        estado=Estados.TASACION_ANTIGUEDAD,
        datos={"tasacion_m2": m2}
    )
    return msg_tasacion_antiguedad()

def handle_tasacion_antiguedad(phone_number: str, mensaje: str, session: dict) -> str:
    """Antigüedad para tasación"""
    antiguedades = {"1": "A estrenar", "2": "Hasta 10 años", "3": "10-30 años", "4": "Más de 30 años"}
    mensaje = mensaje.strip()

    if mensaje not in antiguedades:
        return msg_opcion_invalida("1-4")

    update_session(
        phone_number,
        estado=Estados.TASACION_RESUMEN,
        datos={"tasacion_antiguedad": antiguedades[mensaje]}
    )

    session = get_session(phone_number)
    return msg_tasacion_resumen(session["datos"])

def handle_tasacion_resumen(phone_number: str, mensaje: str, session: dict) -> str:
    """Confirmación de tasación"""
    mensaje = mensaje.strip()

    if mensaje == "1":
        update_session(phone_number, estado=Estados.FINALIZADO)
        guardar_lead_tasacion(session)
        return """✅ *¡Solicitud enviada!*

Un tasador profesional analizará tu propiedad y te contactará en las próximas 24-48 horas hábiles.

¿Necesitás algo más? Escribí *"hola"* para una nueva consulta."""

    elif mensaje == "2":
        update_session(phone_number, estado=Estados.TASACION_DIRECCION)
        return "✏️ Vamos a corregir los datos.\n\n" + msg_tasacion_inicio()

    elif mensaje == "3":
        reset_session(phone_number)
        return "🔄 Solicitud cancelada.\n\n" + msg_bienvenida()

    return msg_opcion_invalida("1-3")

# ========== HANDLERS FINALES ==========

def handle_finalizado(phone_number: str, mensaje: str, session: dict) -> str:
    """Usuario ya finalizó el flujo"""
    mensaje_lower = mensaje.lower()

    if any(x in mensaje_lower for x in ["hola", "nueva", "otro", "buscar"]):
        reset_session(phone_number)
        return msg_bienvenida()

    return """👋 ¡Tu búsqueda ya fue registrada!

¿Querés hacer otra consulta? Escribí *"hola"* para empezar.

O escribí *"agente"* para hablar con una persona."""

def handle_agente_humano(phone_number: str, mensaje: str, session: dict) -> str:
    """Usuario pidió agente humano"""
    return msg_agente_humano()

def handle_default(phone_number: str, mensaje: str, session: dict) -> str:
    """Handler por defecto para estados no reconocidos"""
    reset_session(phone_number)
    return msg_error_generico() + "\n\n" + msg_bienvenida()

# ========== FUNCIONES DE PERSISTENCIA ==========

def guardar_lead(session: dict):
    """
    Guarda el lead en base de datos / CRM.
    Implementar según tu sistema.
    """
    datos = session["datos"]
    phone = session["phone"]

    lead = {
        "telefono": phone,
        "operacion": datos.get("operacion"),
        "tipo_inmueble": datos.get("tipo_inmueble"),
        "zona": datos.get("zona_nombre"),
        "ambientes": datos.get("ambientes"),
        "presupuesto": datos.get("presupuesto_rango"),
        "urgencia": datos.get("urgencia"),
        "caracteristicas": datos.get("caracteristicas", []),
        "timestamp": session.get("created_at"),
    }

    # TODO: Implementar guardado en DB
    # - SQLite / PostgreSQL
    # - Google Sheets
    # - CRM (HubSpot, Salesforce, etc.)
    # - Webhook a tu sistema

    print(f"💾 NUEVO LEAD: {lead}")
    return lead

def guardar_lead_tasacion(session: dict):
    """Guarda solicitud de tasación"""
    datos = session["datos"]
    phone = session["phone"]

    lead = {
        "telefono": phone,
        "tipo": "TASACION",
        "direccion": datos.get("tasacion_direccion"),
        "tipo_propiedad": datos.get("tasacion_tipo"),
        "metros": datos.get("tasacion_m2"),
        "antiguedad": datos.get("tasacion_antiguedad"),
        "timestamp": session.get("created_at"),
    }

    print(f"💾 NUEVA TASACIÓN: {lead}")
    return lead
