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
PIE_MENU = "🏠 Dante Propiedades · Tu lugar ideal 🗝️"
PIE_SELECCION= "Selecciona una opción 👇"
HINT_SALIR = "\n\n💡 _Envía '*S*' para salir o '*M*' para volver al menú._"

# ========== HELPERS PARA DATA DE CAMPAÑA ==========

def _get_campana_data(estado_usuario):
    if not isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data'] = {}
    return estado_usuario['data'].get('campana', {})

def _set_campana_data(estado_usuario, campana_data):
    if not isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data'] = {}
    estado_usuario['data']['campana'] = campana_data

def _clear_campana_data(estado_usuario):
    if isinstance(estado_usuario.get('data'), dict):
        estado_usuario['data']['campana'] = {}

# ========== FUNCIÓN PRINCIPAL ==========

def get_bot_response_campana(text, user_id):
    text_lower = text.lower().strip()
    estado_usuario = obtener_estado_usuario(user_id)
    paso_actual = estado_usuario.get('paso', 'campana_inicio')
    
    from database import obtener_estado_usuario as get_fresh_state
    fresh_state = get_fresh_state(user_id)
    platform = fresh_state.get('platform') or estado_usuario.get('platform')
    
    log(f"🔍 get_bot_response_campana - platform obtenido: '{platform}'")
    
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
        except Exception as e:
            log(f"⚠️ Error en consulta directa de platform: {e}")
    
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig and paso_actual == 'campana_intent' and text_lower in ["1", "2", "3", "4", "5"]:
        return manejar_intencion_campana(text_lower, estado_usuario, user_id)
    
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
    
    # ========== VENDER - FLUJO SECUENCIAL ==========
    elif paso_actual == 'vender_paso1_nombre':
        return manejar_vender_paso1_nombre(text, estado_usuario, user_id)
    
    elif paso_actual == 'vender_paso1_horario':  # ← NUEVO PASO
        return manejar_vender_paso1_horario(text_lower, estado_usuario, user_id)
    
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

    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana(platform)

# ========== MENÚ PRINCIPAL DE CAMPAÑA ==========

def iniciar_campana(platform=None):
    es_fb_ig = False
    if platform:
        platform_lower = str(platform).lower()
        es_fb_ig = platform_lower in ("messenger", "facebook", "instagram")
    
    cuerpo_base = (
        "¡Hola! 👋 Soy el asistente de Dante Propiedades.\n\n"
        "Estamos para acompañarte en todo el proceso de venta o tasación de tu propiedad.\n\n"
        "¿Te gustaría recibir una valoración gratuita o conocer las mejores oportunidades del mercado?\n\n"
        "Contame qué necesitás y te ayudo personalmente a avanzar."
    )
    
    if es_fb_ig:
        partes = [
            "¡Hola! 👋 Soy el asistente de Dante Propiedades ",
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
        rows = [
            {"id": "c_tasar", "title": "📈 Tasación Virtual Inteligente", "description": "Obtené un valor estimado de tu propiedad en segundos."},
            {"id": "c_comprar", "title": "🏡 Quiero Vender", "description": "Para propietarios que ya están decididos y quieren que publiques su propiedad."},
            {"id": "c_alquilar", "title": "🔑 Ver Propiedades Disponibles", "description": "Explorá nuestro catálogo actualizado en dantepropiedades.com.ar."},
            {"id": "c_asesor", "title": "👤 Asesoramiento Inmobiliario", "description": "Para consultas sobre trámites, contratos o asesoría técnica."}
        ]
        otras = [{"id": "c_salir", "title": "❌ Salir", "description": "Finalizar la conversación."}]
        
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
    _clear_campana_data(estado_usuario)
    data = {}
    platform = estado_usuario.get('platform')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    text_normalized = text.lower().strip()
    
    if es_fb_ig:
        opciones_numericas = {
            "1": "c_comprar", "2": "c_alquilar", "3": "c_tasar", "4": "c_asesor", "5": "c_salir",
            "uno": "c_comprar", "dos": "c_alquilar", "tres": "c_tasar", "cuatro": "c_asesor", "cinco": "c_salir",
            "comprar": "c_comprar", "vender": "c_comprar", "alquilar": "c_alquilar", "tasar": "c_tasar",
            "asesor": "c_asesor", "asesoramiento": "c_asesor", "salir": "c_salir"
        }
        if text_normalized in opciones_numericas:
            text_normalized = opciones_numericas[text_normalized]
    
    # ========== OPCIÓN 1: QUIERO VENDER ==========
    if text_normalized in ["c_comprar", "comprar", "vender", "quiero vender", "venta", "1"]:
        data['intencion'] = "Vender"
        estado_usuario['paso'] = 'vender_paso1_nombre'  # Cambia a paso1_nombre
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        # Solo pedir nombre, no horario
        return "📇 *Para comenzar, por favor confirmame tu nombre completo:*\n\n_(Ej: Juan Pérez, María González)_"
    
    # OPCIÓN 2: VER PROPIEDADES DISPONIBLES
    elif text_normalized in ["c_alquilar", "alquilar", "ver propiedades", "propiedades", "sitio web", "web", "catalogo", "2"]:
        sitio_web = "https://www.dantepropiedades.com.ar"
        cuerpo = f"🔍 *Catálogo de Propiedades*\n\nPodés explorar todas nuestras propiedades disponibles en nuestro sitio web:\n\n👉 {sitio_web}\n\n¿Necesitas ayuda con algo más?"
        if es_fb_ig:
            return {"type": "text", "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*", "preview": False}
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[{"id": "c_menu", "title": "📋 Volver al menú"}, {"id": "c_salir", "title": "❌ Salir"}],
                footer=PIE_MENU
            )
    
    # OPCIÓN 3: TASACIÓN
    elif text_normalized in ["c_tasar", "tasar", "tasacion", "valorar", "3", "tasación virtual", "tasación inteligente"]:
        from tasaciones import manejar_menu_tasacion
        return manejar_menu_tasacion(text, estado_usuario, user_id)
    
    # OPCIÓN 4: ASESORAMIENTO
    elif text_normalized in ["c_asesor", "asesor", "asesoramiento", "hablar con asesor", "contacto", "4"]:
        data['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        if es_fb_ig:
            return "👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para asesorarte.\n\nPor favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor:\n\n💡 *Envía 'M' para volver al menú o 'S' para salir.*"
        else:
            return f"👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para asesorarte.\n\nPor favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor: {HINT_SALIR}"
    
    # OPCIÓN 5: SALIR
    elif text_normalized in ["c_salir", "salir", "s", "exit", "0", "5"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    
    else:
        return iniciar_campana(platform)

# ========== VENDER - FLUJO SECUENCIAL ==========

def manejar_vender_paso1_nombre(text, estado_usuario, user_id):
    """Paso 1: Guarda el nombre y avanza a preguntar barrio"""
    data = _get_campana_data(estado_usuario)
    data['nombre_completo'] = text
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "nombre_completo", text)
    
    # Avanzar al paso de barrio
    estado_usuario['paso'] = 'vender_paso2_barrio'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return mostrar_lista_barrios_vender(estado_usuario, user_id)


     
        
def manejar_vender_paso2_barrio(text, estado_usuario, user_id):
    """Paso 2: Guarda el barrio y avanza a documentación"""
    from logic.constants import BARRIOS_VALIDOS
    
    text_stripped = text.strip()
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    barrio_seleccionado = None
    
    # Intentar por número
    if text_stripped.isdigit():
        idx = int(text_stripped) - 1
        if 0 <= idx < len(BARRIOS_VALIDOS):
            barrio_seleccionado = BARRIOS_VALIDOS[idx]
    
    # Intentar por nombre exacto o parcial
    if not barrio_seleccionado:
        for barrio in BARRIOS_VALIDOS:
            if barrio.lower() == text_stripped.lower():
                barrio_seleccionado = barrio
                break
        if not barrio_seleccionado:
            for barrio in BARRIOS_VALIDOS:
                if barrio.lower().startswith(text_stripped.lower()) or text_stripped.lower() in barrio.lower():
                    barrio_seleccionado = barrio
                    break
    
    if barrio_seleccionado:
        data = _get_campana_data(estado_usuario)
        data['barrio'] = barrio_seleccionado
        _set_campana_data(estado_usuario, data)
        guardar_lead_vender(user_id, data, "barrio", barrio_seleccionado)
        
        # Avanzar al paso 3: Documentación
        estado_usuario['paso'] = 'vender_paso3_documentacion'
        actualizar_estado_usuario(user_id, estado_usuario)
        
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
    else:
        # Barrio no reconocido, mostrar lista nuevamente
        return mostrar_lista_barrios_vender(estado_usuario, user_id)        
        
        
def mostrar_lista_barrios_vender(estado_usuario, user_id):
    """Muestra la lista de barrios para seleccionar"""
    from logic.constants import BARRIOS_VALIDOS
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        barrios_texto = ""
        for i, barrio in enumerate(BARRIOS_VALIDOS, 1):
            barrios_texto += f"{i}. {barrio}\n"
        
        return {
            "type": "text",
            "body": f"📍 *¿En qué barrio se encuentra tu propiedad?*\n\n{barrios_texto}\n💡 *Envía el número o el nombre del barrio*",
            "preview": False
        }
    else:
        rows = [{"id": barrio, "title": barrio} for barrio in BARRIOS_VALIDOS]
        
        return WhatsAppResponse.list_menu(
            header="📍 Selección de Barrio",
            body="*¿En qué barrio se encuentra tu propiedad?*\n\nSeleccioná una opción de la lista:",
            button_text="Ver barrios",
            sections=[{"title": "Barrios disponibles", "rows": rows}],
            footer="Selecciona tu barrio 👇"
        )

def manejar_vender_paso1_horario(text, estado_usuario, user_id):
    """Paso 1b: Guarda el horario y avanza a documentación"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    opciones = {
        "1": "Mañana (9 a 12hs)",
        "2": "Mediodía (12 a 15hs)",
        "3": "Tarde (15 a 18hs)",
        "4": "Noche (18 a 20hs)",
        "horario_manana": "Mañana (9 a 12hs)",
        "horario_mediodia": "Mediodía (12 a 15hs)",
        "horario_tarde": "Tarde (15 a 18hs)",
        "horario_noche": "Noche (18 a 20hs)"
    }
    
    # Normalizar para FB/IG
    if es_fb_ig and text.isdigit():
        text = opciones.get(text, text)
    
    horario = opciones.get(text, text)
    
    # Validar que sea una opción válida
    if horario not in ["Mañana (9 a 12hs)", "Mediodía (12 a 15hs)", "Tarde (15 a 18hs)", "Noche (18 a 20hs)"]:
        # Opción no válida, mostrar el menú nuevamente
        cuerpo = "📅 *¿En qué horario te gustaría que Dante te llame?*\n\nSeleccioná una opción válida:"
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{cuerpo}\n\n1. 🌅 Mañana (9 a 12hs)\n2. ☀️ Mediodía (12 a 15hs)\n3. 🌇 Tarde (15 a 18hs)\n4. 🌙 Noche (18 a 20hs)\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[
                    {"id": "horario_manana", "title": "🌅 Mañana (9-12hs)"},
                    {"id": "horario_mediodia", "title": "☀️ Mediodía (12-15hs)"},
                    {"id": "horario_tarde", "title": "🌇 Tarde (15-18hs)"},
                    {"id": "horario_noche", "title": "🌙 Noche (18-20hs)"}
                ],
                footer="Selecciona un horario 👇"
            )
    
    data = _get_campana_data(estado_usuario)
    data['horario_preferido'] = horario
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "horario_preferido", horario)
    
    # Avanzar al paso 2: Documentación
    estado_usuario['paso'] = 'vender_paso2_documentacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
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
    opciones = {"1": "Sí, la tengo", "2": "No, todavía no", "3": "Está en trámite",
                "doc_si": "Sí, la tengo", "doc_no": "No, todavía no", "doc_tramite": "Está en trámite"}
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['documentacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "documentacion", respuesta)
    
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
    opciones = {"1": "Sí, planos aprobados", "2": "No tiene planos", "3": "No estoy seguro",
                "detalles_si": "Sí, planos aprobados", "detalles_no": "No tiene planos", "detalles_duda": "No estoy seguro"}
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['detalles_tecnicos'] = respuesta
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "detalles_tecnicos", respuesta)
    
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
    opciones = {"1": "Habitada", "2": "Vacía", "3": "Alquilada",
                "ocupacion_habitada": "Habitada", "ocupacion_vacia": "Vacía", "ocupacion_alquilada": "Alquilada"}
    respuesta = opciones.get(text, text)
    data = _get_campana_data(estado_usuario)
    data['estado_ocupacion'] = respuesta
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "estado_ocupacion", respuesta)
    
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
    opciones = {"1": "Tengo un valor", "2": "Prefiero tasación profesional",
                "precio_valor": "Tengo un valor", "precio_tasacion": "Prefiero tasación profesional"}
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
    data = _get_campana_data(estado_usuario)
    data['precio_pretendido'] = text
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "precio_pretendido", text)
    
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
    opciones = {"1": "Mañana", "2": "Tarde", "3": "Fines de semana", "4": "Coordinar otro horario",
                "disponibilidad_manana": "Mañana", "disponibilidad_tarde": "Tarde",
                "disponibilidad_finde": "Fines de semana", "disponibilidad_otro": "Coordinar otro horario"}
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
        return finalizar_vender_y_notificar(user_id, estado_usuario, data)

def manejar_vender_paso6_disponibilidad_otro(text, estado_usuario, user_id):
    data = _get_campana_data(estado_usuario)
    data['disponibilidad'] = text
    _set_campana_data(estado_usuario, data)
    guardar_lead_vender(user_id, data, "disponibilidad", text)
    return finalizar_vender_y_notificar(user_id, estado_usuario, data)

def finalizar_vender_y_notificar(user_id, estado_usuario, data):
    detalles = []
    for key, value in data.items():
        if key != 'intencion':
            detalles.append(f"{key}: {value}")
    detalles_str = " | ".join(detalles)
    
    nombre = data.get('nombre_completo', f"Lead Venta {str(user_id)[-4:]}")
    guardar_lead_campana(user_id, data)
    
    mensaje_agente = f"🏠 *NUEVO LEAD DE VENTA* 🏠\n\n"
    mensaje_agente += f"👤 *Contacto:* {nombre}\n"
    mensaje_agente += f"📱 *WhatsApp:* +{user_id}\n"
    mensaje_agente += f"📋 *Detalles completos:*\n{detalles_str}\n\n"
    mensaje_agente += "👉 *Requiere seguimiento comercial.*"
    notificar_agente(mensaje_agente)
    
    estado_usuario['paso'] = 'campana_inicio'
    _clear_campana_data(estado_usuario)
    actualizar_estado_usuario(user_id, estado_usuario)
    
    mensaje_final = (
        "✅ *Perfecto, ya tenemos toda la información necesaria.*\n\n"
        "En breve un asesor de Dante Propiedades se va a comunicar con vos para coordinar los próximos pasos.\n\n"
        "¡Gracias por confiar en nosotros! 🏠🗝️"
    )
    
    return WhatsAppResponse.buttons(
        body=mensaje_final,
        buttons=[{"id": "c_menu", "title": "📋 Volver al menú"}, {"id": "c_salir", "title": "❌ Salir"}],
        footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
    )

# ========== RECOPILACIÓN DE DATOS ==========

def manejar_recopilacion_datos(text, estado_usuario, user_id):
    paso = estado_usuario['paso']
    data = _get_campana_data(estado_usuario)
    intencion = data.get('intencion')
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    if not intencion:
        estado_usuario['paso'] = 'campana_intent'
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana()
    
    if intencion in ["Comprar", "Alquilar"]:
        if paso == 'campana_recopilar_zona':
            data['zona'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            if es_fb_ig:
                return {"type": "text", "body": f"📍 Zona: *{text}* ✅\n\n¿Qué *tipo de propiedad* estás buscando?\n\n1️⃣ 🏢 Departamento\n2️⃣ 🏠 Casa\n3️⃣ 🏭 Otro (Local/Lote)\n\n💡 Envía el número de la opción deseada, 🔙 M para volver o ❌ S para salir.", "preview": False}
            else:
                return WhatsAppResponse.buttons(body=f"📍 Zona: *{text}* ✅\n\n¿Qué *tipo de propiedad* estás buscando?", buttons=[{"id": "Depto", "title": "🏢 Departamento"}, {"id": "Casa", "title": "🏠 Casa"}, {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}], footer=PIE_SELECCION)
        elif paso == 'campana_recopilar_tipo':
            texto_tipo = text
            if es_fb_ig:
                mapa_tipos = {"1": "Departamento", "2": "Casa", "3": "Otro", "1.": "Departamento", "2.": "Casa", "3.": "Otro"}
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
    elif intencion == "Tasar":
        if paso == 'campana_recopilar_direccion':
            data['direccion'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo_tasacion'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            if es_fb_ig:
                return {"type": "text", "body": f"📍 Dirección: *{text}* ✅\n\n¿Qué *tipo de propiedad* deseas tasar?\n\n1. 🏢 Departamento\n2. 🏠 Casa\n3. 🏭 Otro (Local/Lote)\n\n💡 Envía el número de la opción deseada, 'M' para volver al menú o 'S' para salir.", "preview": False}
            else:
                return WhatsAppResponse.buttons(body=f"📍 Dirección: *{text}* ✅\n\n¿Qué *tipo de propiedad* deseas tasar?", buttons=[{"id": "Depto", "title": "🏢 Departamento"}, {"id": "Casa", "title": "🏠 Casa"}, {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}], footer=PIE_MENU)
        elif paso == 'campana_recopilar_tipo_tasacion':
            texto_tipo = text
            if es_fb_ig:
                mapa_tipos = {"1": "Departamento", "2": "Casa", "3": "Otro", "1.": "Departamento", "2.": "Casa", "3.": "Otro"}
                texto_tipo = mapa_tipos.get(text.lower().strip(), text)
            data['tipo'] = texto_tipo
            estado_usuario['paso'] = 'campana_recopilar_estado'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            if es_fb_ig:
                return {"type": "text", "body": f"🏠 Tipo: *{texto_tipo}* ✅\n\n¿En qué *estado general* se encuentra la propiedad?\n\n1. ✨ Excelente\n2. 👍 Bueno/Refaccionar\n3. 🏗️ En obra/Terreno\n\n💡 Envía el número de la opción deseada, 'M' para volver al menú o 'S' para salir.", "preview": False}
            else:
                return WhatsAppResponse.buttons(body=f"🏠 Tipo: *{texto_tipo}* ✅\n\n¿En qué *estado general* se encuentra la propiedad?", buttons=[{"id": "Excelente", "title": "✨ Excelente"}, {"id": "Bueno", "title": "👍 Bueno/Refaccionar"}, {"id": "En_obra", "title": "🏗️ En obra/Terreno"}], footer=PIE_MENU)
        elif paso == 'campana_recopilar_estado':
            texto_estado = text
            if es_fb_ig:
                mapa_estados = {"1": "Excelente", "2": "Bueno", "3": "En_obra", "1.": "Excelente", "2.": "Bueno", "3.": "En_obra"}
                texto_estado = mapa_estados.get(text.lower().strip(), text)
            data['estado_propiedad'] = texto_estado
            estado_usuario['paso'] = 'campana_confirmacion'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            return mostrar_resumen_campana(data)
    
    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana()

# ========== NOMBRE PARA ASESOR ==========

def manejar_pedir_nombre_asesor(text, estado_usuario, user_id):
    data = _get_campana_data(estado_usuario)
    data['nombre'] = text
    guardar_lead_campana(user_id, data)
    estado_usuario['paso'] = 'campana_inicio'
    _clear_campana_data(estado_usuario)
    actualizar_estado_usuario(user_id, estado_usuario)
    return WhatsAppResponse.buttons(
        body=f"✅ *¡Gracias, {text}!*\n\nHemos derivado tu contacto a un asesor de guardia, quien se comunicará contigo a la brevedad por este WhatsApp.\n\n{LOGO} Dante Propiedades\n\n1️⃣ Volver al menú\n2️⃣ Salir",
        buttons=[{"id": "c_menu", "title": "1️⃣ 📋 Volver al menú"}, {"id": "c_salir", "title": "2️⃣ ❌ Salir"}],
        footer=PIE_MENU
    )

# ========== RESUMEN Y CONFIRMACIÓN ==========

def mostrar_resumen_campana(data):
    intencion = data.get('intencion')
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
        guardar_lead_campana(user_id, data)
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        if intencion == "Tasar":
            msg_base = "✅ *¡Solicitud registrada!*\n\nUn tasador experto de nuestro equipo se pondrá en contacto contigo muy pronto para brindarte el valor real de tu propiedad."
        else:
            msg_base = "✅ *¡Búsqueda registrada!*\n\nUn asesor especializado está analizando nuestra base de datos (incluso propiedades off-market) y se contactará contigo a la brevedad con las mejores opciones a medida."
        msg = f"{msg_base}\n\n{DESPEDIDA}"
        if es_fb_ig:
            return {"type": "text", "body": f"{msg}\n\n1️⃣ 📋 Nueva búsqueda\n2️⃣ ❌ Salir\n\n{PIE_MENU}\n\n💡 *Envía el número de la opción deseada*", "preview": False}
        else:
            return WhatsAppResponse.buttons(body=msg, buttons=[{"id": "c_menu", "title": "📋 Nueva búsqueda"}, {"id": "c_salir", "title": "❌ Salir"}], footer=PIE_MENU)
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
                return {"type": "text", "body": f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_\n\n💡 *Envía 'M' para volver al menú o 'S' para salir.*", "preview": False}
            else:
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_{HINT_SALIR}"
        elif intencion == "Tasar":
            estado_usuario['paso'] = 'campana_recopilar_direccion'
            _set_campana_data(estado_usuario, {'intencion': intencion})
            actualizar_estado_usuario(user_id, estado_usuario)
            if es_fb_ig:
                return {"type": "text", "body": f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿Cuál es la *dirección o zona* de la propiedad a tasar?\n_(Ej: Av. Rivadavia 5000, Caballito)_\n\n💡 *Envía 'M' para volver al menú o 'S' para salir.*", "preview": False}
            else:
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿Cuál es la *dirección o zona* de la propiedad a tasar?\n_(Ej: Av. Rivadavia 5000, Caballito)_{HINT_SALIR}"
    elif text in ["c_salir", "salir", "cancelar", "3"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    else:
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        if es_fb_ig:
            return {"type": "text", "body": "¿Estos datos son correctos?\n\n1️⃣ ✅ Confirmar\n2️⃣ 🔄 Corregir\n3️⃣ ❌ Cancelar\n\n💡 *Envía el número de la opción deseada*", "preview": False}
        else:
            return WhatsAppResponse.buttons(body="Por favor, confirmá si los datos son correctos:", buttons=[{"id": "confirmar_datos", "title": "✅ Confirmar"}, {"id": "corregir_datos", "title": "🔄 Corregir"}, {"id": "c_salir", "title": "❌ Cancelar"}], footer=PIE_MENU)

# ========== PERSISTENCIA DE LEADS ==========

def guardar_lead_campana(user_id, data):
    intencion = data.get('intencion', 'Desconocida')
    nombre = data.get('nombre_completo') or data.get('nombre', f"Lead {str(user_id)[-4:]}")
    accion = f"lead_campaña_{intencion.lower()}"
    detalles_lista = [f"{k.capitalize()}: {v}" for k, v in data.items() if k not in ['intencion', 'nombre', 'nombre_completo']]
    detalles_str = " | ".join(detalles_lista)
    
    try:
        lead_id_pg = guardar_en_postgresql(user_id, nombre, accion, detalles_str)
        if lead_id_pg:
            log(f"✅ Lead de campaña guardado en PostgreSQL (ID: {lead_id_pg}): {user_id} - {intencion}")
        else:
            log(f"⚠️ PostgreSQL no disponible para lead de campaña: {user_id} - {intencion}", "WARNING")
    except Exception as e:
        log(f"⚠️ Error guardando lead de campaña en PostgreSQL: {e}", "WARNING")
    
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
        nuevo_lead = {'timestamp': datetime.now().isoformat(), 'user_id': user_id, 'propiedad_id': '', 'accion': accion, 'detalle': detalles_str, 'propiedad_nombre': f"Campaña: {intencion}", 'nombre': nombre}
        leads.append(nuevo_lead)
        save_json_atomic(LEADS_FILE, leads)
        log(f"✅ Lead de campaña guardado en JSON: {user_id} - {intencion}")
    except Exception as e:
        log(f"🔥 Error guardando lead de campaña en JSON: {e}", "ERROR")
    
    mensaje_agente = f"🚨 *NUEVO LEAD DE CAMPAÑA* 🚨\n\n👤 *Nombre:* {nombre}\n📱 *WhatsApp:* +{user_id}\n🎯 *Intención:* {intencion}\n\n📝 *Detalles:*\n{detalles_str}\n\n👉 *Requiere contacto inmediato.*"
    notificar_agente(mensaje_agente)

def guardar_lead_vender(user_id, data, paso, valor):
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
        nombre = data.get('nombre_completo') or data.get('nombre_horario', f"Lead Venta {str(user_id)[-4:]}")
        nuevo_lead = {'timestamp': datetime.now().isoformat(), 'user_id': user_id, 'propiedad_id': '', 'accion': f"venta_{paso}", 'detalle': valor, 'propiedad_nombre': f"Venta - {paso}", 'nombre': nombre}
        leads.append(nuevo_lead)
        save_json_atomic(LEADS_FILE, leads)
        log(f"✅ Progreso de venta guardado: {user_id} - {paso}: {valor}")
    except Exception as e:
        log(f"⚠️ Error guardando progreso de venta: {e}", "WARNING")