import json
from config import *
from utils import log, normalizar_numero_argentina
from database import obtener_estado_usuario, actualizar_estado_usuario, guardar_en_postgresql
from logic.response_builder import WhatsAppResponse
from whatsapp_api import notificar_agente

# ========== CONSTANTES DE BRANDING ==========
LOGO = "🏠🗝️"
MARCA = f"{LOGO} *DANTE PROPIEDADES*"
DESPEDIDA = f"¡Gracias por confiar en Dante Propiedades! {LOGO}"
PIE_MENU = "Dante Propiedades · Tu lugar ideal"
PIE_SELECCION= "Selecciona una opción 👇"
HINT_SALIR = "\n\n💡 _Envía '*S*' para salir o '*M*' para volver al menú._"

# ========== CONSTANTES PARA QUIERO VENDER ==========
VENDER_OPCIONES = {
    "1": {"id": "vender_datos", "titulo": "📇 Datos de contacto"},
    "2": {"id": "vender_documentacion", "titulo": "📄 Documentación"},
    "3": {"id": "vender_detalles", "titulo": "📐 Detalles técnicos"},
    "4": {"id": "vender_ocupacion", "titulo": "🚪 Estado de ocupación"},
    "5": {"id": "vender_precio", "titulo": "💰 Precio pretendido"},
    "6": {"id": "vender_disponibilidad", "titulo": "📅 Disponibilidad para visita"}
}

# Mapeo para números (FB/IG)
VENDER_NUMEROS = {
    "1": "vender_datos",
    "2": "vender_documentacion",
    "3": "vender_detalles",
    "4": "vender_ocupacion",
    "5": "vender_precio",
    "6": "vender_disponibilidad"
}



# ========== HELPERS PARA DATA DE CAMPAÑA ==========
# Usamos estado_usuario['data']['campana'] porque 'data' es el único
# campo JSON que se persiste en la tabla user_states de PostgreSQL.
# Usar una clave separada como 'data_campana' causa que se pierda
# entre requests cuando la DB es la fuente de verdad.

def _get_campana_data(estado_usuario):
    """Obtiene los datos de campaña desde el campo persistido 'data'"""
    if not isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data'] = {}
    return estado_usuario['data'].get('campana', {})

def _set_campana_data(estado_usuario, campana_data):
    """Guarda los datos de campaña dentro del campo persistido 'data'"""
    if not isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data'] = {}
    estado_usuario['data']['campana'] = campana_data

def _clear_campana_data(estado_usuario):
    """Limpia los datos de campaña"""
    if isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data']['campana'] = {}


def get_bot_response_campana(text, user_id):
    """
    Despachador principal para el MODO CAMPAÑA (TIPO_MENU = 1).
    """
    text_lower = text.lower().strip()
    
    # Obtener estado del usuario SIEMPRE fresco
    estado_usuario = obtener_estado_usuario(user_id)
    paso_actual = estado_usuario.get('paso', 'campana_inicio')
    
    # ✅ IMPORTANTE: Forzar obtener el platform NUEVAMENTE desde la DB
    from database import obtener_estado_usuario as get_fresh_state
    fresh_state = get_fresh_state(user_id)
    platform = fresh_state.get('platform') or estado_usuario.get('platform')
    
    # Log para depuración
    log(f"🔍 get_bot_response_campana - platform obtenido: '{platform}'")
    
    # Si aún no hay platform, intentar una última vez con una consulta directa
    if not platform:
        try:
            import psycopg2
            from config import DATABASE_URL
            
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT state FROM user_states WHERE user_id = %s", (str(user_id),))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row and row[0]:
                import json
                state_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                platform = state_data.get('platform')
                log(f"🔍 get_bot_response_campana - platform por consulta directa: '{platform}'")
        except Exception as e:
            log(f"⚠️ Error en consulta directa de platform: {e}")
    
    # ========== ✅ NUEVO: MANEJO DE NÚMEROS PARA FACEBOOK/INSTAGRAM ==========
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Si es FB/IG y el usuario está en el paso campana_intent, redirigir número a la intención
    if es_fb_ig and paso_actual == 'campana_intent' and text_lower in ["1", "2", "3", "4", "5"]:
        log(f"🔄 [FB/IG] Número recibido en menú principal: '{text_lower}' -> redirigiendo")
        return manejar_intencion_campana(text_lower, estado_usuario, user_id)
    
    # ========== COMANDOS GLOBALES ==========
    if text_lower in ["salir", "s", "exit", "0"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    
    if text_lower in ["menu", "m", "volver", "inicio", "hola", "hi", "hello", "atras"]:
        estado_usuario['paso'] = 'campana_intent'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana(platform)
    
    # MANEJO ESPECIAL PARA REINTENTAR TASACIÓN (ID 10)
    if text_lower == "10":
        from tasaciones import manejar_reintentar_tasacion
        return manejar_reintentar_tasacion(estado_usuario, user_id)
    
    # ========== ROUTING POR PASO ==========
    if paso_actual in ('campana_inicio', 'menu_principal'):
        estado_usuario['paso'] = 'campana_intent'
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana(platform)
        
    elif paso_actual == 'campana_intent':
        return manejar_intencion_campana(text_lower, estado_usuario, user_id)
        
    elif paso_actual.startswith('campana_recopilar_'):
        return manejar_recopilacion_datos(text, estado_usuario, user_id)
        
    elif paso_actual == 'campana_confirmacion':
        return manejar_confirmacion_campana(text_lower, estado_usuario, user_id)
        
    elif paso_actual == 'campana_pedir_nombre':
        return manejar_pedir_nombre_asesor(text, estado_usuario, user_id)
    
    # ========== VENDER - FLUJO SECUENCIAL (NUEVO) ==========
    elif paso_actual == 'vender_paso1_nombre':
        return manejar_vender_paso1_nombre(text, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso2_documentacion':
        return manejar_vender_paso2_documentacion(text_lower, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso3_detalles':
        return manejar_vender_paso3_detalles(text_lower, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso4_ocupacion':
        return manejar_vender_paso4_ocupacion(text_lower, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso5_precio':
        return manejar_vender_paso5_precio(text_lower, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso5_precio_valor_espera':
        return manejar_vender_paso5_precio_valor(text, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso6_disponibilidad':
        return manejar_vender_paso6_disponibilidad(text_lower, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso6_disponibilidad_otro':
        return manejar_vender_paso6_disponibilidad_otro(text, estado_usuario, user_id)
    
    # ========== TASACIÓN ==========
    elif paso_actual.startswith('tasacion_'):
        from tasaciones import (
            manejar_tasacion_operacion, manejar_tasacion_barrio_seleccion, 
            manejar_tasacion_tipo, manejar_tasacion_m2, 
            manejar_tasacion_estado, manejar_tasacion_contacto
        )
        resp = None
        if paso_actual == 'tasacion_operacion':
            resp = manejar_tasacion_operacion(text_lower, estado_usuario, user_id)
        elif paso_actual == 'tasacion_barrio_seleccion':
            resp = manejar_tasacion_barrio_seleccion(text, estado_usuario, user_id)
        elif paso_actual == 'tasacion_tipo':
            resp = manejar_tasacion_tipo(text_lower, estado_usuario, user_id)
        elif paso_actual == 'tasacion_m2':
            resp = manejar_tasacion_m2(text, estado_usuario, user_id)
        elif paso_actual == 'tasacion_estado':
            resp = manejar_tasacion_estado(text_lower, estado_usuario, user_id)
        elif paso_actual == 'tasacion_esperando_contacto':
            resp = manejar_tasacion_contacto(text_lower, estado_usuario, user_id)
            
        if resp == "WELCOME_FLOW_TRIGGER":
            estado_usuario['paso'] = 'campana_intent'
            actualizar_estado_usuario(user_id, estado_usuario)
            return iniciar_campana(platform)
        return resp

    # Fallback → menú principal
    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana(platform)

# ========== MENÚ PRINCIPAL DE CAMPAÑA ==========

def iniciar_campana(platform=None):
    """
    Muestra el menú principal adaptado a la plataforma.
    """
    es_fb_ig = False
    if platform:
        platform_lower = str(platform).lower()
        es_fb_ig = platform_lower in ("messenger", "facebook", "instagram")
    
    log(f"🔍 iniciar_campana - platform: '{platform}', es_fb_ig: {es_fb_ig}")
    
    cuerpo_base = (
        "¡Hola! 👋 Soy el asistente de Dante Propiedades 🏠🗝️.\n\n"
        "Estamos para acompañarte en todo el proceso de venta o tasación de tu propiedad.\n\n"
        "¿Te gustaría recibir una valoración gratuita o conocer las mejores oportunidades del mercado?\n\n"
        "Contame qué necesitás y te ayudo personalmente a avanzar."
    )
    
    if es_fb_ig:
        # Facebook/Instagram/Messenger: texto plano con números
        partes = [
            "¡Hola! 👋 Soy el asistente de Dante Propiedades 🏠🗝️",
            "Estamos para acompañarte en todo el proceso de venta o tasación de tu propiedad.\n"
            "¿Te gustaría recibir una valoración gratuita o conocer las mejores oportunidades del mercado?\n"
            "Contame qué necesitás y te ayudo personalmente a avanzar.",
            "",
            "*Servicios Disponibles*\n"
            "1️⃣ 📈 Tasación Virtual Inteligente - Obtené un valor estimado de tu propiedad en segundos.\n"
            "2️⃣ 🏡 Quiero Vender - Para propietarios que ya están decididos y quieren que publiques su propiedad.\n"
            "3️⃣ 🔑 Ver Propiedades Disponibles - Explorá nuestro catálogo actualizado en dantepropiedades.com.ar.\n"
            "4️⃣ 👤 Asesoramiento Inmobiliario - Para consultas sobre trámites, contratos o asesoría técnica.",
            "",
            "*Otras Opciones*\n"
            "5️⃣ ❌ Salir - Finalizar la conversación.",
            "",
            "💡 *Envía el número de la opción deseada* 👇"
        ]

        return [{"type": "text", "body": parte, "preview": False} for parte in partes if parte]

    else:
        # WhatsApp: lista interactiva
        rows = [
            {"id": "c_tasar", "title": "📈 Tasación Virtual Inteligente", "description": "Obtené un valor estimado de tu propiedad en segundos."},
            {"id": "c_comprar", "title": "🏡 Quiero Vender", "description": "Para propietarios que ya están decididos y quieren que publiques su propiedad."},
            {"id": "c_alquilar", "title": "🔑 Ver Propiedades Disponibles", "description": "Explorá nuestro catálogo actualizado en dantepropiedades.com.ar."},
            {"id": "c_asesor", "title": "👤 Asesoramiento Inmobiliario", "description": "Para consultas sobre trámites, contratos o asesoría técnica."}
        ]
        otras = [
            {"id": "c_salir", "title": "❌ Salir", "description": "Finalizar la conversación."}
        ]
        
        return WhatsAppResponse.list_menu(
            header=f"Dante Propiedades 🏠🗝️",
            body=cuerpo_base,
            button_text="Ver opciones",
            sections=[
                {"title": "Servicios Disponibles", "rows": rows},
                {"title": "Otras Opciones", "rows": otras}
            ],
            footer=PIE_MENU
        )
# ========== MANEJO DE INTENCIÓN ==========

def manejar_intencion_campana(text, estado_usuario, user_id):
    """Maneja la selección de intención en el menú principal de campaña"""
    _clear_campana_data(estado_usuario)
    data = {}
    
    # Obtener platform del estado
    platform = estado_usuario.get('platform')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    log(f"🔍 manejar_intencion_campana - platform: {platform}, es_fb_ig: {es_fb_ig}")
    
    # Normalizar el texto recibido
    text_normalized = text.lower().strip()
    
    # Mapeo de opciones numéricas SOLO para Facebook/Instagram
    if es_fb_ig:
        opciones_numericas = {
            "1": "c_comprar",
            "2": "c_alquilar",
            "3": "c_tasar",
            "4": "c_asesor",
            "5": "c_salir",
            "uno": "c_comprar",
            "dos": "c_alquilar",
            "tres": "c_tasar",
            "cuatro": "c_asesor",
            "cinco": "c_salir",
            "comprar": "c_comprar",
            "vender": "c_comprar",
            "alquilar": "c_alquilar",
            "tasar": "c_tasar",
            "asesor": "c_asesor",
            "asesoramiento": "c_asesor",
            "salir": "c_salir"
        }
        
        if text_normalized in opciones_numericas:
            text_normalized = opciones_numericas[text_normalized]
            log(f"🔄 Conversión numérica: '{text}' -> '{text_normalized}'")
    
    # ========== OPCIÓN 1: QUIERO VENDER ==========
    if text_normalized in ["c_comprar", "comprar", "vender", "quiero vender", "venta", "1"]:
        data['intencion'] = "Vender"
        estado_usuario['paso'] = 'vender_paso1_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Paso 1: Pedir nombre y horario
        return "📇 *Para comenzar, por favor confirmame tu nombre completo y un horario de preferencia para que Dante te llame.*\n\n_(Ej: Juan Pérez, después de las 15hs)_"
    
    
    
    # ========== OPCIÓN 2: VER PROPIEDADES DISPONIBLES ==========
    elif text_normalized in ["c_alquilar", "alquilar", "ver propiedades", "propiedades", "sitio web", "web", "catalogo", "2"]:
        sitio_web = "https://www.dantepropiedades.com.ar"
        
        cuerpo = f"🔍 *Catálogo de Propiedades*\n\nPodés explorar todas nuestras propiedades disponibles en nuestro sitio web:\n\n👉 {sitio_web}\n\n¿Necesitas ayuda con algo más?"
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[
                    {"id": "c_menu", "title": "📋 Volver al menú"},
                    {"id": "c_salir", "title": "❌ Salir"}
                ],
                footer=PIE_MENU
            )
    
    # ========== OPCIÓN 3: TASACIÓN VIRTUAL INTELIGENTE ==========
    elif text_normalized in ["c_tasar", "tasar", "tasacion", "valorar", "3", "tasación virtual", "tasación inteligente"]:
        from tasaciones import manejar_menu_tasacion
        return manejar_menu_tasacion(text, estado_usuario, user_id)
    
    # ========== OPCIÓN 4: ASESORAMIENTO INMOBILIARIO ==========
    elif text_normalized in ["c_asesor", "asesor", "asesoramiento", "hablar con asesor", "contacto", "4"]:
        data['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return (
                "👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para asesorarte.\n\n"
                f"Por favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor:\n\n"
                f"💡 *Envía 'M' para volver al menú o 'S' para salir.*"
            )
        else:
            return (
                "👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para asesorarte.\n\n"
                f"Por favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor: {HINT_SALIR}"
            )
    
    # ========== OPCIÓN 5: SALIR ==========
    elif text_normalized in ["c_salir", "salir", "s", "exit", "0", "5"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    
    # ========== FALLBACK ==========
    else:
        log(f"⚠️ Opción no reconocida en campaña: '{text}' - Mostrando menú nuevamente")
        return iniciar_campana(platform)
    


# ========== VENDER - FLUJO SECUENCIAL ==========

def manejar_vender_paso1_nombre(text, estado_usuario, user_id):
    """Paso 1: Guarda nombre+horario y avanza a paso 2 (documentación)"""
    data = _get_campana_data(estado_usuario)
    data['nombre_horario'] = text
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "nombre_horario", text)
    
    # Avanzar al paso 2
    estado_usuario['paso'] = 'vender_paso2_documentacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📄 *¿Contás con la escritura o título de propiedad a tu nombre?*\n\nEsto nos permite verificar la viabilidad legal inmediata de la venta.\n\n1. Sí, la tengo\n2. No, todavía no\n3. Está en trámite\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="📄 *¿Contás con la escritura o título de propiedad a tu nombre?*\n\nEsto nos permite verificar la viabilidad legal inmediata de la venta.",
            buttons=[
                {"id": "doc_si", "title": "✅ Sí, la tengo"},
                {"id": "doc_no", "title": "❌ No, todavía no"},
                {"id": "doc_tramite", "title": "📋 Está en trámite"}
            ],
            footer="Selecciona una opción 👇"
        )


def manejar_vender_paso2_documentacion(text, estado_usuario, user_id):
    """Paso 2: Guarda documentación y avanza a paso 3 (detalles técnicos)"""
    opciones = {
        "1": "Sí, la tengo",
        "2": "No, todavía no",
        "3": "Está en trámite",
        "doc_si": "Sí, la tengo",
        "doc_no": "No, todavía no",
        "doc_tramite": "Está en trámite"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['documentacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "documentacion", respuesta)
    
    # Avanzar al paso 3
    estado_usuario['paso'] = 'vender_paso3_detalles'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📐 *¿La propiedad tiene planos aprobados y está apta para crédito bancario?*\n\n1. Sí, planos aprobados\n2. No tiene planos\n3. No estoy seguro\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="📐 *¿La propiedad tiene planos aprobados y está apta para crédito bancario?*",
            buttons=[
                {"id": "detalles_si", "title": "✅ Sí, planos aprobados"},
                {"id": "detalles_no", "title": "❌ No tiene planos"},
                {"id": "detalles_duda", "title": "🤔 No estoy seguro"}
            ],
            footer="Selecciona una opción 👇"
        )


def manejar_vender_paso3_detalles(text, estado_usuario, user_id):
    """Paso 3: Guarda detalles técnicos y avanza a paso 4 (ocupación)"""
    opciones = {
        "1": "Sí, planos aprobados",
        "2": "No tiene planos",
        "3": "No estoy seguro",
        "detalles_si": "Sí, planos aprobados",
        "detalles_no": "No tiene planos",
        "detalles_duda": "No estoy seguro"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['detalles_tecnicos'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "detalles_tecnicos", respuesta)
    
    # Avanzar al paso 4
    estado_usuario['paso'] = 'vender_paso4_ocupacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "🚪 *¿La propiedad se encuentra habitada, vacía o alquilada actualmente?*\n\n1. Habitada\n2. Vacía\n3. Alquilada\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="🚪 *¿La propiedad se encuentra habitada, vacía o alquilada actualmente?*",
            buttons=[
                {"id": "ocupacion_habitada", "title": "🏠 Habitada"},
                {"id": "ocupacion_vacia", "title": "🏚️ Vacía"},
                {"id": "ocupacion_alquilada", "title": "🔑 Alquilada"}
            ],
            footer="Selecciona una opción 👇"
        )


def manejar_vender_paso4_ocupacion(text, estado_usuario, user_id):
    """Paso 4: Guarda estado de ocupación y avanza a paso 5 (precio)"""
    opciones = {
        "1": "Habitada",
        "2": "Vacía",
        "3": "Alquilada",
        "ocupacion_habitada": "Habitada",
        "ocupacion_vacia": "Vacía",
        "ocupacion_alquilada": "Alquilada"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['estado_ocupacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "estado_ocupacion", respuesta)
    
    # Avanzar al paso 5
    estado_usuario['paso'] = 'vender_paso5_precio'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "💰 *¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?*\n\n1. Tengo un valor\n2. Prefiero tasación profesional\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="💰 *¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?*",
            buttons=[
                {"id": "precio_valor", "title": "💰 Tengo un valor"},
                {"id": "precio_tasacion", "title": "📊 Prefiero tasación profesional"}
            ],
            footer="Selecciona una opción 👇"
        )


def manejar_vender_paso5_precio(text, estado_usuario, user_id):
    """Paso 5: Guarda precio pretendido y avanza a paso 6 (disponibilidad)"""
    opciones = {
        "1": "Tengo un valor",
        "2": "Prefiero tasación profesional",
        "precio_valor": "Tengo un valor",
        "precio_tasacion": "Prefiero tasación profesional"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    
    if respuesta == "Tengo un valor":
        estado_usuario['paso'] = 'vender_paso5_precio_valor_espera'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "💰 *¿Cuál es el valor de venta que tenés en mente?*\n\n_(Ej: 120.000 USD, 150.000 USD, etc.)_"
    else:
        data['precio_pretendido'] = respuesta
        _set_campana_data(estado_usuario, data)
        guardar_lead_vender(user_id, data, "precio_pretendido", respuesta)
        
        # Avanzar al paso 6
        estado_usuario['paso'] = 'vender_paso6_disponibilidad'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "📅 *¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?*\n\n1. Mañana\n2. Tarde\n3. Fines de semana\n4. Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="📅 *¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?*",
                buttons=[
                    {"id": "disponibilidad_manana", "title": "🌅 Mañana"},
                    {"id": "disponibilidad_tarde", "title": "☀️ Tarde"},
                    {"id": "disponibilidad_finde", "title": "📅 Fines de semana"},
                    {"id": "disponibilidad_otro", "title": "⏰ Coordinar otro horario"}
                ],
                footer="Selecciona una opción 👇"
            )


def manejar_vender_paso5_precio_valor(text, estado_usuario, user_id):
    """Guarda el valor específico del precio y avanza a paso 6"""
    data = _get_campana_data(estado_usuario)
    data['precio_pretendido'] = text
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "precio_pretendido", text)
    
    # Avanzar al paso 6
    estado_usuario['paso'] = 'vender_paso6_disponibilidad'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📅 *¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?*\n\n1. Mañana\n2. Tarde\n3. Fines de semana\n4. Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="📅 *¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?*",
            buttons=[
                {"id": "disponibilidad_manana", "title": "🌅 Mañana"},
                {"id": "disponibilidad_tarde", "title": "☀️ Tarde"},
                {"id": "disponibilidad_finde", "title": "📅 Fines de semana"},
                {"id": "disponibilidad_otro", "title": "⏰ Coordinar otro horario"}
            ],
            footer="Selecciona una opción 👇"
        )


def manejar_vender_paso6_disponibilidad(text, estado_usuario, user_id):
    """Paso 6: Guarda disponibilidad y finaliza el flujo"""
    opciones = {
        "1": "Mañana",
        "2": "Tarde",
        "3": "Fines de semana",
        "4": "Coordinar otro horario",
        "disponibilidad_manana": "Mañana",
        "disponibilidad_tarde": "Tarde",
        "disponibilidad_finde": "Fines de semana",
        "disponibilidad_otro": "Coordinar otro horario"
    }
    
    respuesta = opciones.get(text, text)
    
    if respuesta == "Coordinar otro horario":
        estado_usuario['paso'] = 'vender_paso6_disponibilidad_otro'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📅 *Contanos qué días y horarios te quedan cómodos:*\n\n_(Ej: Lunes y miércoles de 10 a 12hs, o sábados por la mañana)_"
    else:
        data = _get_campana_data(estado_usuario)
        data['disponibilidad'] = respuesta
        _set_campana_data(estado_usuario, data)
        
        guardar_lead_vender(user_id, data, "disponibilidad", respuesta)
        
        # Finalizar flujo
        return finalizar_vender_y_notificar(user_id, estado_usuario, data)


def manejar_vender_paso6_disponibilidad_otro(text, estado_usuario, user_id):
    """Guarda disponibilidad personalizada y finaliza"""
    data = _get_campana_data(estado_usuario)
    data['disponibilidad'] = text
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "disponibilidad", text)
    
    return finalizar_vender_y_notificar(user_id, estado_usuario, data)


def finalizar_vender_y_notificar(user_id, estado_usuario, data):
    """Finaliza el flujo de venta y notifica al agente"""
    # Construir detalles completos
    detalles = []
    for key, value in data.items():
        if key != 'intencion':
            detalles.append(f"{key}: {value}")
    
    detalles_str = " | ".join(detalles)
    
    # Guardar lead final
    nombre = data.get('nombre_horario', f"Lead Venta {str(user_id)[-4:]}")
    guardar_lead_campana(user_id, data)
    
    # Notificar al agente
    mensaje_agente = f"🏠 *NUEVO LEAD DE VENTA* 🏠\n\n"
    mensaje_agente += f"👤 *Contacto:* {nombre}\n"
    mensaje_agente += f"📱 *WhatsApp:* +{user_id}\n"
    mensaje_agente += f"📋 *Detalles completos:*\n{detalles_str}\n\n"
    mensaje_agente += "👉 *Requiere seguimiento comercial.*"
    
    notificar_agente(mensaje_agente)
    
    # Resetear estado
    estado_usuario['paso'] = 'campana_inicio'
    _clear_campana_data(estado_usuario)
    actualizar_estado_usuario(user_id, estado_usuario)
    
    # Mensaje de cierre para el usuario
    mensaje_final = (
        "✅ *Perfecto, ya tenemos toda la información necesaria.*\n\n"
        "En breve un asesor de Dante Propiedades se va a comunicar con vos para coordinar los próximos pasos.\n\n"
        "¡Gracias por confiar en nosotros! 🏠🗝️"
    )
    
    return WhatsAppResponse.buttons(
        body=mensaje_final,
        buttons=[
            {"id": "c_menu", "title": "📋 Volver al menú"},
            {"id": "c_salir", "title": "❌ Salir"}
        ],
        footer="Dante Propiedades · Tu lugar ideal"
    )


def manejar_vender_documentacion(text, estado_usuario, user_id):
    """Guarda la respuesta de documentación y avanza a detalles técnicos"""
    opciones = {
        "1": "Sí, la tengo",
        "2": "No, todavía no",
        "3": "Está en trámite",
        "vender_doc_si": "Sí, la tengo",
        "vender_doc_no": "No, todavía no",
        "vender_doc_tramite": "Está en trámite"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['documentacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "documentacion", respuesta)
    
    # Avanzar al siguiente paso: DETALLES TÉCNICOS
    estado_usuario['paso'] = 'vender_paso_detalles'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📐 *Detalles técnicos*\n\n¿La propiedad tiene planos aprobados y está apta para crédito bancario?\n\n1. Sí, planos aprobados\n2. No tiene planos\n3. No estoy seguro\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="📐 *Detalles técnicos*\n\n¿La propiedad tiene planos aprobados y está apta para crédito bancario?",
            buttons=[
                {"id": "vender_detalles_si", "title": "✅ Sí, planos aprobados"},
                {"id": "vender_detalles_no", "title": "❌ No tiene planos"},
                {"id": "vender_detalles_duda", "title": "🤔 No estoy seguro"}
            ],
            footer="Selecciona una opción 👇"
        )



def manejar_vender_menu(text_lower, estado_usuario, user_id):
    """Maneja la selección del menú principal de Vender"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Normalizar para FB/IG (números)
    if es_fb_ig and text_lower in VENDER_NUMEROS:
        text_lower = VENDER_NUMEROS[text_lower]
    
    # Comandos globales
    if text_lower in ["0", "volver", "menu"]:
        estado_usuario['paso'] = 'campana_intent'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana(platform)
    
    # Datos de la campaña
    data = _get_campana_data(estado_usuario)
    
    # ========== OPCIÓN 1: DATOS DE CONTACTO ==========
    if text_lower == "vender_datos":
        estado_usuario['paso'] = 'vender_submenu_datos'
        actualizar_estado_usuario(user_id, estado_usuario)
        # 👇 TEXTO ACTUALIZADO AQUÍ
        return "📇 *Para comenzar, por favor confirmame tu nombre completo:*\n\n_(Ej: Juan Pérez, María González)_"
    
    # ========== OPCIÓN 2: DOCUMENTACIÓN ==========
    elif text_lower == "vender_documentacion":
        estado_usuario['paso'] = 'vender_submenu_documentacion'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "¿Contás con la escritura o título de propiedad a tu nombre?\nEsto nos permite verificar la viabilidad legal inmediata de la venta.\n\n1. Sí, la tengo\n2. No, todavía no\n3. Está en trámite\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="¿Contás con la escritura o título de propiedad a tu nombre?\nEsto nos permite verificar la viabilidad legal inmediata de la venta.",
                buttons=[
                    {"id": "vender_doc_si", "title": "✅ Sí, la tengo"},
                    {"id": "vender_doc_no", "title": "❌ No, todavía no"},
                    {"id": "vender_doc_tramite", "title": "📋 Está en trámite"}
                ],
                footer="Selecciona una opción 👇"
            )
    
    # ========== OPCIÓN 3: DETALLES TÉCNICOS ==========
    elif text_lower == "vender_detalles":
        estado_usuario['paso'] = 'vender_submenu_detalles'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "¿La propiedad tiene planos aprobados y está apta para crédito bancario?\n\n1. Sí, planos aprobados\n2. No tiene planos\n3. No estoy seguro\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="¿La propiedad tiene planos aprobados y está apta para crédito bancario?",
                buttons=[
                    {"id": "vender_detalles_si", "title": "✅ Sí, planos aprobados"},
                    {"id": "vender_detalles_no", "title": "❌ No tiene planos"},
                    {"id": "vender_detalles_duda", "title": "🤔 No estoy seguro"}
                ],
                footer="Selecciona una opción 👇"
            )
    
    # ========== OPCIÓN 4: ESTADO DE OCUPACIÓN ==========
    elif text_lower == "vender_ocupacion":
        estado_usuario['paso'] = 'vender_submenu_ocupacion'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "¿La propiedad se encuentra habitada, vacía o alquilada actualmente?\n\n1. Habitada\n2. Vacía\n3. Alquilada\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="¿La propiedad se encuentra habitada, vacía o alquilada actualmente?",
                buttons=[
                    {"id": "vender_ocupacion_habitada", "title": "🏠 Habitada"},
                    {"id": "vender_ocupacion_vacia", "title": "🏚️ Vacía"},
                    {"id": "vender_ocupacion_alquilada", "title": "🔑 Alquilada"}
                ],
                footer="Selecciona una opción 👇"
            )
    
    # ========== OPCIÓN 5: PRECIO PRETENDIDO ==========
    elif text_lower == "vender_precio":
        estado_usuario['paso'] = 'vender_submenu_precio'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?\n\n1. Tengo un valor\n2. Prefiero tasación profesional\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?",
                buttons=[
                    {"id": "vender_precio_valor", "title": "💰 Tengo un valor"},
                    {"id": "vender_precio_tasacion", "title": "📊 Prefiero tasación profesional"}
                ],
                footer="Selecciona una opción 👇"
            )
    
    # ========== OPCIÓN 6: DISPONIBILIDAD PARA VISITA ==========
    elif text_lower == "vender_disponibilidad":
        estado_usuario['paso'] = 'vender_submenu_disponibilidad'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?\n\n1. Mañana\n2. Tarde\n3. Fines de semana\n4. Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?",
                buttons=[
                    {"id": "vender_disponibilidad_manana", "title": "🌅 Mañana"},
                    {"id": "vender_disponibilidad_tarde", "title": "☀️ Tarde"},
                    {"id": "vender_disponibilidad_finde", "title": "📅 Fines de semana"},
                    {"id": "vender_disponibilidad_otro", "title": "⏰ Coordinar otro horario"}
                ],
                footer="Selecciona una opción 👇"
            )
    
    # ========== OPCIÓN NO RECONOCIDA ==========
    else:
        return mostrar_menu_vender(estado_usuario, user_id)


def mostrar_menu_horarios(estado_usuario, user_id):
    """Muestra los rangos horarios para que el usuario elija"""
    log(f"🔍 [HORARIOS] Iniciando mostrar_menu_horarios")
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    log(f"🔍 [HORARIOS] platform: {platform}, es_fb_ig: {es_fb_ig}")
    
    cuerpo = "📅 *¿En qué horario te gustaría que Dante te llame?*\n\nSeleccioná una opción:"
    
    if es_fb_ig:
        log(f"🔍 [HORARIOS] Devolviendo texto para FB/IG")
        return {
            "type": "text",
            "body": f"{cuerpo}\n\n1. 🌅 Mañana (9 a 12hs)\n2. ☀️ Mediodía (12 a 15hs)\n3. 🌇 Tarde (15 a 18hs)\n4. 🌙 Noche (18 a 20hs)\n5. 📅 Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        log(f"🔍 [HORARIOS] Devolviendo botones para WhatsApp")
        return WhatsAppResponse.buttons(
            body=cuerpo,
            buttons=[
                {"id": "horario_manana", "title": "🌅 Mañana (9-12hs)"},
                {"id": "horario_mediodia", "title": "☀️ Mediodía (12-15hs)"},
                {"id": "horario_tarde", "title": "🌇 Tarde (15-18hs)"},
                {"id": "horario_noche", "title": "🌙 Noche (18-20hs)"},
                {"id": "horario_otro", "title": "📅 Coordinar otro horario"}
            ],
            footer="Selecciona un horario 👇"
        )
        
        
def manejar_vender_horario(text, estado_usuario, user_id):
    """Maneja la selección de horario y avanza al siguiente paso"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    opciones = {
        "1": "Mañana (9 a 12hs)",
        "2": "Mediodía (12 a 15hs)",
        "3": "Tarde (15 a 18hs)",
        "4": "Noche (18 a 20hs)",
        "5": "Coordinar otro horario",
        "horario_manana": "Mañana (9 a 12hs)",
        "horario_mediodia": "Mediodía (12 a 15hs)",
        "horario_tarde": "Tarde (15 a 18hs)",
        "horario_noche": "Noche (18 a 20hs)",
        "horario_otro": "Coordinar otro horario"
    }
    
    if es_fb_ig and text.isdigit():
        for key, value in opciones.items():
            if key == text:
                text = value
                break
    
    horario = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    
    if horario == "Coordinar otro horario":
        estado_usuario['paso'] = 'vender_horario_personalizado'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📅 *Contanos qué horario te queda más cómodo:*\n\n_(Ej: Lunes de 10 a 12hs, o después de las 16hs)_"
    else:
        data['horario_preferido'] = horario
        _set_campana_data(estado_usuario, data)
        
        guardar_lead_vender(user_id, data, "horario_preferido", horario)
        
        # Avanzar al siguiente paso: DOCUMENTACIÓN
        estado_usuario['paso'] = 'vender_paso_documentacion'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Mostrar pregunta de documentación
        if es_fb_ig:
            return {
                "type": "text",
                "body": "📄 *Documentación*\n\n¿Contás con la escritura o título de propiedad a tu nombre?\nEsto nos permite verificar la viabilidad legal inmediata de la venta.\n\n1. Sí, la tengo\n2. No, todavía no\n3. Está en trámite\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="📄 *Documentación*\n\n¿Contás con la escritura o título de propiedad a tu nombre?\nEsto nos permite verificar la viabilidad legal inmediata de la venta.",
                buttons=[
                    {"id": "vender_doc_si", "title": "✅ Sí, la tengo"},
                    {"id": "vender_doc_no", "title": "❌ No, todavía no"},
                    {"id": "vender_doc_tramite", "title": "📋 Está en trámite"}
                ],
                footer="Selecciona una opción 👇"
            )
            

def manejar_vender_horario_personalizado(text, estado_usuario, user_id):
    """Guarda el horario personalizado"""
    log(f"🔍 [HORARIO_PERS] Inicio - texto: '{text}'")
    
    data = _get_campana_data(estado_usuario)
    data['horario_preferido'] = text
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "horario_preferido", text)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Volver al menú principal de venta
    estado_usuario['paso'] = 'vender_menu_principal'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    respuesta = f"✅ *¡Gracias {data.get('nombre_completo', '')}!* Hemos registrado tu horario: {text}\n\n¿Necesitás completar algún otro dato o preferís que un asesor te contacte?"
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": f"{respuesta}\n\n1. Volver al menú Vender\n2. Salir\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body=respuesta,
            buttons=[
                {"id": "vender_menu", "title": "📋 Volver al menú Vender"},
                {"id": "c_salir", "title": "❌ Salir"}
            ],
            footer="Dante Propiedades · Tu lugar ideal"
        )
        
        

def manejar_vender_detalles(text, estado_usuario, user_id):
    """Guarda la respuesta de detalles técnicos y avanza a estado de ocupación"""
    opciones = {
        "1": "Sí, planos aprobados",
        "2": "No tiene planos",
        "3": "No estoy seguro",
        "vender_detalles_si": "Sí, planos aprobados",
        "vender_detalles_no": "No tiene planos",
        "vender_detalles_duda": "No estoy seguro"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['detalles_tecnicos'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "detalles_tecnicos", respuesta)
    
    # Avanzar al siguiente paso: ESTADO DE OCUPACIÓN
    estado_usuario['paso'] = 'vender_paso_ocupacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "🚪 *Estado de ocupación*\n\n¿La propiedad se encuentra habitada, vacía o alquilada actualmente?\n\n1. Habitada\n2. Vacía\n3. Alquilada\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="🚪 *Estado de ocupación*\n\n¿La propiedad se encuentra habitada, vacía o alquilada actualmente?",
            buttons=[
                {"id": "vender_ocupacion_habitada", "title": "🏠 Habitada"},
                {"id": "vender_ocupacion_vacia", "title": "🏚️ Vacía"},
                {"id": "vender_ocupacion_alquilada", "title": "🔑 Alquilada"}
            ],
            footer="Selecciona una opción 👇"
        )
        
        

def manejar_vender_ocupacion(text, estado_usuario, user_id):
    """Guarda la respuesta de estado de ocupación y avanza a precio pretendido"""
    opciones = {
        "1": "Habitada",
        "2": "Vacía",
        "3": "Alquilada",
        "vender_ocupacion_habitada": "Habitada",
        "vender_ocupacion_vacia": "Vacía",
        "vender_ocupacion_alquilada": "Alquilada"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['estado_ocupacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "estado_ocupacion", respuesta)
    
    # Avanzar al siguiente paso: PRECIO PRETENDIDO
    estado_usuario['paso'] = 'vender_paso_precio'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "💰 *Precio pretendido*\n\n¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?\n\n1. Tengo un valor\n2. Prefiero tasación profesional\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="💰 *Precio pretendido*\n\n¿Tenés un valor de venta en mente o preferís que realicemos primero la tasación profesional?",
            buttons=[
                {"id": "vender_precio_valor", "title": "💰 Tengo un valor"},
                {"id": "vender_precio_tasacion", "title": "📊 Prefiero tasación profesional"}
            ],
            footer="Selecciona una opción 👇"
        )
        
        

def manejar_vender_precio(text, estado_usuario, user_id):
    """Guarda la respuesta de precio pretendido y avanza a disponibilidad"""
    opciones = {
        "1": "Tengo un valor",
        "2": "Prefiero tasación profesional",
        "vender_precio_valor": "Tengo un valor",
        "vender_precio_tasacion": "Prefiero tasación profesional"
    }
    
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    
    if respuesta == "Tengo un valor":
        estado_usuario['paso'] = 'vender_precio_valor_espera'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "💰 *¿Cuál es el valor de venta que tenés en mente?*\n\n_(Ej: 120.000 USD, 150.000 USD, etc.)_"
    else:
        data['precio_pretendido'] = respuesta
        _set_campana_data(estado_usuario, data)
        guardar_lead_vender(user_id, data, "precio_pretendido", respuesta)
        
        # Avanzar al siguiente paso: DISPONIBILIDAD
        estado_usuario['paso'] = 'vender_paso_disponibilidad'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "📅 *Disponibilidad para visita*\n\n¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?\n\n1. Mañana\n2. Tarde\n3. Fines de semana\n4. Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="📅 *Disponibilidad para visita*\n\n¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?",
                buttons=[
                    {"id": "vender_disponibilidad_manana", "title": "🌅 Mañana"},
                    {"id": "vender_disponibilidad_tarde", "title": "☀️ Tarde"},
                    {"id": "vender_disponibilidad_finde", "title": "📅 Fines de semana"},
                    {"id": "vender_disponibilidad_otro", "title": "⏰ Coordinar otro horario"}
                ],
                footer="Selecciona una opción 👇"
            )
            
            

def manejar_vender_precio_valor(text, estado_usuario, user_id):
    """Guarda el valor específico del precio y avanza a disponibilidad"""
    data = _get_campana_data(estado_usuario)
    data['precio_pretendido'] = text
    _set_campana_data(estado_usuario, data)
    
    guardar_lead_vender(user_id, data, "precio_pretendido", text)
    
    # Avanzar al siguiente paso: DISPONIBILIDAD
    estado_usuario['paso'] = 'vender_paso_disponibilidad'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📅 *Disponibilidad para visita*\n\n¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?\n\n1. Mañana\n2. Tarde\n3. Fines de semana\n4. Coordinar otro horario\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="📅 *Disponibilidad para visita*\n\n¿Qué días y horarios te quedarían cómodos para que visitemos la propiedad y tomemos las fotos profesionales para la publicación?",
            buttons=[
                {"id": "vender_disponibilidad_manana", "title": "🌅 Mañana"},
                {"id": "vender_disponibilidad_tarde", "title": "☀️ Tarde"},
                {"id": "vender_disponibilidad_finde", "title": "📅 Fines de semana"},
                {"id": "vender_disponibilidad_otro", "title": "⏰ Coordinar otro horario"}
            ],
            footer="Selecciona una opción 👇"
        )
        

def manejar_vender_disponibilidad(text, estado_usuario, user_id):
    """Guarda la respuesta de disponibilidad y finaliza"""
    opciones = {
        "1": "Mañana",
        "2": "Tarde",
        "3": "Fines de semana",
        "4": "Coordinar otro horario",
        "vender_disponibilidad_manana": "Mañana",
        "vender_disponibilidad_tarde": "Tarde",
        "vender_disponibilidad_finde": "Fines de semana",
        "vender_disponibilidad_otro": "Coordinar otro horario"
    }
    
    respuesta = opciones.get(text, text)
    
    if respuesta == "Coordinar otro horario":
        estado_usuario['paso'] = 'vender_disponibilidad_otro_espera'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📅 *Contanos qué días y horarios te quedan cómodos:*\n\n_(Ej: Lunes y miércoles de 10 a 12hs, o sábados por la mañana)_"
    else:
        data = _get_campana_data(estado_usuario)
        data['disponibilidad'] = respuesta
        _set_campana_data(estado_usuario, data)
        
        guardar_lead_vender(user_id, data, "disponibilidad", respuesta)
        
        # Finalizar flujo y notificar
        return finalizar_vender_y_notificar(user_id, estado_usuario, data)
    
    


def guardar_lead_vender(user_id, data, paso, valor):
    """Guarda progreso parcial del lead de venta en JSON"""
    try:
        import os, json
        from config import LEADS_FILE
        from utils import save_json_atomic
        from datetime import datetime
        
        leads = []
        if os.path.exists(LEADS_FILE):
            try:
                with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                    leads = json.load(f)
            except Exception:
                leads = []
        
        # IMPORTANTE: Usar nombre_completo en lugar de nombre_horario
        nombre = data.get('nombre_completo') or data.get('nombre_horario', f"Lead Venta {str(user_id)[-4:]}")
        
        nuevo_lead = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'propiedad_id': '',
            'accion': f"venta_{paso}",
            'detalle': valor,
            'propiedad_nombre': f"Venta - {paso}",
            'nombre': nombre
        }
        
        # Agregar al array existente
        leads.append(nuevo_lead)
        save_json_atomic(LEADS_FILE, leads)
        log(f"✅ Progreso de venta guardado: {user_id} - {paso}: {valor}")
    except Exception as e:
        log(f"⚠️ Error guardando progreso de venta: {e}", "WARNING")
        
        
def manejar_vender_datos(text, estado_usuario, user_id):
    """Guarda el nombre y luego pregunta horario"""
    log(f"🔍 [DATOS] Inicio - texto: '{text}'")
    log(f"🔍 [DATOS] paso actual antes: {estado_usuario.get('paso')}")
    
    data = _get_campana_data(estado_usuario)
    log(f"🔍 [DATOS] data actual: {data}")
    
    # Verificar si ya tenemos el nombre o es el primer paso
    if 'nombre_completo' not in data:
        log(f"🔍 [DATOS] No hay nombre_completo, guardando...")
        
        # Primer paso: guardar nombre
        data['nombre_completo'] = text
        _set_campana_data(estado_usuario, data)
        
        # Guardar progreso parcial
        guardar_lead_vender(user_id, data, "nombre_completo", text)
        
        # Cambiar al siguiente paso (horario)
        estado_usuario['paso'] = 'vender_submenu_horario'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        log(f"🔍 [DATOS] paso cambiado a: {estado_usuario['paso']}")
        
        # Mostrar menú de horarios
        log(f"🔍 [DATOS] Llamando a mostrar_menu_horarios")
        return mostrar_menu_horarios(estado_usuario, user_id)
    
    else:
        log(f"🔍 [DATOS] YA existe nombre_completo: {data['nombre_completo']}")
        return mostrar_menu_horarios(estado_usuario, user_id)
    
    

def manejar_vender_disponibilidad(text, estado_usuario, user_id):
    """Guarda la respuesta de disponibilidad"""
    opciones = {
        "1": "Mañana",
        "2": "Tarde",
        "3": "Fines de semana",
        "4": "Coordinar otro horario",
        "vender_disponibilidad_manana": "Mañana",
        "vender_disponibilidad_tarde": "Tarde",
        "vender_disponibilidad_finde": "Fines de semana",
        "vender_disponibilidad_otro": "Coordinar otro horario"
    }
    
    respuesta = opciones.get(text, text)
    
    if respuesta == "Coordinar otro horario":
        estado_usuario['paso'] = 'vender_disponibilidad_otro_espera'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📅 *Contanos qué días y horarios te quedan cómodos:*\n\n_(Ej: Lunes y miércoles de 10 a 12hs, o sábados por la mañana)_"
    else:
        data = _get_campana_data(estado_usuario)
        data['disponibilidad'] = respuesta
        _set_campana_data(estado_usuario, data)
        
        guardar_lead_vender(user_id, data, "disponibilidad", respuesta)
        
        # Finalizar flujo y notificar
        return finalizar_vender_y_notificar(user_id, estado_usuario, data)


def finalizar_vender_y_notificar(user_id, estado_usuario, data):
    """Finaliza el flujo de venta y notifica al agente"""
    # Construir detalles completos
    detalles = []
    for key, value in data.items():
        if key != 'intencion':
            detalles.append(f"{key}: {value}")
    
    detalles_str = " | ".join(detalles)
    
    # IMPORTANTE: Usar nombre_completo en lugar de nombre_horario
    nombre = data.get('nombre_completo', f"Lead Venta {str(user_id)[-4:]}")
    guardar_lead_campana(user_id, data)  # Reusamos la función existente
    
    # Notificar al agente
    mensaje_agente = f"🏠 *NUEVO LEAD DE VENTA* 🏠\n\n"
    mensaje_agente += f"👤 *Contacto:* {nombre}\n"
    mensaje_agente += f"📱 *WhatsApp:* +{user_id}\n"
    mensaje_agente += f"📋 *Detalles completos:*\n{detalles_str}\n\n"
    mensaje_agente += "👉 *Requiere seguimiento comercial.*"
    
    notificar_agente(mensaje_agente)
    
    # Resetear estado
    estado_usuario['paso'] = 'campana_inicio'
    _clear_campana_data(estado_usuario)
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    mensaje_final = (
        "✅ *¡Excelente!* Hemos recibido toda la información de tu propiedad.\n\n"
        "Un asesor especializado de Dante Propiedades se pondrá en contacto contigo a la brevedad para coordinar los próximos pasos y comenzar con la comercialización.\n\n"
        "¡Gracias por confiar en nosotros! 🏠🗝️"
    )
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": f"{mensaje_final}\n\n1. Volver al menú principal\n2. Salir\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body=mensaje_final,
            buttons=[
                {"id": "c_menu", "title": "📋 Volver al menú"},
                {"id": "c_salir", "title": "❌ Salir"}
            ],
            footer="Dante Propiedades · Tu lugar ideal"
        )




def mostrar_menu_vender(estado_usuario, user_id):
    """Muestra el menú principal de 'Quiero Vender'"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    cuerpo = "Perfecto, te acompaño con la venta de tu propiedad. Para avanzar, seleccioná una de las siguientes opciones:"
    
    if es_fb_ig:
        # Facebook/Instagram: texto con numeración
        opciones_texto = (
            "1. 📇 Datos de contacto\n"
            "2. 📄 Documentación\n"
            "3. 📐 Detalles técnicos\n"
            "4. 🚪 Estado de ocupación\n"
            "5. 💰 Precio pretendido\n"
            "6. 📅 Disponibilidad para visita\n\n"
            "💡 *Envía el número de la opción deseada*\n\n"
            "0️⃣ Volver al menú principal"
        )
        
        return {
            "type": "text",
            "body": f"{cuerpo}\n\n{opciones_texto}",
            "preview": False
        }
    else:
        # WhatsApp: botones interactivos
        buttons = [
            {"id": "vender_datos", "title": "📇 Datos de contacto"},
            {"id": "vender_documentacion", "title": "📄 Documentación"},
            {"id": "vender_detalles", "title": "📐 Detalles técnicos"},
            {"id": "vender_ocupacion", "title": "🚪 Estado de ocupación"},
            {"id": "vender_precio", "title": "💰 Precio pretendido"},
            {"id": "vender_disponibilidad", "title": "📅 Disponibilidad para visita"}
        ]
        
        return WhatsAppResponse.buttons(
            body=cuerpo,
            buttons=buttons,
            footer="Selecciona una opción 👇"
        )
        
        



# ========== RECOPILACIÓN DE DATOS ==========

def manejar_recopilacion_datos(text, estado_usuario, user_id):
    paso = estado_usuario['paso']
    data = _get_campana_data(estado_usuario)
    intencion = data.get('intencion')
    
    # Obtener platform para saber qué formato usar
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    # Log para depuración
    log(f"🔍 manejar_recopilacion_datos - platform: {platform}, es_fb_ig: {es_fb_ig}")
    
    # Si no hay intención guardada, algo se perdió → reiniciar
    if not intencion:
        log(f"⚠️ data_campana sin intención en paso {paso}, reiniciando", "WARNING", user_id=user_id)
        estado_usuario['paso'] = 'campana_intent'
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana()
    
    # FLUJO: COMPRAR / ALQUILAR
    if intencion in ["Comprar", "Alquilar"]:
        if paso == 'campana_recopilar_zona':
            data['zona'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if es_fb_ig:
                # Facebook/Instagram: texto con numeración simple
                return {
                    "type": "text",
                    "body": f"📍 Zona: *{text}* ✅\n\n¿Qué *tipo de propiedad* estás buscando?\n\n1️⃣ 🏢 Departamento\n2️⃣ 🏠 Casa\n3️⃣ 🏭 Otro (Local/Lote)\n\n💡 Envía el número de la opción deseada, 🔙 M para volver o ❌ S para salir.",
                    "preview": False
                }
            else:
                # WhatsApp: botones SIN números
                return WhatsAppResponse.buttons(
                    body=f"📍 Zona: *{text}* ✅\n\n¿Qué *tipo de propiedad* estás buscando?",
                    buttons=[
                        {"id": "Depto", "title": "🏢 Departamento"},
                        {"id": "Casa", "title": "🏠 Casa"},
                        {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}
                    ],
                    footer=PIE_SELECCION
                )
            
        elif paso == 'campana_recopilar_tipo':
            # Mapear números a textos para FB/IG
            texto_tipo = text
            if es_fb_ig:
                mapa_tipos = {
                    "1": "Departamento",
                    "2": "Casa",
                    "3": "Otro",
                    "1.": "Departamento",
                    "2.": "Casa",
                    "3.": "Otro"
                }
                texto_tipo = mapa_tipos.get(text.lower().strip(), text)
            
            data['tipo'] = texto_tipo
            estado_usuario['paso'] = 'campana_recopilar_presupuesto'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            moneda = "USD" if intencion == "Comprar" else "ARS/USD"
            
            if es_fb_ig:
                return f"🏠 Tipo: *{texto_tipo}* ✅\n\nPor último, ¿cuál es tu *presupuesto máximo* estimado en {moneda}?\n_(Ej: 100.000, 500k, etc.)_\n\n💡 Envía '*M*' para volver al menú o '*S*' para salir."
            else:
                return f"🏠 Tipo: *{texto_tipo}* ✅\n\nPor último, ¿cuál es tu *presupuesto máximo* estimado en {moneda}?\n_(Ej: 100.000, 500k, etc.)_{HINT_SALIR}"
            
        elif paso == 'campana_recopilar_presupuesto':
            data['presupuesto'] = text
            estado_usuario['paso'] = 'campana_confirmacion'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            return mostrar_resumen_campana(data)

    # FLUJO: TASAR
    elif intencion == "Tasar":
        if paso == 'campana_recopilar_direccion':
            data['direccion'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo_tasacion'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if es_fb_ig:
                # Facebook/Instagram: texto con numeración simple
                return {
                    "type": "text",
                    "body": f"📍 Dirección: *{text}* ✅\n\n¿Qué *tipo de propiedad* deseas tasar?\n\n1. 🏢 Departamento\n2. 🏠 Casa\n3. 🏭 Otro (Local/Lote)\n\n💡 Envía el número de la opción deseada, 'M' para volver al menú o 'S' para salir.",
                    "preview": False
                }
            else:
                # WhatsApp: botones SIN números
                return WhatsAppResponse.buttons(
                    body=f"📍 Dirección: *{text}* ✅\n\n¿Qué *tipo de propiedad* deseas tasar?",
                    buttons=[
                        {"id": "Depto", "title": "🏢 Departamento"},
                        {"id": "Casa", "title": "🏠 Casa"},
                        {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}
                    ],
                    footer=PIE_MENU
                )
            
        elif paso == 'campana_recopilar_tipo_tasacion':
            # Mapear números a textos para FB/IG
            texto_tipo = text
            if es_fb_ig:
                mapa_tipos = {
                    "1": "Departamento",
                    "2": "Casa",
                    "3": "Otro",
                    "1.": "Departamento",
                    "2.": "Casa",
                    "3.": "Otro"
                }
                texto_tipo = mapa_tipos.get(text.lower().strip(), text)
            
            data['tipo'] = texto_tipo
            estado_usuario['paso'] = 'campana_recopilar_estado'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if es_fb_ig:
                # Facebook/Instagram: texto con numeración simple
                return {
                    "type": "text",
                    "body": f"🏠 Tipo: *{texto_tipo}* ✅\n\n¿En qué *estado general* se encuentra la propiedad?\n\n1. ✨ Excelente\n2. 👍 Bueno/Refaccionar\n3. 🏗️ En obra/Terreno\n\n💡 Envía el número de la opción deseada, 'M' para volver al menú o 'S' para salir.",
                    "preview": False
                }
            else:
                # WhatsApp: botones SIN números
                return WhatsAppResponse.buttons(
                    body=f"🏠 Tipo: *{texto_tipo}* ✅\n\n¿En qué *estado general* se encuentra la propiedad?",
                    buttons=[
                        {"id": "Excelente", "title": "✨ Excelente"},
                        {"id": "Bueno", "title": "👍 Bueno/Refaccionar"},
                        {"id": "En_obra", "title": "🏗️ En obra/Terreno"}
                    ],
                    footer=PIE_MENU
                )
            
        elif paso == 'campana_recopilar_estado':
            # Mapear números a textos para FB/IG
            texto_estado = text
            if es_fb_ig:
                mapa_estados = {
                    "1": "Excelente",
                    "2": "Bueno",
                    "3": "En_obra",
                    "1.": "Excelente",
                    "2.": "Bueno",
                    "3.": "En_obra"
                }
                texto_estado = mapa_estados.get(text.lower().strip(), text)
            
            data['estado_propiedad'] = texto_estado
            estado_usuario['paso'] = 'campana_confirmacion'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            return mostrar_resumen_campana(data)
            
    # Fallback si el paso no matchea
    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana()



# ========== NOMBRE PARA ASESOR ==========

def manejar_pedir_nombre_asesor(text, estado_usuario, user_id):
    data = _get_campana_data(estado_usuario)
    data['nombre'] = text
    
    # Derivar inmediatamente
    guardar_lead_campana(user_id, data)
    
    estado_usuario['paso'] = 'campana_inicio'
    _clear_campana_data(estado_usuario)
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return WhatsAppResponse.buttons(
        body=f"✅ *¡Gracias, {text}!*\n\nHemos derivado tu contacto a un asesor de guardia, quien se comunicará contigo a la brevedad por este WhatsApp.\n\n{LOGO} Dante Propiedades\n\n1️⃣ Volver al menú\n2️⃣ Salir",
        buttons=[
            {"id": "c_menu", "title": "1️⃣ 📋 Volver al menú"},
            {"id": "c_salir", "title": "2️⃣ ❌ Salir"}
        ],
        footer=PIE_MENU
    )


# ========== RESUMEN Y CONFIRMACIÓN ==========

def mostrar_resumen_campana(data):
    """Muestra el resumen de la búsqueda con opciones interactivas según plataforma"""
    
    intencion = data.get('intencion')
    platform = None
    es_fb_ig = False
    
    # Intentar obtener platform del contexto
    import inspect
    frame = inspect.currentframe()
    try:
        # Buscar estado_usuario en frames anteriores
        while frame:
            if 'estado_usuario' in frame.f_locals:
                estado = frame.f_locals['estado_usuario']
                if isinstance(estado, dict) and 'platform' in estado:
                    platform = estado.get('platform')
                    es_fb_ig = platform in ("messenger", "facebook", "instagram")
                    break
            frame = frame.f_back
    finally:
        del frame
    
    resumen = f"{MARCA}\n━━━━━━━━━━━━━━━━━\n📋 *RESUMEN DE TU BÚSQUEDA*\n\n"
    resumen += f"🔸 *Intención:* {intencion}\n"
    
    if intencion in ["Comprar", "Alquilar"]:
        resumen += f"📍 *Zona:* {data.get('zona')}\n"
        resumen += f"🏠 *Tipo:* {data.get('tipo')}\n"
        resumen += f"💰 *Presupuesto:* {data.get('presupuesto')}\n"
    elif intencion == "Tasar":
        resumen += f"📍 *Dirección/Zona:* {data.get('direccion')}\n"
        resumen += f"🏠 *Tipo:* {data.get('tipo')}\n"
        resumen += f"🛠️ *Estado:* {data.get('estado_propiedad')}\n"
    
    resumen += "\n━━━━━━━━━━━━━━━━━"
    
    if es_fb_ig:
        # Facebook/Instagram: SOLO texto plano con emojis numéricos (sin botones de Meta)
        resumen_completo = (
            f"{resumen}\n\n"
            "¿Estos datos son correctos?\n\n"
            "1️⃣ ✅ Confirmar\n"
            "2️⃣ 🔄 Corregir\n"
            "3️⃣ ❌ Cancelar\n\n"
            f"{PIE_MENU}\n\n"
            "💡 *Envía el número de la opción deseada*"
        )
        
        return {
            "type": "text",
            "body": resumen_completo,
            "preview": False
        }
    else:
        # WhatsApp: SOLO botones interactivos (sin texto duplicado)
        return WhatsAppResponse.buttons(
            body=resumen,
            buttons=[
                {"id": "confirmar_datos", "title": "✅ Confirmar"},
                {"id": "corregir_datos", "title": "🔄 Corregir"},
                {"id": "c_salir", "title": "❌ Cancelar"}
            ],
            footer=PIE_SELECCION
        )
        
        
def manejar_confirmacion_campana(text, estado_usuario, user_id):
    if text in ["confirmar_datos", "1", "si", "sí", "confirmar", "ok"]:
        data = _get_campana_data(estado_usuario)
        intencion = data.get('intencion')
        
        # Guardar en CRM (PostgreSQL + JSON)
        guardar_lead_campana(user_id, data)
        
        # Resetear estado
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Detectar plataforma
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        
        if intencion == "Tasar":
            msg_base = "✅ *¡Solicitud registrada!*\n\nUn tasador experto de nuestro equipo se pondrá en contacto contigo muy pronto para brindarte el valor real de tu propiedad."
        else:
            msg_base = "✅ *¡Búsqueda registrada!*\n\nUn asesor especializado está analizando nuestra base de datos (incluso propiedades off-market) y se contactará contigo a la brevedad con las mejores opciones a medida."
        
        msg = f"{msg_base}\n\n{DESPEDIDA}"
        
        if es_fb_ig:
            # Facebook/Instagram: texto con EMOJIS NUMÉRICOS
            mensaje_completo = (
                f"{msg}\n\n"
                "1️⃣ 📋 Nueva búsqueda\n"
                "2️⃣ ❌ Salir\n\n"
                f"{PIE_MENU}\n\n"
                "💡 *Envía el número de la opción deseada*"
            )
            
            return {
                "type": "text",
                "body": mensaje_completo,
                "preview": False
            }
        else:
            # WhatsApp: botones interactivos
            return WhatsAppResponse.buttons(
                body=msg,
                buttons=[
                    {"id": "c_menu", "title": "📋 Nueva búsqueda"},
                    {"id": "c_salir", "title": "❌ Salir"}
                ],
                footer=PIE_MENU
            )
            
    elif text in ["corregir_datos", "2", "no", "corregir"]:
        data = _get_campana_data(estado_usuario)
        intencion = data.get('intencion')
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        
        if intencion in ["Comprar", "Alquilar"]:
            estado_usuario['paso'] = 'campana_recopilar_zona'
            _set_campana_data(estado_usuario, {'intencion': intencion})
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if es_fb_ig:
                return {
                    "type": "text",
                    "body": f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_\n\n💡 *Envía 'M' para volver al menú o 'S' para salir.*",
                    "preview": False
                }
            else:
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_{HINT_SALIR}"
                
        elif intencion == "Tasar":
            estado_usuario['paso'] = 'campana_recopilar_direccion'
            _set_campana_data(estado_usuario, {'intencion': intencion})
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if es_fb_ig:
                return {
                    "type": "text",
                    "body": f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿Cuál es la *dirección o zona* de la propiedad a tasar?\n_(Ej: Av. Rivadavia 5000, Caballito)_\n\n💡 *Envía 'M' para volver al menú o 'S' para salir.*",
                    "preview": False
                }
            else:
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿Cuál es la *dirección o zona* de la propiedad a tasar?\n_(Ej: Av. Rivadavia 5000, Caballito)_{HINT_SALIR}"
        else:
            estado_usuario['paso'] = 'campana_intent'
            _clear_campana_data(estado_usuario)
            actualizar_estado_usuario(user_id, estado_usuario)
            return iniciar_campana(platform)
    
    elif text in ["c_salir", "salir", "cancelar", "3"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
        
    # Si no reconoce, mostrar de nuevo
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "¿Estos datos son correctos?\n\n1️⃣ ✅ Confirmar\n2️⃣ 🔄 Corregir\n3️⃣ ❌ Cancelar\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            body="Por favor, confirmá si los datos son correctos:",
            buttons=[
                {"id": "confirmar_datos", "title": "✅ Confirmar"},
                {"id": "corregir_datos", "title": "🔄 Corregir"},
                {"id": "c_salir", "title": "❌ Cancelar"}
            ],
            footer=PIE_MENU
        )

# ========== PERSISTENCIA DE LEADS ==========

def guardar_lead_campana(user_id, data):
    """Guarda el lead en la BD (PostgreSQL + JSON fallback) y notifica al agente"""
    intencion = data.get('intencion', 'Desconocida')
    nombre = data.get('nombre', f"Lead {str(user_id)[-4:]}")
    
    accion = f"lead_campaña_{intencion.lower()}"
    
    detalles_lista = []
    for k, v in data.items():
        if k not in ['intencion', 'nombre']:
            detalles_lista.append(f"{k.capitalize()}: {v}")
            
    detalles_str = " | ".join(detalles_lista)
    
    # 1. Guardar en PostgreSQL
    lead_id_pg = None
    try:
        lead_id_pg = guardar_en_postgresql(user_id, nombre, accion, detalles_str)
        if lead_id_pg:
            log(f"✅ Lead de campaña guardado en PostgreSQL (ID: {lead_id_pg}): {user_id} - {intencion}")
        else:
            log(f"⚠️ PostgreSQL no disponible para lead de campaña: {user_id} - {intencion}", "WARNING")
    except Exception as e:
        log(f"⚠️ Error guardando lead de campaña en PostgreSQL: {e}", "WARNING")
    
    # 2. Guardar SIEMPRE en JSON como respaldo (para que el admin panel lo vea)
    try:
        import os, json
        from config import LEADS_FILE
        from utils import save_json_atomic
        
        leads = []
        if os.path.exists(LEADS_FILE):
            try:
                with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                    leads = json.load(f)
            except Exception:
                leads = []
        
        from datetime import datetime
        nuevo_lead = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'propiedad_id': '',
            'accion': accion,
            'detalle': detalles_str,
            'propiedad_nombre': f"Campaña: {intencion}",
            'nombre': nombre
        }
        leads.append(nuevo_lead)
        save_json_atomic(LEADS_FILE, leads)
        log(f"✅ Lead de campaña guardado en JSON: {user_id} - {intencion}")
    except Exception as e:
        log(f"🔥 Error guardando lead de campaña en JSON: {e}", "ERROR")
        
    # 3. Notificar al Agente
    mensaje_agente = f"🚨 *NUEVO LEAD DE CAMPAÑA* 🚨\n\n"
    mensaje_agente += f"👤 *Nombre:* {nombre}\n"
    mensaje_agente += f"📱 *WhatsApp:* +{user_id}\n"
    mensaje_agente += f"🎯 *Intención:* {intencion}\n\n"
    if detalles_str:
        mensaje_agente += f"📝 *Detalles:*\n{detalles_str}\n\n"
    mensaje_agente += "👉 *Requiere contacto inmediato.*"
    
    notificar_agente(mensaje_agente)
