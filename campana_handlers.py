import json
from config import *
from utils import log, normalizar_numero_argentina
from database import obtener_estado_usuario, actualizar_estado_usuario, guardar_en_postgresql
from logic.response_builder import WhatsAppResponse
from whatsapp_api import notificar_agente

def get_bot_response_campana(text, user_id):
    """
    Despachador principal para el MODO CAMPAÑA (TIPO_MENU = 1).
    Orientado exclusivamente a la captación de leads en frío.
    """
    text_lower = text.lower().strip()
    estado_usuario = obtener_estado_usuario(user_id)
    paso_actual = estado_usuario.get('paso', 'campana_inicio')
    
    # Comandos globales
    if text_lower in ["salir", "s", "0"]:
        return reiniciar_campana(user_id, estado_usuario, "❌ Gracias por contactar a Dante Propiedades. ¡Hasta pronto!")
    
    if text_lower in ["menu", "m", "volver", "inicio"]:
        return reiniciar_campana(user_id, estado_usuario, iniciar_campana())

    # Routing basado en el paso actual
    if paso_actual == 'campana_inicio' or paso_actual == 'menu_principal':
        # Si vienen del menú principal estándar o están recién empezando
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

    # Fallback
    estado_usuario['paso'] = 'campana_intent'
    actualizar_estado_usuario(user_id, estado_usuario)
    return iniciar_campana()

def iniciar_campana():
    return WhatsAppResponse.list_menu(
        header="🏠🗝️ DANTE PROPIEDADES",
        body="¡Hola! Soy el asistente inmobiliario de Dante Propiedades.\nQueremos ayudarte a encontrar o vender tu lugar ideal de la forma más fácil y rápida.\n\n*¿Qué estás buscando hacer hoy?*",
        button_text="Seleccionar opción",
        sections=[
            {
                "title": "Opciones Disponibles",
                "rows": [
                    {"id": "c_comprar", "title": "🏡 Comprar", "description": "Busco comprar una propiedad"},
                    {"id": "c_alquilar", "title": "🔑 Alquilar", "description": "Busco alquilar una propiedad"},
                    {"id": "c_tasar", "title": "📈 Tasar mi propiedad", "description": "Quiero saber cuánto vale mi propiedad"},
                    {"id": "c_asesor", "title": "👤 Hablar con asesor", "description": "Necesito atención personalizada"}
                ]
            }
        ],
        footer="Selecciona una opción 👇"
    )

def reiniciar_campana(user_id, estado_usuario, mensaje):
    estado_usuario['paso'] = 'campana_inicio'
    estado_usuario['data_campana'] = {}
    actualizar_estado_usuario(user_id, estado_usuario)
    return mensaje

def manejar_intencion_campana(text, estado_usuario, user_id):
    estado_usuario['data_campana'] = {}
    
    if text in ["c_comprar", "comprar", "1"]:
        estado_usuario['data_campana']['intencion'] = "Comprar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Excelente! 🏡 Vamos a buscar tu nuevo hogar.\n\n¿En qué *barrio o zona* te gustaría comprar? (Ej: Caballito, Palermo, Belgrano)"
        
    elif text in ["c_alquilar", "alquilar", "2"]:
        estado_usuario['data_campana']['intencion'] = "Alquilar"
        estado_usuario['paso'] = 'campana_recopilar_zona'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Perfecto! 🔑 Te ayudaremos a encontrar un alquiler.\n\n¿En qué *barrio o zona* estás buscando? (Ej: Almagro, Villa Crespo)"
        
    elif text in ["c_tasar", "tasar", "3"]:
        estado_usuario['data_campana']['intencion'] = "Tasar"
        estado_usuario['paso'] = 'campana_recopilar_direccion'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Genial! 📈 Nuestros expertos tasarán tu propiedad al valor real de mercado.\n\nPor favor, decime la *dirección aproximada* o barrio de la propiedad:"
        
    elif text in ["c_asesor", "asesor", "hablar con asesor", "4"]:
        estado_usuario['data_campana']['intencion'] = "Asesoramiento"
        estado_usuario['paso'] = 'campana_pedir_nombre'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "Con gusto te contactaremos con uno de nuestros expertos. 👤\n\nPor favor, decime tu *Nombre y Apellido*:"
        
    else:
        return iniciar_campana()

def manejar_recopilacion_datos(text, estado_usuario, user_id):
    paso = estado_usuario['paso']
    data = estado_usuario.get('data_campana', {})
    intencion = data.get('intencion')
    
    # FLUJO: COMPRAR / ALQUILAR
    if intencion in ["Comprar", "Alquilar"]:
        if paso == 'campana_recopilar_zona':
            data['zona'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo'
            actualizar_estado_usuario(user_id, estado_usuario)
            return WhatsAppResponse.buttons(
                body="¿Qué *tipo de propiedad* estás buscando?",
                buttons=[
                    {"id": "Depto", "title": "🏢 Departamento"},
                    {"id": "Casa", "title": "🏠 Casa"},
                    {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}
                ]
            )
            
        elif paso == 'campana_recopilar_tipo':
            data['tipo'] = text
            estado_usuario['paso'] = 'campana_recopilar_presupuesto'
            actualizar_estado_usuario(user_id, estado_usuario)
            moneda = "USD" if intencion == "Comprar" else "ARS/USD"
            return f"Entendido. Por último, ¿cuál es tu *presupuesto máximo* estimado en {moneda}? (Ej: 100.000, 500k, etc.)"
            
        elif paso == 'campana_recopilar_presupuesto':
            data['presupuesto'] = text
            estado_usuario['paso'] = 'campana_confirmacion'
            actualizar_estado_usuario(user_id, estado_usuario)
            return mostrar_resumen_campana(data)

    # FLUJO: TASAR
    elif intencion == "Tasar":
        if paso == 'campana_recopilar_direccion':
            data['direccion'] = text
            estado_usuario['paso'] = 'campana_recopilar_tipo_tasacion'
            actualizar_estado_usuario(user_id, estado_usuario)
            return WhatsAppResponse.buttons(
                body="¿Qué *tipo de propiedad* deseas tasar?",
                buttons=[
                    {"id": "Depto", "title": "🏢 Departamento"},
                    {"id": "Casa", "title": "🏠 Casa"},
                    {"id": "Otro", "title": "🏭 Otro (Local/Lote)"}
                ]
            )
            
        elif paso == 'campana_recopilar_tipo_tasacion':
            data['tipo'] = text
            estado_usuario['paso'] = 'campana_recopilar_estado'
            actualizar_estado_usuario(user_id, estado_usuario)
            return WhatsAppResponse.buttons(
                body="¿En qué *estado general* se encuentra la propiedad?",
                buttons=[
                    {"id": "Excelente", "title": "✨ Excelente"},
                    {"id": "Bueno", "title": "👍 Bueno/A refaccionar"},
                    {"id": "En_obra", "title": "🏗️ En obra/Terreno"}
                ]
            )
            
        elif paso == 'campana_recopilar_estado':
            data['estado_propiedad'] = text
            estado_usuario['paso'] = 'campana_confirmacion'
            actualizar_estado_usuario(user_id, estado_usuario)
            return mostrar_resumen_campana(data)
            
    return iniciar_campana()

def manejar_pedir_nombre_asesor(text, estado_usuario, user_id):
    data = estado_usuario.get('data_campana', {})
    data['nombre'] = text
    
    # Derivar inmediatamente
    guardar_lead_campana(user_id, data)
    
    estado_usuario['paso'] = 'campana_inicio'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return "✅ ¡Gracias! Hemos derivado tu contacto a un asesor de guardia, quien se comunicará contigo a la brevedad a este número de WhatsApp.\n\n(Envía 'M' para volver al menú)"

def mostrar_resumen_campana(data):
    intencion = data.get('intencion')
    
    resumen = f"📋 *RESUMEN DE TU BÚSQUEDA*\n\n"
    resumen += f"🔸 *Intención:* {intencion}\n"
    
    if intencion in ["Comprar", "Alquilar"]:
        resumen += f"📍 *Zona:* {data.get('zona')}\n"
        resumen += f"🏠 *Tipo:* {data.get('tipo')}\n"
        resumen += f"💰 *Presupuesto:* {data.get('presupuesto')}\n"
    elif intencion == "Tasar":
        resumen += f"📍 *Dirección/Zona:* {data.get('direccion')}\n"
        resumen += f"🏠 *Tipo:* {data.get('tipo')}\n"
        resumen += f"🛠️ *Estado:* {data.get('estado_propiedad')}\n"
        
    resumen += "\n¿Estos datos son correctos?"
    
    return WhatsAppResponse.buttons(
        body=resumen,
        buttons=[
            {"id": "confirmar_datos", "title": "✅ Sí, confirmar"},
            {"id": "corregir_datos", "title": "🔄 Corregir"}
        ]
    )

def manejar_confirmacion_campana(text, estado_usuario, user_id):
    if text in ["confirmar_datos", "1", "si", "sí", "confirmar", "ok"]:
        data = estado_usuario.get('data_campana', {})
        intencion = data.get('intencion')
        
        # Guardar en CRM (PostgreSQL)
        guardar_lead_campana(user_id, data)
        
        # Resetear estado
        estado_usuario['paso'] = 'campana_inicio'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if intencion == "Tasar":
            return "✅ *¡Perfecto!* Hemos registrado tu solicitud de tasación. Un tasador experto de nuestro equipo se pondrá en contacto contigo muy pronto para brindarte el valor real de tu propiedad.\n\n¡Gracias por confiar en Dante Propiedades!"
        else:
            return "✅ *¡Búsqueda registrada!* Un asesor especializado está analizando nuestra base de datos (incluso propiedades off-market) y se contactará contigo a la brevedad con las mejores opciones a medida.\n\n¡Gracias por confiar en Dante Propiedades!"
            
    elif text in ["corregir_datos", "2", "no", "corregir"]:
        # Mandar la pregunta de intencion en vez de reiniciar de cero
        return reiniciar_campana(user_id, estado_usuario, "🔄 No hay problema, empecemos de nuevo.\n\n" + iniciar_campana()['body']) 
        
    return WhatsAppResponse.buttons(
        body="Por favor, confirma si los datos son correctos:",
        buttons=[
            {"id": "confirmar_datos", "title": "✅ Sí, confirmar"},
            {"id": "corregir_datos", "title": "🔄 Corregir"}
        ]
    )

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
    mensaje_agente += f"👤 *Usuario:* +{user_id}\n"
    mensaje_agente += f"🎯 *Intención:* {intencion}\n\n"
    if detalles_str:
        mensaje_agente += f"📝 *Detalles:*\n{detalles_str}\n\n"
    mensaje_agente += "👉 *Requiere contacto inmediato.*"
    
    notificar_agente(mensaje_agente)

