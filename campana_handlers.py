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


def get_bot_response_campana(text, user_id, platform=None):
    """
    Despachador principal para el MODO CAMPAÑA (TIPO_MENU = 1).
    """
    text_lower = text.lower().strip()
    
    # Obtener estado del usuario SIEMPRE fresco
    estado_usuario = obtener_estado_usuario(user_id)
    paso_actual = estado_usuario.get('paso', 'campana_inicio')
    
    # Usar la plataforma real del webhook cuando esté disponible; si no, caer al estado guardado.
    if not platform:
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
        
    elif paso_actual.startswith('tasacion_'):
        from tasaciones import (
            manejar_tasacion_operacion, manejar_tasacion_barrio, 
            manejar_tasacion_tipo, manejar_tasacion_m2, 
            manejar_tasacion_ambientes, manejar_tasacion_estado, 
            manejar_tasacion_contacto
        )
        resp = None
        if paso_actual == 'tasacion_operacion':
            resp = manejar_tasacion_operacion(text_lower, estado_usuario, user_id)
        elif paso_actual == 'tasacion_barrio':
            resp = manejar_tasacion_barrio(text, estado_usuario, user_id)
        elif paso_actual == 'tasacion_tipo':
            resp = manejar_tasacion_tipo(text_lower, estado_usuario, user_id)
        elif paso_actual == 'tasacion_m2':
            resp = manejar_tasacion_m2(text, estado_usuario, user_id)
        elif paso_actual == 'tasacion_ambientes':
            resp = manejar_tasacion_ambientes(text, estado_usuario, user_id)
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
        "¡Hola! Bienvenido a **Dante Propiedades Inmobiliaria**. Soy tu asistente inteligente. "
        "¿En qué puedo ayudarte hoy? Por favor, elegí una opción enviando el número:\n\n"
        "1. **Tasación Virtual Inteligente:** Obtené un valor estimado de tu propiedad en segundos.\n"
        "2. **Quiero Vender:** Iniciá el proceso para que publiquemos tu inmueble.\n"
        "3. **Ver Propiedades:** Explorá nuestro catálogo en dantepropiedades.com.ar.\n"
        "4. **Asesoramiento:** Consultas sobre trámites, contratos o tasaciones profesionales.\n"
        "5. **Hablar con Dante:** Si necesitás atención personalizada inmediata."
    )
    
    if es_fb_ig:
        cuerpo_plano = (
            "¡Hola! Bienvenido a Dante Propiedades Inmobiliaria. Soy tu asistente inteligente. "
            "¿En qué puedo ayudarte hoy? Por favor, elegí una opción enviando el número:\n\n"
            "1. Tasación Virtual Inteligente: Obtené un valor estimado de tu propiedad en segundos.\n"
            "2. Quiero Vender: Iniciá el proceso para que publiquemos tu inmueble.\n"
            "3. Ver Propiedades: Explorá nuestro catálogo en dantepropiedades.com.ar\n"
            "4. Asesoramiento: Consultas sobre trámites, contratos o tasaciones profesionales.\n"
            "5. Hablar con Dante: Si necesitás atención personalizada inmediata."
        )
        return {"type": "text", "body": cuerpo_plano, "preview": False}

    rows = [
        {"id": "c_tasar", "title": "1️⃣ Tasación Virtual Inteligente", "description": "Obtené un valor estimado de tu propiedad en segundos"},
        {"id": "c_vender", "title": "2️⃣ Quiero Vender", "description": "Iniciá el proceso para publicar tu inmueble"},
        {"id": "c_propiedades", "title": "3️⃣ Ver Propiedades", "description": "Explorá nuestro catálogo"},
        {"id": "c_asesor", "title": "4️⃣ Asesoramiento", "description": "Consultas sobre trámites, contratos o tasaciones"},
        {"id": "c_dante", "title": "5️⃣ Hablar con Dante", "description": "Atención personalizada inmediata"}
    ]

    return WhatsAppResponse.list_menu(
        header="Dante Propiedades 🏠🗝️",
        body=cuerpo_base,
        button_text="Ver opciones",
        sections=[
            {"title": "Opciones disponibles", "rows": rows}
        ],
        footer=PIE_MENU
    )
        
# ========== MANEJO DE INTENCIÓN ==========

def manejar_intencion_campana(text, estado_usuario, user_id):
    """Maneja la selección de intención en el menú principal de campaña"""
    _clear_campana_data(estado_usuario)
    data = {}
    
    # Obtener platform fresco para no depender de un valor viejo guardado en DB.
    from database import obtener_estado_usuario as get_fresh_state
    fresh_state = get_fresh_state(user_id)
    platform = fresh_state.get('platform') or estado_usuario.get('platform')
    if estado_usuario.get('platform') != platform:
        estado_usuario['platform'] = platform
        actualizar_estado_usuario(user_id, estado_usuario)
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    log(f"🔍 manejar_intencion_campana - platform: {platform}, es_fb_ig: {es_fb_ig}")
    
    # Normalizar el texto recibido
    text_normalized = text.lower().strip()
    
    # Mapeo de opciones numéricas para el menú de campaña
    opciones_numericas = {
        "1": "c_tasar",
        "2": "c_vender",
        "3": "c_propiedades",
        "4": "c_asesor",
        "5": "c_dante",
        "uno": "c_tasar",
        "dos": "c_vender",
        "tres": "c_propiedades",
        "cuatro": "c_asesor",
        "cinco": "c_dante",
        "tasacion": "c_tasar",
        "tasación": "c_tasar",
        "tasar": "c_tasar",
        "vender": "c_vender",
        "venta": "c_vender",
        "propiedades": "c_propiedades",
        "ver propiedades": "c_propiedades",
        "catalogo": "c_propiedades",
        "asesoramiento": "c_asesor",
        "asesor": "c_asesor",
        "hablar con dante": "c_dante",
        "dante": "c_dante",
        "salir": "c_salir"
    }

    if text_normalized in opciones_numericas:
        text_normalized = opciones_numericas[text_normalized]
        log(f"🔄 Conversión numérica: '{text}' -> '{text_normalized}'")
    
    if text_normalized in ["c_vender", "vender", "venta", "quiero vender"]:
        data['intencion'] = "Vender"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        return (
            "🏠🗝️ *¡Perfecto! Quiero ayudarte a vender tu propiedad.*\n\n"
            "Un asesor de Dante Propiedades te contactará para coordinar una evaluación inicial.\n\n"
            "Por favor, enviá tu *Nombre y Apellido* para empezar:"
        )

    if text_normalized in ["c_propiedades", "propiedades", "ver propiedades", "catalogo"]:
        return (
            "🏡 *Explorá nuestro catálogo:*\n\n"
            "https://www.dantepropiedades.com.ar\n\n"
            "Si querés, también podés escribir 'M' para volver al menú o 'S' para salir."
        )

    if text_normalized in ["c_dante", "dante", "hablar con dante", "hablar con asesor"]:
        data['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        return (
            "👤 *¡Genial!* Un asesor experto de Dante Propiedades te atenderá a la brevedad.\n\n"
            "Por favor, enviá tu *Nombre y Apellido* para que podamos ayudarte mejor:"
        )

    if text_normalized in ["c_comprar", "comprar", "quiero comprar", "compra"]:
        data['intencion'] = "Comprar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return (
                f"🏠🗝️ *¡Excelente elección!* Te ayudaremos a encontrar el hogar ideal.\n\n"
                f"📍 ¿En qué *barrio o zona* te gustaría comprar?\n"
                f"_(Ej: Caballito, Palermo, Belgrano)_\n\n"
                f"💡 *Envía 'M' para volver al menú o 'S' para salir.*"
            )
        else:
            return (
                f"🏠🗝️ *¡Excelente elección!* Te ayudaremos a encontrar el hogar ideal.\n\n"
                f"📍 ¿En qué *barrio o zona* te gustaría comprar?\n"
                f"_(Ej: Caballito, Palermo, Belgrano)_ {HINT_SALIR}\n\n"
                "Contame tus preferencias y te acompaño en todo el proceso."
            )
        
    elif text_normalized in ["c_alquilar", "alquilar", "quiero alquilar", "alquiler"]:
        data['intencion'] = "Alquilar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return (
                f"🏠🗝️ *¡Perfecto!* Vamos a buscar juntos el alquiler ideal para vos.\n\n"
                f"📍 ¿En qué *barrio o zona* estás buscando?\n"
                f"_(Ej: Almagro, Villa Crespo, Belgrano)_\n\n"
                f"💡 *Envía 'M' para volver al menú o 'S' para salir.*"
            )
        else:
            return (
                f"🏠🗝️ *¡Perfecto!* Vamos a buscar juntos el alquiler ideal para vos.\n\n"
                f"📍 ¿En qué *barrio o zona* estás buscando?\n"
                f"_(Ej: Almagro, Villa Crespo, Belgrano)_ {HINT_SALIR}\n\n"
                "Contame tus preferencias y te acompaño en todo el proceso."
            )
        
    elif text_normalized in ["c_tasar", "tasar", "tasacion", "valorar", "3"]:
        from tasaciones import manejar_menu_tasacion
        return manejar_menu_tasacion(text, estado_usuario, user_id)
        
    elif text_normalized in ["c_asesor", "asesor", "hablar con asesor", "asesoramiento", "contacto", "4"]:
        data['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if es_fb_ig:
            return (
                "👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para acompañarte personalmente.\n\n"
                f"Por favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor:\n\n"
                f"💡 *Envía 'M' para volver al menú o 'S' para salir.*"
            )
        else:
            return (
                "👤 *¡Genial!* Un asesor experto de Dante Propiedades 🏠🗝️ te contactará a la brevedad para acompañarte personalmente.\n\n"
                f"Por favor, decime tu *Nombre y Apellido* para que podamos ayudarte mejor: {HINT_SALIR}"
            )
    
    elif text_normalized in ["c_salir", "salir", "s", "exit", "0", "5"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
        
    else:
        log(f"⚠️ Opción no reconocida en campaña: '{text}' - Mostrando menú nuevamente")
        return iniciar_campana(platform)
# ========== RECOPILACIÓN DE DATOS ==========

def manejar_recopilacion_datos(text, estado_usuario, user_id):
    paso = estado_usuario['paso']
    data = _get_campana_data(estado_usuario)
    intencion = data.get('intencion')
    
    # Obtener platform fresco para saber qué formato usar.
    from database import obtener_estado_usuario as get_fresh_state
    fresh_state = get_fresh_state(user_id)
    platform = fresh_state.get('platform') or estado_usuario.get('platform', 'whatsapp')
    if estado_usuario.get('platform') != platform:
        estado_usuario['platform'] = platform
        actualizar_estado_usuario(user_id, estado_usuario)
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
