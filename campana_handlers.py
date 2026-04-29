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
    Orientado exclusivamente a la captación de leads en frío.
    """
    text_lower = text.lower().strip()
    estado_usuario = obtener_estado_usuario(user_id)
    paso_actual = estado_usuario.get('paso', 'campana_inicio')
    
    # ========== COMANDOS GLOBALES (siempre disponibles) ==========
    if text_lower in ["salir", "s", "exit", "0"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    
    if text_lower in ["menu", "m", "volver", "inicio", "hola", "hi", "hello", "atras"]:
        estado_usuario['paso'] = 'campana_intent'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana()

    # ========== ROUTING POR PASO ==========
    if paso_actual in ('campana_inicio', 'menu_principal'):
        estado_usuario['paso'] = 'campana_intent'
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana()
        
    elif paso_actual == 'campana_intent':
        return manejar_intencion_campana(text_lower, estado_usuario, user_id)
        
    elif paso_actual.startswith('campana_recopilar_'):
        return manejar_recopilacion_datos(text, estado_usuario, user_id)
        
    elif paso_actual == 'campana_confirmacion':
        return manejar_confirmacion_campana(text_lower, estado_usuario, user_id)
        
    elif paso_actual == 'campana_pedir_nombre':
        return manejar_pedir_nombre_asesor(text, estado_usuario, user_id)

    # Fallback → menú principal
    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana()


# ========== MENÚ PRINCIPAL DE CAMPAÑA ==========

def iniciar_campana():
    return WhatsAppResponse.list_menu(
        header=MARCA,
        body=f"¡Hola! 👋 Soy el asistente de *Dante Propiedades*.\n\nEstamos acá para ayudarte a encontrar, vender o tasar tu propiedad de forma rápida y personalizada.\n\n*¿Qué te gustaría hacer hoy?*",
        button_text="Ver opciones",
        sections=[
            {
                "title": "Servicios Disponibles",
                "rows": [
                    {"id": "c_comprar", "title": "🏡 Quiero Comprar", "description": "Busco comprar una propiedad"},
                    {"id": "c_alquilar", "title": "🔑 Quiero Alquilar", "description": "Busco alquilar una propiedad"},
                    {"id": "c_tasar", "title": "📈 Tasar mi Propiedad", "description": "Quiero saber el valor de mercado"},
                    {"id": "c_asesor", "title": "👤 Hablar con Asesor", "description": "Atención personalizada inmediata"}
                ]
            },
            {
                "title": "Otras Opciones",
                "rows": [
                    {"id": "c_salir", "title": "❌ Salir", "description": "Finalizar la conversación"}
                ]
            }
        ],
        footer=PIE_MENU
    )


# ========== MANEJO DE INTENCIÓN ==========

def manejar_intencion_campana(text, estado_usuario, user_id):
    _clear_campana_data(estado_usuario)
    data = {}
    
    if text in ["c_comprar", "comprar", "1"]:
        data['intencion'] = "Comprar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"{LOGO} *¡Excelente!* Vamos a buscar tu nuevo hogar.\n\n📍 ¿En qué *barrio o zona* te gustaría comprar?\n_(Ej: Caballito, Palermo, Belgrano)_{HINT_SALIR}"
        
    elif text in ["c_alquilar", "alquilar", "2"]:
        data['intencion'] = "Alquilar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"{LOGO} *¡Perfecto!* Te ayudaremos a encontrar un alquiler.\n\n📍 ¿En qué *barrio o zona* estás buscando?\n_(Ej: Almagro, Villa Crespo, Belgrano)_{HINT_SALIR}"
        
    elif text in ["c_tasar", "tasar", "3"]:
        # Unificar flujo de tasación con Tipo_Menu=0
        from tasaciones import manejar_menu_tasacion
        return manejar_menu_tasacion(text, estado_usuario, user_id)
        
    elif text in ["c_asesor", "asesor", "hablar con asesor", "4"]:
        data['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        _set_campana_data(estado_usuario, data)
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"👤 Con gusto te contactaremos con uno de nuestros expertos.\n\nPor favor, decime tu *Nombre y Apellido*:{HINT_SALIR}"
    
    elif text in ["c_salir", "salir", "s", "exit", "0"]:
        estado_usuario['paso'] = 'campana_inicio'
        _clear_campana_data(estado_usuario)
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
        
    else:
        return iniciar_campana()


# ========== RECOPILACIÓN DE DATOS ==========

def manejar_recopilacion_datos(text, estado_usuario, user_id):
    paso = estado_usuario['paso']
    data = _get_campana_data(estado_usuario)
    intencion = data.get('intencion')
    
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
            data['tipo'] = text
            estado_usuario['paso'] = 'campana_recopilar_presupuesto'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            moneda = "USD" if intencion == "Comprar" else "ARS/USD"
            return f"🏠 Tipo: *{text}* ✅\n\nPor último, ¿cuál es tu *presupuesto máximo* estimado en {moneda}?\n_(Ej: 100.000, 500k, etc.)_{HINT_SALIR}"
            
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
            data['tipo'] = text
            estado_usuario['paso'] = 'campana_recopilar_estado'
            _set_campana_data(estado_usuario, data)
            actualizar_estado_usuario(user_id, estado_usuario)
            return WhatsAppResponse.buttons(
                body=f"🏠 Tipo: *{text}* ✅\n\n¿En qué *estado general* se encuentra la propiedad?",
                buttons=[
                    {"id": "Excelente", "title": "✨ Excelente"},
                    {"id": "Bueno", "title": "👍 Bueno/Refaccionar"},
                    {"id": "En_obra", "title": "🏗️ En obra/Terreno"}
                ],
                footer=PIE_MENU
            )
            
        elif paso == 'campana_recopilar_estado':
            data['estado_propiedad'] = text
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
        body=f"✅ *¡Gracias, {text}!*\n\nHemos derivado tu contacto a un asesor de guardia, quien se comunicará contigo a la brevedad por este WhatsApp.\n\n{LOGO} Dante Propiedades",
        buttons=[
            {"id": "c_menu", "title": "📋 Volver al menú"},
            {"id": "c_salir", "title": "❌ Salir"}
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
    
    resumen += "\n━━━━━━━━━━━━━━━━━\n¿Estos datos son correctos?"
    
    return WhatsAppResponse.buttons(
        body=resumen,
        buttons=[
            {"id": "confirmar_datos", "title": "✅ Sí, confirmar"},
            {"id": "corregir_datos", "title": "🔄 Corregir"},
            {"id": "c_salir", "title": "❌ Cancelar"}
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
            body=msg,
            buttons=[
                {"id": "c_menu", "title": "📋 Nueva búsqueda"},
                {"id": "c_salir", "title": "❌ Salir"}
            ],
            footer=PIE_MENU
        )
            
    elif text in ["corregir_datos", "2", "no", "corregir"]:
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
    
    accion = f"lead_campana_{intencion.lower()}"
    
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
