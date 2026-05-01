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
HINT_SALIR = "\n\n💡 _Envía 'S' para salir o 'M' para volver al menú._"

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
        "¡Hola! 👋 Soy el asistente de *Dante Propiedades* 🏠🗝️.\n\n"
        "Estamos para acompañarte en todo el proceso de *compra, venta o tasación* de tu propiedad.\n\n"
        "¿Te gustaría recibir una *valoración gratuita* o conocer las mejores oportunidades del mercado?\n\n"
        "*Contame qué necesitás y te ayudo personalmente a avanzar.*"
    )
    
    if es_fb_ig:
        # Facebook/Instagram: texto plano SIN asteriscos (no soporta markdown)
        cuerpo_menu = (
            f"{cuerpo_base}\n\n"
            "Servicios Disponibles\n"
            "1. 🏡 Quiero Comprar - Busco comprar una propiedad\n"
            "2. 🔑 Quiero Alquilar - Busco alquilar una propiedad\n"
            "3. 📈 Tasar mi Propiedad - Quiero saber el valor de mercado (¡gratis!)\n"
            "4. 👤 Hablar con Asesor - Atención personalizada inmediata\n\n"
            "Otras Opciones\n"
            "5. ❌ Salir - Finalizar la conversación\n\n"
            f"{PIE_MENU}\n\n"
            "💡 Envía el número de la opción deseada"
        )
        
        return {
            "type": "text",
            "body": cuerpo_menu,
            "preview": False
        }
    else:
        # WhatsApp: lista interactiva
        rows = [
            {"id": "c_comprar", "title": "🏡 Quiero Comprar", "description": "Busco comprar una propiedad"},
            {"id": "c_alquilar", "title": "🔑 Quiero Alquilar", "description": "Busco alquilar una propiedad"},
            {"id": "c_tasar", "title": "📈 Tasar mi Propiedad", "description": "Quiero saber el valor de mercado (¡gratis!)"},
            {"id": "c_asesor", "title": "👤 Hablar con Asesor", "description": "Atención personalizada inmediata"}
        ]
        otras = [
            {"id": "c_salir", "title": "❌ Salir", "description": "Finalizar la conversación"}
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
            "alquilar": "c_alquilar",
            "tasar": "c_tasar",
            "asesor": "c_asesor",
            "salir": "c_salir"
        }
        
        if text_normalized in opciones_numericas:
            text_normalized = opciones_numericas[text_normalized]
            log(f"🔄 Conversión numérica: '{text}' -> '{text_normalized}'")
    
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
                    "body": f"📍 Zona: {text} ✅\n\n¿Qué tipo de propiedad estás buscando?\n\n1. 🏢 Departamento\n2. 🏠 Casa\n3. 🏭 Otro (Local/Lote)\n\n💡 Envía el número de la opción deseada, M para volver al menú o S para salir.",
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
                    footer=PIE_MENU
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
                return f"🏠 Tipo: *{texto_tipo}* ✅\n\nPor último, ¿cuál es tu *presupuesto máximo* estimado en {moneda}?\n_(Ej: 100.000, 500k, etc.)_\n\n💡 Envía 'M' para volver al menú o 'S' para salir."
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
    
    resumen += "\n━━━━━━━━━━━━━━━━━\n¿Estos datos son correctos?\n\n1️⃣ Confirmar\n2️⃣ Corregir\n3️⃣ Cancelar"

    return WhatsAppResponse.buttons(
        body=resumen,
        buttons=[
            {"id": "confirmar_datos", "title": "1️⃣ ✅ Sí, confirmar"},
            {"id": "corregir_datos", "title": "2️⃣ 🔄 Corregir"},
            {"id": "c_salir", "title": "3️⃣ ❌ Cancelar"}
        ],
        footer=PIE_MENU
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
        
        if intencion == "Tasar":
            msg = f"✅ *¡Solicitud registrada!*\n\nUn tasador experto de nuestro equipo se pondrá en contacto contigo muy pronto para brindarte el valor real de tu propiedad.\n\n{DESPEDIDA}"
        else:
            msg = f"✅ *¡Búsqueda registrada!*\n\nUn asesor especializado está analizando nuestra base de datos (incluso propiedades off-market) y se contactará contigo a la brevedad con las mejores opciones a medida.\n\n{DESPEDIDA}"
        
        return WhatsAppResponse.buttons(
            body=msg + "\n\n1️⃣ Nueva búsqueda\n2️⃣ Salir",
            buttons=[
                {"id": "c_menu", "title": "1️⃣ 📋 Nueva búsqueda"},
                {"id": "c_salir", "title": "2️⃣ ❌ Salir"}
            ],
            footer=PIE_MENU
        )
            
    elif text in ["corregir_datos", "2", "no", "corregir"]:
        data = _get_campana_data(estado_usuario)
        intencion = data.get('intencion')
        
        if intencion in ["Comprar", "Alquilar"]:
            # Reiniciar a la primera pregunta de búsqueda
            estado_usuario['paso'] = 'campana_recopilar_zona'
            # Mantener solo la intención
            _set_campana_data(estado_usuario, {'intencion': intencion})
            actualizar_estado_usuario(user_id, estado_usuario)
            
            if intencion == "Comprar":
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_{HINT_SALIR}"
            else:
                return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿En qué *barrio o zona* estás buscando?\n_(Ej: Almagro, Villa Crespo, Belgrano)_{HINT_SALIR}"
                
        elif intencion == "Tasar":
            estado_usuario['paso'] = 'campana_recopilar_direccion'
            _set_campana_data(estado_usuario, {'intencion': intencion})
            actualizar_estado_usuario(user_id, estado_usuario)
            return f"{LOGO} *Vamos a corregir los datos.*\n\n📍 ¿Cuál es la *dirección o zona* de la propiedad a tasar?\n_(Ej: Av. Rivadavia 5000, Caballito)_{HINT_SALIR}"
            
        else:
            # Fallback a inicio si no hay intención clara
            estado_usuario['paso'] = 'campana_intent'
            _clear_campana_data(estado_usuario)
            actualizar_estado_usuario(user_id, estado_usuario)
            return iniciar_campana()
    
    elif text in ["c_salir", "salir", "cancelar", "3"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
        
    return WhatsAppResponse.buttons(
        body="Por favor, confirmá si los datos son correctos:",
        buttons=[
            {"id": "confirmar_datos", "title": "✅ Sí, confirmar"},
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
