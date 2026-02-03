from flask import Flask, request, jsonify, send_from_directory, send_file
import requests
import os
import json
from datetime import datetime, timedelta
from collections import deque
import threading
import re  # Para expresiones regulares


app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQpT2gMACYFeml7vzkTk4lUZB61rpfKyBY0YHZCX5kJcblFN0k76bqmuvkfaP6BmL0DHZBhUdaX9ZAYqNOxSG28jmoZBdvnhc4rRu5EeeyauKCIIievznyqOvvOWnZAUl9yjYH28GGtkudOtZAPOMByYZAJ0ZBZBwcURBAlFdVrGicCL9AHNbSmlwXJmNUD8IyuynPMBtaK0OTxYuuSK1LrASAzy5CWfafKig6aWp4FaWLZALPEOrhrfIkwVaouotteQ8rRGTca7cvtBIaWU4KDEo06qpgZDZD"
PHONE_NUMBER_ID = "1000705633118215"
ADMIN_NUMBER = "5491151511579"  # Número donde llegarán las alertas de leads
LEADS_FILE = "leads.json"
ADMIN_ACCESS_KEY = "dante2026"  # Llave para acceder al panel admin

# ========== CONFIGURACIÓN DE CITAS ==========
CITAS_FILE = "citas.json"  # Nuevo archivo para almacenar citas
CITAS_DISPONIBLES = [  # Horarios disponibles para citas
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]

# ========== GESTIÓN DE ESTADO DE USUARIOS ==========
estados_usuarios = {}
processed_message_ids = deque(maxlen=100)

def obtener_estado_usuario(user_id):
    """Obtiene o crea el estado de un usuario"""
    if user_id not in estados_usuarios:
        estados_usuarios[user_id] = {
            'paso': 'menu_principal',
            'operacion_seleccionada': None,
            'propiedades_filtradas': [],
            'ultimo_indice_preguntado': None,
            'timestamp': datetime.now().isoformat()
        }
    return estados_usuarios[user_id]

def actualizar_estado_usuario(user_id, nuevo_estado):
    """Actualiza el estado de un usuario"""
    nuevo_estado['timestamp'] = datetime.now().isoformat()
    estados_usuarios[user_id] = nuevo_estado
    
    log(f"💾 Guardando estado para {user_id}:")
    log(f"   Paso: {nuevo_estado.get('paso', 'N/A')}")
    log(f"   Nombre cliente: {nuevo_estado.get('nombre_cliente', 'N/A')}")
    log(f"   Fecha cita: {nuevo_estado.get('fecha_cita', 'N/A')}")
    
    # Limpiar estados antiguos (más de 1 hora)
    ahora = datetime.now()
    usuarios_a_eliminar = [
        uid for uid, estado in estados_usuarios.items()
        if 'timestamp' in estado and (ahora - datetime.fromisoformat(estado['timestamp'])).total_seconds() > 3600
    ]
    
    for uid in usuarios_a_eliminar:
        log(f"🗑️  Eliminando estado antiguo para {uid}")
        del estados_usuarios[uid]

# ========== GESTIÓN DE LEADS (CLIENTES INTERESADOS) ==========
def registrar_lead(user_id, propiedad_id, accion, detalle=""):
    """Registra una interacción de lead en el archivo leads.json"""
    try:
        leads = []
        if os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        
        nuevo_lead = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'propiedad_id': propiedad_id,
            'accion': accion,
            'detalle': detalle
        }
        leads.append(nuevo_lead)
        
        with open(LEADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
            
        log(f"📈 Lead registrado: {user_id} - {accion}")
    except Exception as e:
        log(f"🔥 Error registrando lead: {e}")

def notificar_agente(mensaje):
    """Envía una notificación al número de Dante (ADMIN_NUMBER)"""
    log(f"📢 NOTIFICANDO AL AGENTE: {mensaje[:50]}...")
    return send_whatsapp_message(ADMIN_NUMBER, f"🔔 *ALERTA DANTE-INSIGHTS*\n{mensaje}")

# ========== CARGAR PROPIEDADES ==========
PROPIEDADES_FILE = "propiedades.json"

def cargar_propiedades():
    """Carga las propiedades desde el archivo JSON"""
    try:
        with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
            propiedades = json.load(f)
        log(f"✅ Cargadas {len(propiedades)} propiedades desde {PROPIEDADES_FILE}")
        return propiedades
    except FileNotFoundError:
        log(f"❌ Archivo {PROPIEDADES_FILE} no encontrado")
        return []
    except json.JSONDecodeError as e:
        log(f"❌ Error al leer JSON: {e}")
        return []

def log(message):
    """Función para logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} {message}", flush=True)

def numero_a_emoji(n):
    """Convierte un número a su emoji correspondiente (1-10)"""
    emojis = {
        0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣",
        5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
    }
    return emojis.get(n, str(n))

# ========== FUNCIONES PARA PROPIEDADES ==========
def filtrar_propiedades_por_operacion(operacion):
    """Filtra propiedades por tipo de operación (venta/alquiler)"""
    propiedades = cargar_propiedades()
    if not propiedades:
        return []
    
    propiedades_filtradas = []
    for prop in propiedades:
        if prop.get('operacion', '').lower() == operacion.lower():
            propiedades_filtradas.append(prop)
    
    log(f"🔍 Filtradas {len(propiedades_filtradas)} propiedades para operación: {operacion}")
    return propiedades_filtradas

def generar_listado_propiedades(propiedades):
    """Genera un listado formateado de propiedades para WhatsApp"""
    if not propiedades:
        return "📭 No hay propiedades disponibles en este momento."
    
    listado = "📋 *LISTADO DE PROPIEDADES*\n\n"
    
    for i, prop in enumerate(propiedades[:10], 1):  # Limitar a 10 propiedades
        listado += f"{numero_a_emoji(i)} {prop.get('titulo', 'Sin título')}\n"
        listado += f"   📍 {prop.get('barrio', 'N/A')} | "
        listado += f"💰 "
        
        precio = prop.get('precio', 0)
        moneda = prop.get('moneda_precio', 'USD')
        if moneda == 'USD':
            listado += f"USD ${precio:,.0f}\n"
        else:
            listado += f"$ {precio:,.0f} ARS\n"
        
        listado += f"   🛏️ {prop.get('ambientes', 0)} amb. | "
        listado += f"📐 {prop.get('metros_cuadrados', 0)} m²\n"
        
        # Mostrar estado si es venta
        if prop.get('operacion') == 'venta':
            estado = prop.get('estado', 'N/A')
            listado += f"   🏗️ Estado: {estado.capitalize()}\n"
        
        listado += "─" * 20 + "\n"
    
    if len(propiedades) > 10:
        listado += f"\n📊 ...y {len(propiedades) - 10} propiedades más.\n"
    
    listado += f"\nPara ver detalles, responde con el número (ej: 1️⃣)\n"
    listado += f"{numero_a_emoji(0)} *❌ SALIR*"
    
    return listado

def obtener_detalle_propiedad(propiedades, indice):
    """Obtiene el detalle completo de una propiedad por índice"""
    if indice < 1 or indice > len(propiedades):
        return None
    
    return propiedades[indice - 1]

def formatear_detalle_propiedad(propiedad):
    """Formatea el detalle completo de una propiedad"""
    detalle = f"🏠 *{propiedad.get('titulo', 'Sin título')}*\n\n"
    
    detalle += f"📍 *Ubicación:* {propiedad.get('direccion', 'Sin dirección')}, {propiedad.get('barrio', '')}\n"
    
    precio = propiedad.get('precio', 0)
    moneda = propiedad.get('moneda_precio', 'USD')
    if moneda == 'USD':
        detalle += f"💰 *Precio:* USD ${precio:,.0f}\n"
    else:
        detalle += f"💰 *Precio:* $ {precio:,.0f} ARS\n"
    
    detalle += f"🛏️ *Ambientes:* {propiedad.get('ambientes', 0)}\n"
    detalle += f"📐 *Metros cuadrados:* {propiedad.get('metros_cuadrados', 0)} m²\n"
    detalle += f"📋 *Tipo:* {propiedad.get('tipo', '').capitalize()}\n"
    detalle += f"🏗️ *Estado:* {propiedad.get('estado', 'N/A').capitalize()}\n"
    
    # Mostrar expensas si tiene
    expensas = propiedad.get('expensas', 0)
    if expensas > 0:
        moneda_exp = propiedad.get('moneda_expensas', 'ARS')
        if moneda_exp == 'USD':
            detalle += f"🏢 *Expensas:* USD ${expensas:,.0f}\n"
        else:
            detalle += f"🏢 *Expensas:* $ {expensas:,.0f} ARS\n"
    
    # Mostrar amenities si tiene
    if propiedad.get('cochera', 'No').lower() in ['si', 'sí', 'sí', 'x', '1', 'true']:
        detalle += "🚗 *Cochera:* Sí\n"
    if propiedad.get('balcon', 'No').lower() in ['si', 'sí', 'sí', 'x', '1', 'true']:
        detalle += "🌆 *Balcón:* Sí\n"
    if propiedad.get('pileta', 'No').lower() in ['si', 'sí', 'sí', '1', 'true']:
        detalle += "🏊 *Pileta:* Sí\n"
    if propiedad.get('aire_acondicionado', 'No').lower() in ['si', 'sí', 'sí', '1', 'true']:
        detalle += "❄️ *Aire acondicionado:* Sí\n"
    if propiedad.get('acepta_mascotas', 'No').lower() in ['si', 'sí', 'sí', '1', 'true']:
        detalle += "🐕 *Acepta mascotas:* Sí\n"
    
    detalle += f"\n📝 *Descripción:*\n{propiedad.get('descripcion', 'Sin descripción')}\n\n"
    detalle += "────────────────────\n"
    detalle += "📷 *FOTOS* (Escribe 'F') | 8️⃣ *ME INTERESA*\n"
    detalle += "Para volver al menú, envía '1' | Para salir envía '0' ❌"
    
    return detalle

# ========== BOT CON PROPIEDADES ==========
def get_bot_response(text, user_id):
    """Responde con un mensaje simple, manteniendo estado de usuario"""
    text_lower = text.lower().strip()
    
    # Obtener estado actual del usuario
    estado_usuario = obtener_estado_usuario(user_id)
    log(f"👤 Estado usuario {user_id}: {estado_usuario['paso']} - Texto recibido: '{text}'")
    
    # DEPURACIÓN: Mostrar todo el estado
    log(f"🔍 DEPURACIÓN Estado completo: {json.dumps(estado_usuario, indent=2)}")
    
    # 1. COMANDOS UNIVERSALES (Hola / Salir)
    if text_lower in ["hola", "hi", "hello", "hola bot", "inicio", "menu", "volver", "atras"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if text_lower in ["0", "salir", "exit", "chau", "adios", "basta", "fin"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"👋 ¡Gracias por contactarnos! Para volver al menú, envía '1' | Para salir envía '0' ❌"

    # 2. BOTONES DE NAVEGACIÓN RÁPIDA (Solo en ciertos estados)
    if text_lower == "1" and estado_usuario['paso'] in ['detalle_propiedad', 'vista_fotos', 'vista_web', 'esperando_nombre_lead']:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"

    # 2. ACCIONES ESPECIALES (8 - Me interesa / F - Fotos)
    # Estas acciones funcionan si el usuario tiene un contexto de propiedad (ultimo_indice_preguntado)
    if text_lower == "8" or text_lower in ["f", "foto", "fotos"]:
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        
        if indice and 1 <= indice <= len(propiedades):
            propiedad = obtener_detalle_propiedad(propiedades, indice)
            
            if text_lower == "8":
                log(f"🎯 ACCIÓN GLOBAL: Me interesa (Prop ID: {propiedad.get('id_temporal')})")
                estado_usuario['paso'] = 'esperando_nombre_lead'
                actualizar_estado_usuario(user_id, estado_usuario)
                registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "click_me_interesa")
                return "🙌 ¡Excelente elección! Para que un asesor pueda contactarte, por favor decime tu *Nombre y Apellido*:"
            
            else: # Fotos
                log(f"🎯 ACCIÓN GLOBAL: Fotos (Prop ID: {propiedad.get('id_temporal')})")
                estado_usuario['paso'] = 'vista_fotos'
                actualizar_estado_usuario(user_id, estado_usuario)
                return f"PHOTOS_TRIGGER|{propiedad.get('id_temporal')}"
        
        # Si mandó 8/F pero no hay contexto, lo llevamos al menú principal pero no fallamos
        elif text_lower == "8":
            return "⚠️ Por favor, primero selecciona una propiedad del listado para indicar tu interés."
        elif text_lower in ["f", "foto", "fotos"]:
            return "⚠️ Por favor, primero selecciona una propiedad del listado para ver las fotos."

    # 3. LÓGICA POR ESTADO (Máquina de Estados)
    
    # ESTADO: menu_principal - Si recibe un horario, es un error
    if estado_usuario['paso'] == 'menu_principal':
        # Verificar si es un formato de horario (HH:MM o H:MM)
        try:
            if re.match(r'^\d{1,2}:\d{2}$', text):
                return "❌ *Error de contexto*\n\nParece que intentaste seleccionar un horario, pero primero debes:\n\n1. Seleccionar una propiedad (envía '1' para venta o '2' para alquiler)\n2. Hacer clic en 'Me interesa' (8)\n3. Seguir el proceso de agendamiento de cita\n\nEnvía 'Hola' para comenzar."
        except NameError:
            # Si por alguna razón re no está disponible, usar una verificación simple
            if ':' in text and len(text.split(':')) == 2:
                parts = text.split(':')
                if parts[0].isdigit() and parts[1].isdigit():
                    return "❌ *Error de contexto*\n\nParece que intentaste seleccionar un horario, pero primero debes:\n\n1. Seleccionar una propiedad (envía '1' para venta o '2' para alquiler)\n2. Hacer clic en 'Me interesa' (8)\n3. Seguir el proceso de agendamiento de cita\n\nEnvía 'Hola' para comenzar."
    
    
    # ESTADO: listado_propiedades
    if estado_usuario['paso'] == 'listado_propiedades':
        if text_lower.isdigit():
            indice = int(text_lower)
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            
            if not propiedades:
                estado_usuario['paso'] = 'menu_principal'
                actualizar_estado_usuario(user_id, estado_usuario)
                return "⚠️ No hay propiedades para mostrar. Envía 'Hola' para volver al menú."
            
            if 1 <= indice <= len(propiedades):
                propiedad = obtener_detalle_propiedad(propiedades, indice)
                estado_usuario['paso'] = 'detalle_propiedad'
                estado_usuario['ultimo_indice_preguntado'] = indice
                actualizar_estado_usuario(user_id, estado_usuario)
                
                # Registrar interés
                registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
                
                operacion = propiedad.get('operacion', '')
                titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
                mensaje = f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
                return mensaje
            else:
                return f"❌ El número {indice} está fuera de rango (1-{len(propiedades)}). Elige uno o envía 'Hola'."
        else:
            return "Por favor, elegí un número del listado o enviá 'Hola' para volver."

    # ESTADO: detalle_propiedad
    elif estado_usuario['paso'] == 'detalle_propiedad':
        # (Las opciones 8 y F ya se manejaron arriba de forma global)
        
        # Otras opciones (números para otras propiedades del mismo listado)
        if text_lower.isdigit():
            indice = int(text_lower)
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            if 1 <= indice <= len(propiedades):
                propiedad = obtener_detalle_propiedad(propiedades, indice)
                estado_usuario['ultimo_indice_preguntado'] = indice
                actualizar_estado_usuario(user_id, estado_usuario)
                
                registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
                
                operacion = propiedad.get('operacion', '')
                titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
                return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
            else:
                return f"❌ El número {indice} está fuera de rango. Elige entre 1 y {len(propiedades)} o escribe 'Hola'."
        # Si recibe un horario en este estado, es un error
        elif re.match(r'^\d{1,2}:\d{2}$', text):
            return "❌ *Error de contexto*\n\nPara seleccionar un horario de cita, primero debes hacer clic en 'Me interesa' (8) en esta propiedad y seguir el proceso de agendamiento.\n\nSi quieres agendar cita para esta propiedad, envía '8'"

    # ESTADO: vista_fotos / vista_web / vista_comun
    elif estado_usuario['paso'] in ['vista_fotos', 'vista_web']:
        if text_lower == "1":
            estado_usuario['paso'] = 'menu_principal'
            actualizar_estado_usuario(user_id, estado_usuario)
            return "WELCOME_FLOW_TRIGGER"
        return "⚠️ Opción no válida.\n\nPara volver al menú, envía '1' | Para salir envía '0' ❌"

    # ESTADO: esperando_nombre_lead
    elif estado_usuario['paso'] == 'esperando_nombre_lead':
        nombre_cliente = text.strip()
        
        # Validar que el nombre tenga al menos 2 caracteres
        if len(nombre_cliente) < 2:
            return "❌ Por favor, ingresa tu nombre completo (mínimo 2 caracteres)."
        
        # Guardar el nombre en el estado del usuario
        estado_usuario['nombre_cliente'] = nombre_cliente
        
        # Obtener datos de la propiedad
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        
        if indice and 1 <= indice <= len(propiedades):
            propiedad = obtener_detalle_propiedad(propiedades, indice)
            propiedad_id = propiedad.get('id_temporal', 'N/A')
            propiedad_titulo = propiedad.get('titulo', 'Propiedad sin título')
            
            # Registrar lead completo
            registrar_lead(user_id, propiedad_id, "lead_completo", f"Nombre: {nombre_cliente}")
            
            # Notificar al agente (versión breve)
            notificar_agente(f"🔥 *NUEVO INTERESADO*\n👤 Cliente: {nombre_cliente}\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad_titulo}")
            
            # Cambiar estado para ofrecer cita
            estado_usuario['paso'] = 'ofrecer_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            # Mensaje mejorado con emojis
            return f"✅ *¡Perfecto {nombre_cliente}!*\n\n" \
                f"Hemos registrado tu interés en:\n" \
                f"🏠 *{propiedad_titulo}*\n\n" \
                f"📅 *¿Te gustaría agendar una cita para visitar la propiedad?*\n\n" \
                f"1️⃣ *SÍ, AGENDAR CITA* 📅 (Recomendado)\n" \
                f"2️⃣ *No por ahora, solo información* 📋\n" \
                f"3️⃣ *Ya la vi, quiero ofertar* 💰\n" \
                f"0️⃣ *Salir* ❌"
        
        else:
            # Error: no se encontró la propiedad
            estado_usuario['paso'] = 'menu_principal'
            actualizar_estado_usuario(user_id, estado_usuario)
            return "❌ Hubo un error al procesar tu interés. Por favor, volvé a buscar la propiedad enviando 'Hola'."

    # ESTADO: ofrecer_cita
    elif estado_usuario['paso'] == 'ofrecer_cita':
        text_lower = text.lower().strip()
        log(f"📅 Estado ofrecer_cita - Opción seleccionada: '{text_lower}'")
        
        # Opción 1: Sí, agendar cita
        if text_lower in ["1", "si", "sí", "si quiero", "agendar", "cita", "visita", "sí agendar"]:
            estado_usuario['paso'] = 'solicitar_fecha_cita'
            estado_usuario['ultima_accion'] = 'selecciono_agendar_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            # Mostrar ejemplo de fecha
            hoy = datetime.now()
            mañana = hoy + timedelta(days=1)
            ejemplo_fecha = mañana.strftime("%Y-%m-%d")
            
            mensaje = f"📅 *EXCELENTE {estado_usuario.get('nombre_cliente', 'Cliente')}!*\n\n"
            mensaje += f"Vamos a agendar tu visita.\n\n"
            mensaje += f"📋 *Formato de fecha:* **AAAA-MM-DD**\n"
            mensaje += f"📅 *Ejemplo para mañana:* **{ejemplo_fecha}**\n\n"
            mensaje += f"📍 *Recomendaciones:*\n"
            mensaje += f"• Agendar con 24-48hs de anticipación\n"
            mensaje += f"• Evitar fines de semana (disponibilidad limitada)\n"
            mensaje += f"• Horarios de 9:00 a 18:30\n\n"
            mensaje += f"📅 *Envía la fecha que prefieras:*"
            
            return mensaje
        
        # Opción 2: Solo información
        elif text_lower in ["2", "no", "solo info", "informacion", "información"]:
            nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
            
            # Notificar al admin que es lead sin cita
            notificar_agente(f"📋 *LEAD SIN CITA - SOLO INFO*\n👤 {nombre_cliente}\n📞 +{user_id}\n📝 Solo solicitó información")
            
            # Resetear estado
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['nombre_cliente'] = None
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"✅ *Entendido {nombre_cliente}!*\n\n" \
                f"Un asesor se contactará contigo para brindarte toda la información.\n\n" \
                f"📱 *¿Necesitas algo más?*\n" \
                f"• Ver otras propiedades → Envía '1'\n" \
                f"• Ver detalles de esta propiedad → Envía 'F'\n" \
                f"• Salir → Envía '0'"
        
        # Opción 3: Ya la vi, quiere ofertar
        elif text_lower in ["3", "ofertar", "oferta", "comprar", "alquilar ya"]:
            nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
            
            # Notificar al admin como lead CALIENTE
            notificar_agente(f"🔥🔥 *LEAD CALIENTE - QUIERE OFERTAR!* 🔥🔥\n👤 {nombre_cliente}\n📞 +{user_id}\n💸 LISTO PARA OPERAR")
            
            # Registrar como lead caliente
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            if indice and 1 <= indice <= len(propiedades):
                propiedad = obtener_detalle_propiedad(propiedades, indice)
                registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "lead_caliente_oferta", f"Nombre: {nombre_cliente} - QUIERE OFERTAR")
            
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['nombre_cliente'] = None
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"🎯 *¡EXCELENTE {nombre_cliente}!*\n\n" \
                f"🔥 *PRIORIDAD MÁXIMA*\n" \
                f"Un asesor te contactará en los próximos **15 minutos** para gestionar tu oferta.\n\n" \
                f"📞 *Teléfono de contacto:* +{user_id}\n\n" \
                f"⏰ *Horario de contacto:* Inmediato\n\n" \
                f"¡Gracias por tu interés! 🏠💸"
        
        # Opción 0: Salir
        elif text_lower in ["0", "salir", "chau", "adiós"]:
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['nombre_cliente'] = None
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"👋 ¡Gracias por contactarnos! Para volver al menú, envía '1' | Para salir envía '0' ❌"
        
        # Respuesta no reconocida
        else:
            return "❌ Opción no válida. Por favor selecciona:\n\n" \
                f"1️⃣ *SÍ, AGENDAR CITA* 📅\n" \
                f"2️⃣ *No por ahora, solo información* 📋\n" \
                f"3️⃣ *Ya la vi, quiero ofertar* 💰\n" \
                f"0️⃣ *Salir* ❌"

    # ESTADO: solicitar_fecha_cita
    elif estado_usuario['paso'] == 'solicitar_fecha_cita':
        log(f"📅 Estado solicitar_fecha_cita - Fecha recibida: '{text}'")
        text_lower = text.lower().strip()
        
        # Comando especial: ver fechas disponibles
        if text_lower in ["ver fechas", "disponibles", "fechas"]:
            mensaje = "📅 *PRÓXIMAS FECHAS DISPONIBLES:*\n\n"
            
            hoy = datetime.now()
            for i in range(1, 8):  # Próximos 7 días
                fecha = hoy + timedelta(days=i)
                fecha_str = fecha.strftime("%Y-%m-%d")
                dia_semana = fecha.strftime("%A")
                dia_emoji = "🌞" if fecha.weekday() < 5 else "🎉"  # Emoji diferente para fin de semana
                
                # Obtener disponibilidad
                horarios_disponibles = obtener_horarios_disponibles(fecha_str)
                if horarios_disponibles:
                    mensaje += f"{dia_emoji} *{fecha_str}* ({dia_semana.capitalize()}) ✅\n"
                else:
                    mensaje += f"{dia_emoji} {fecha_str} ({dia_semana.capitalize()}) ❌ AGOTADO\n"
            
            mensaje += "\n📌 *Envía la fecha en formato AAAA-MM-DD*"
            return mensaje
        
        # Validar formato de fecha
        try:
            fecha_ingresada = datetime.strptime(text, "%Y-%m-%d")
            hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Validaciones
            if fecha_ingresada < hoy:
                return "❌ *Fecha pasada*\nNo se pueden agendar citas en fechas pasadas.\n\n" \
                    "Envía una fecha futura (AAAA-MM-DD) o 'Ver fechas'"
            
            if (fecha_ingresada - hoy).days > 30:
                return "❌ *Plazo excedido*\nSolo podemos agendar hasta 30 días en el futuro.\n\n" \
                    "Por favor, elige una fecha más cercana."
            
            # Verificar si es fin de semana (opcional)
            if fecha_ingresada.weekday() >= 5:  # 5 = sábado, 6 = domingo
                return "⚠️ *Fin de semana*\nLa disponibilidad de fines de semana es limitada.\n\n" \
                    "¿Confirmas que quieres agendar para fin de semana?\n\n" \
                    "✅ *Sí, confirmar* | ❌ *Elegir otra fecha*"
            
            # Guardar fecha en estado
            fecha_str = fecha_ingresada.strftime("%Y-%m-%d")
            estado_usuario['fecha_cita'] = fecha_str
            estado_usuario['ultima_accion'] = 'ingreso_fecha_cita'
            
            # Obtener horarios disponibles
            horarios_disponibles = obtener_horarios_disponibles(fecha_str)
            
            if not horarios_disponibles:
                estado_usuario['paso'] = 'ofrecer_cita'  # Volver atrás
                actualizar_estado_usuario(user_id, estado_usuario)
                
                return f"❌ *SIN DISPONIBILIDAD*\n\n" \
                    f"No hay horarios disponibles para el *{fecha_str}*.\n\n" \
                    f"📅 Por favor, elige otra fecha o:\n" \
                    f"1️⃣ Intentar otra fecha\n" \
                    f"2️⃣ Solo información\n" \
                    f"0️⃣ Salir"
            
            # Pasar al siguiente estado
            estado_usuario['paso'] = 'seleccionar_hora_cita'
            estado_usuario['horarios_disponibles'] = horarios_disponibles
            actualizar_estado_usuario(user_id, estado_usuario)
            
            # Formatear mensaje con horarios
            mensaje = f"📅 *Fecha confirmada:* **{fecha_str}**\n\n"
            mensaje += "⏰ *HORARIOS DISPONIBLES:*\n\n"
            
            # Agrupar horarios
            manana = [h for h in horarios_disponibles if int(h.split(':')[0]) < 12]
            tarde = [h for h in horarios_disponibles if 12 <= int(h.split(':')[0]) < 17]
            tarde_noche = [h for h in horarios_disponibles if int(h.split(':')[0]) >= 17]
            
            if manana:
                mensaje += "🌅 *MAÑANA:*\n"
                for hora in manana:
                    mensaje += f"• **{hora}** hs\n"
                mensaje += "\n"
            
            if tarde:
                mensaje += "🌞 *TARDE:*\n"
                for hora in tarde:
                    mensaje += f"• **{hora}** hs\n"
                mensaje += "\n"
            
            if tarde_noche:
                mensaje += "🌇 *TARDE-NOCHE:*\n"
                for hora in tarde_noche:
                    mensaje += f"• **{hora}** hs\n"
            
            mensaje += "\n⏳ *Envía el horario que prefieras* (ej: '09:30' o '14:00')"
            mensaje += "\n↩️ Para volver atrás, envía 'Atrás'"
            
            return mensaje
            
        except ValueError:
            return "❌ *Formato incorrecto*\n\n" \
                "Por favor, usa el formato **AAAA-MM-DD**\n" \
                "*Ejemplo:* 2024-12-25\n\n" \
                "También puedes escribir 'Ver fechas' para ver disponibilidad."

    # ESTADO: seleccionar_hora_cita
    elif estado_usuario['paso'] == 'seleccionar_hora_cita':
        text_lower = text.lower().strip()
        
        # Volver atrás
        if text_lower in ["atrás", "atras", "volver", "back"]:
            estado_usuario['paso'] = 'solicitar_fecha_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            return "🔄 *Volviendo atrás...*\n\nEnvía una nueva fecha (AAAA-MM-DD) o 'Ver fechas'"
        
        # Validar horario seleccionado
        horarios_disponibles = estado_usuario.get('horarios_disponibles', [])
        
        if text not in horarios_disponibles:
            return "❌ *Horario no disponible*\n\n" \
                "El horario seleccionado no está disponible. Por favor elige uno de los horarios listados.\n\n" \
                "Ejemplo: '09:30' o '14:00'"
        
        # Guardar horario en estado
        estado_usuario['hora_cita'] = text
        
        # Obtener datos de la propiedad
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        
        if indice and 1 <= indice <= len(propiedades):
            propiedad = obtener_detalle_propiedad(propiedades, indice)
            propiedad_id = propiedad.get('id_temporal', 'N/A')
            propiedad_titulo = propiedad.get('titulo', 'Propiedad sin título')
            nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
            fecha_cita = estado_usuario.get('fecha_cita')
            hora_cita = text
            
            # Crear la cita
            cita = crear_cita(
                user_id=user_id,
                nombre=nombre_cliente,
                telefono=user_id,
                fecha=fecha_cita,
                hora=hora_cita,
                propiedad_id=propiedad_id,
                notas=f"Propiedad: {propiedad_titulo}"
            )
            
            if cita:
                # Formatear fecha para mostrar
                fecha_obj = datetime.strptime(fecha_cita, "%Y-%m-%d")
                fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
                
                # Resetear estado
                estado_usuario['paso'] = 'menu_principal'
                estado_usuario['nombre_cliente'] = None
                estado_usuario['fecha_cita'] = None
                estado_usuario['hora_cita'] = None
                actualizar_estado_usuario(user_id, estado_usuario)
                
                return f"🎉 *¡CITA AGENDADA CON ÉXITO!*\n\n" \
                    f"✅ **Resumen de tu cita:**\n" \
                    f"👤 *Cliente:* {nombre_cliente}\n" \
                    f"📅 *Fecha:* {fecha_formateada}\n" \
                    f"⏰ *Hora:* {hora_cita} hs\n" \
                    f"🏠 *Propiedad:* {propiedad_titulo[:50]}...\n" \
                    f"🆔 *ID Cita:* {cita['id']}\n\n" \
                    f"📍 *Instrucciones importantes:*\n" \
                    f"• Llega 10 minutos antes\n" \
                    f"• Trae tu documento de identidad\n" \
                    f"• Si necesitas cancelar o reprogramar, contacta al administrador\n\n" \
                    f"📞 *Contacto:* +{ADMIN_NUMBER}\n\n" \
                    f"¡Gracias por elegir Dante Propiedades! 🏠🗝️"
            else:
                return "❌ *Error al agendar la cita*\n\n" \
                    "Hubo un problema al guardar tu cita. Por favor, intenta nuevamente o contacta al administrador."
        
        else:
            return "❌ *Error: No se encontró la propiedad*\n\n" \
                "Hubo un problema al procesar tu cita. Por favor, inicia el proceso nuevamente enviando 'Hola'."

    # 4. OPCIONES GLOBALES (1..7) - Se procesan si no se capturaron arriba
    if text_lower == "1":
        estado_usuario['paso'] = 'listado_propiedades'
        estado_usuario['operacion_seleccionada'] = 'venta'
        propiedades = filtrar_propiedades_por_operacion('venta')
        estado_usuario['propiedades_filtradas'] = propiedades
        actualizar_estado_usuario(user_id, estado_usuario)
        if not propiedades: return "📭 No hay propiedades en venta por ahora.\n\nEnviá 'Hola' para volver."
        return f"💰 *PROPIEDADES EN VENTA*\nEncontramos *{len(propiedades)}* disponibles:\n\n" + generar_listado_propiedades(propiedades)

    elif text_lower == "2":
        estado_usuario['paso'] = 'listado_propiedades'
        estado_usuario['operacion_seleccionada'] = 'alquiler'
        propiedades = filtrar_propiedades_por_operacion('alquiler')
        estado_usuario['propiedades_filtradas'] = propiedades
        actualizar_estado_usuario(user_id, estado_usuario)
        if not propiedades: return "📭 No hay propiedades en alquiler por ahora.\n\nEnviá 'Hola' para volver."
        return f"🔑 *PROPIEDADES EN ALQUILER*\nEncontramos *{len(propiedades)}* disponibles:\n\n" + generar_listado_propiedades(propiedades)

    elif text_lower == "3":
        return "📍 *Búsqueda por zona* - Próximamente disponible.\n\nEnviá 'Hola' para volver."
    
    elif text_lower == "4":
        return "🔍 *Búsqueda libre* - Próximamente disponible.\n\nEnviá 'Hola' para volver."

    elif text_lower == "5":
        estado_usuario['paso'] = 'listado_propiedades'
        estado_usuario['operacion_seleccionada'] = 'todas'
        propiedades = cargar_propiedades()
        estado_usuario['propiedades_filtradas'] = propiedades
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📋 *TODAS LAS PROPIEDADES*\n\n" + generar_listado_propiedades(propiedades)

    elif text_lower == "6":
        # Verificar si es el número de Dante (admin) para mostrar panel de citas
        if user_id == ADMIN_NUMBER.lstrip('549'):
            # Para Dante, mostrar opciones admin
            estado_usuario['paso'] = 'menu_admin'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"🔐 *PANEL ADMINISTRATIVO*\n\n" \
                   f"Hola Dante 👋\n\n" \
                   f"Opciones disponibles:\n\n" \
                   f"📊 *1. Ver dashboard principal*\n" \
                   f"📅 *2. Gestionar citas*\n" \
                   f"👥 *3. Ver leads*\n" \
                   f"🏠 *4. Gestionar propiedades*\n" \
                   f"📈 *5. Ver estadísticas*\n\n" \
                   f"📱 *0. Volver al menú principal*"
        else:
            # Para usuarios normales, verificar si tienen citas agendadas
            citas = cargar_citas()
            citas_usuario = [c for c in citas if c['telefono'] == user_id and c['estado'] != 'cancelada']
            
            if not citas_usuario:
                return "📅 *No tienes citas agendadas*\n\n" \
                       "Para agendar una cita, primero selecciona una propiedad y haz clic en 'Me interesa' (8).\n\n" \
                       "Enviá 'Hola' para volver al menú."
            
            # Mostrar citas del usuario
            mensaje = f"📅 *TUS CITAS AGENDADAS*\n\n"
            mensaje += f"Tienes *{len(citas_usuario)}* cita(s) activa(s):\n\n"
            
            for i, cita in enumerate(citas_usuario, 1):
                fecha_obj = datetime.strptime(cita['fecha'], "%Y-%m-%d")
                fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
                
                mensaje += f"{i}. *{cita['propiedad_id']}*\n"
                mensaje += f"   📅 {fecha_formateada} - ⏰ {cita['hora']}\n"
                mensaje += f"   📍 Estado: {cita['estado'].upper()}\n"
                
                if cita.get('notas') and cita['notas'] != 'Sin notas adicionales':
                    mensaje += f"   📝 Notas: {cita['notas'][:50]}...\n"
                
                mensaje += "   ───────────────\n"
            
            mensaje += f"\nPara consultar o modificar una cita, contacta al administrador.\n\n"
            mensaje += f"Para volver al menú, envía '1' | Para salir envía '0' ❌"
            
            return mensaje
    
    elif text_lower == "7":
        estado_usuario['paso'] = 'vista_web'
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"🌐 *Visita nuestra web oficial:*\n\n👉 https://www.dantepropiedades.com.ar\n\nPara volver al menú, envía '1' | Para salir envía '0' ❌"
    
    elif text_lower == "8":
        # Verificar si es Dante
        if user_id == ADMIN_NUMBER.lstrip('549'):
            estado_usuario['paso'] = 'menu_admin'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"🔐 *ACCESO ADMIN DETECTADO*\n\n" \
                   f"Bienvenido Dante 👋\n\n" \
                   f"Selecciona una opción:\n\n" \
                   f"📊 *1. Ver dashboard principal*\n" \
                   f"📅 *2. Gestionar citas*\n" \
                   f"👥 *3. Ver leads*\n" \
                   f"🏠 *4. Gestionar propiedades*\n" \
                   f"📈 *5. Ver estadísticas*\n\n" \
                   f"📱 *0. Volver al menú principal*"
        else:
            return "⚠️ Acceso restringido. Esta opción es solo para administradores.\n\nEnviá 'Hola' para volver."

    # Si llega aquí sin haber retornado nada, mostrar mensaje de error
    return "❌ *Opción no reconocida*\n\n" \
           "Por favor, selecciona una opción del menú o envía 'Hola' para ver las opciones disponibles."


# ========== VERIFICACIÓN DE TOKEN ==========
def check_token_validity():
    """Verifica si el token de acceso es válido"""
    try:
        log("🔍 Verificando validez del token de acceso...")
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ TOKEN VÁLIDO")
            log(f"   Phone ID: {data.get('id')}")
            log(f"   Nombre: {data.get('verified_name', 'N/A')}")
            log(f"   Número: {data.get('display_phone_number', 'N/A')}")
            return True, data
        else:
            error_data = response.json() if response.content else {}
            log(f"❌ TOKEN INVÁLIDO: Status {response.status_code}")
            log(f"   Error: {error_data.get('error', {}).get('message', 'Error desconocido')}")
            log(f"   Código: {error_data.get('error', {}).get('code', 'N/A')}")
            return False, error_data
            
    except Exception as e:
        log(f"🔥 ERROR VERIFICANDO TOKEN: {e}")
        return False, {"error": str(e)}

# ========== SEND WHATSAPP MESSAGE ==========
def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de WhatsApp usando texto directo"""
    try:
        # Primero verificar si el token es válido
        token_valid, token_info = check_token_validity()
        if not token_valid:
            log("❌❌❌ TOKEN INVÁLIDO - No se puede enviar mensaje")
            return {
                "status": "error",
                "error_code": "invalid_token",
                "error_message": "Token de acceso expirado o inválido",
                "details": "Ve a Meta Developers > WhatsApp > Getting Started para generar nuevo token"
            }
        
        # ========== TRANSFORMAR NÚMERO PARA SANDBOX (AR) ==========
        def transform_number(number):
            # Formato ARG Sandbox: 54911XXXXXXXX -> 541115XXXXXXXX
            if number.startswith("549") and len(number) == 13:
                # Quitamos el '9' y agregamos '15' después del código de área
                country = number[:2]    # 54
                area = number[3:5]       # 11 (o el área que sea)
                rest = number[5:]       # El resto del número
                return f"{country}{area}15{rest}"
            return number
        
        transformed_number = transform_number(to_number)
        
        # URL de la API de Meta
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        
        # Headers con el token de acceso
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Payload para mensaje de texto directo
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        log(f"📤 ENVIANDO MENSAJE DIRECTO")
        log(f"   Token válido: ✓")
        log(f"   Número original: {to_number}")
        log(f"   Número transformado: {transformed_number}")
        log(f"💬 MENSAJE: {message_text[:100]}...")
        
        # Enviar la solicitud
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        log(f"📊 STATUS HTTP: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ ✅ ✅ MENSAJE ENVIADO EXITOSAMENTE")
            log(f"📱 ID del mensaje: {message_id}")
            return {
                "status": "success",
                "message_id": message_id,
                "details": "Mensaje de texto directo enviado",
                "numero_original": to_number,
                "numero_usado": transformed_number
            }
        else:
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code', 'N/A')
            error_message = error_data.get('error', {}).get('message', 'Error desconocido')
            
            log(f"❌ ERROR EN API: {error_code}")
            log(f"❌ MENSAJE: {error_message}")
            
            # Manejar diferentes tipos de errores
            if error_code == 190:  # Token expirado
                log("⚠️  TOKEN EXPIRADO - Debes renovarlo en Meta Developers")
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "Token expirado. Renueva el token en Meta Developers.",
                    "details": "Ve a: https://developers.facebook.com/apps/"
                }
            elif error_code == 10:  # Permisos insuficientes
                log("❌ ERROR DE PERMISOS - El token no tiene 'whatsapp_business_messaging'")
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "El token no tiene permisos suficientes (whatsapp_business_messaging).",
                    "details": "Asegúrate de marcar los permisos al generar el token."
                }
            elif error_code == 131030:  # Número no permitido
                log("⚠️  NÚMERO NO PERMITIDO - Agrega a números de prueba")
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "Número no está en la lista de números de prueba",
                    "details": f"Agrega {to_number} a la lista de números de prueba en Meta"
                }
            
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_message,
                "details": error_data
            }
            
    except Exception as e:
        log(f"🔥 ERROR INESPERADO: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def send_photos_async(user_id, propiedad_id, base_url):
    """Tarea ejecutada en hilo secundario para enviar fotos sin bloquear el webhook"""
    try:
        # Recuperar datos de la propiedad
        propiedades = cargar_propiedades()
        propiedad = next((p for p in propiedades if p.get('id_temporal') == propiedad_id), None)
        
        if not propiedad:
            log(f"❌ No se encontró propiedad {propiedad_id} para envío de fotos")
            return

        fotos = propiedad.get('fotos', [])
        if not fotos:
            return

        # Enviar mensaje de aviso inicial
        send_whatsapp_message(user_id, f"🏠🗝️ *DANTE PROPIEDADES*\nRecuperando {len(fotos)} fotos...")

        # Enviar cada foto
        for foto_path in fotos:
            img_url = f"{base_url}/{foto_path.lstrip('/')}"
            log(f"📤 HILO-SECUNDARIO: Enviando {img_url}")
            send_whatsapp_image(user_id, img_url)
            
        # Notificaciones finales
        notificar_agente(f"👤 El cliente {user_id} está viendo fotos de: {propiedad.get('titulo')}")
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_fotos")
        
        # Enviar mensaje de cierre con instrucciones al usuario
        final_msg = "✅ *¡Fotos enviadas!*\n\nPara volver al menú, envía '1' | Para salir envía '0' ❌"
        send_whatsapp_message(user_id, final_msg)
        
        log(f"✅ HILO-SECUNDARIO: Envío de fotos completado para {user_id}")
    except Exception as e:
        log(f"🔥 Error en hilo de fotos: {e}")

def send_whatsapp_image(to_number, image_url, caption=""):
    """Envía una imagen por WhatsApp"""
    try:
        # Verificar token primero
        token_valid, _ = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar imagen")
            return False
        
        # Transformar número si es necesario (Sandbox ARG)
        def transform_number(number):
            if number.startswith("549") and len(number) == 13:
                country = number[:2]
                area = number[3:5]
                rest = number[5:]
                return f"{country}{area}15{rest}"
            return number
        
        transformed_number = transform_number(to_number)
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption[:1024]
            }
        }
        
        log(f"🖼️ ENVIANDO IMAGEN: {image_url}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            log(f"✅ Imagen enviada exitosamente")
            return True
        else:
            error_data = response.json() if response.content else {}
            log(f"❌ Error enviando imagen: {error_data}")
            return False
            
    except Exception as e:
        log(f"🔥 ERROR enviando imagen: {str(e)}")
        return False

def send_welcome_flow(user_id):
    """Envía el flujo completo de bienvenida: logo (imagen) + mensaje con emoji"""
    # 1. Enviar logo como imagen separada
    # image_sent = send_whatsapp_image(user_id, LOGO_URL, "Dante Propiedades")
    image_sent = False
    
    if image_sent:
        log(f"✅ Logo enviado a {user_id}")
    else:
        log(f"⚠️  No se pudo enviar logo a {user_id}")
    
    # 2. Mensaje de bienvenida CON EMOJIS 🔑🏠
    welcome_message = """🏠🗝️ *DANTE PROPIEDADES*

    ¡Hola! Soy el asistente inmobiliario de Dante Propiedades.

    *¿Qué tipo de operación te interesa?*
    Escribí el número de tu opción:

    1️⃣ *💰 VENTA* - Propiedades en venta
    2️⃣ *🔑 ALQUILER* - Propiedades en alquiler
    3️⃣ *📍 Búsqueda por zona* (próximamente)
    4️⃣ *🔍 Búsqueda libre* (próximamente)
    5️⃣ *📋 Ver todas las propiedades*
    6️⃣ *📅 Mis citas agendadas* (NUEVO)
    7️⃣ *🌐 Ir a nuestra Web*
    8️⃣ *🔐 Panel Admin* (Solo Dante)
    0️⃣ *❌ SALIR*

    Para seleccionar, solo envía el número (ej: "1" o "0")"""   
    
    return send_whatsapp_message(user_id, welcome_message)

# ========== RUTAS PRINCIPALES ==========
@app.route("/")
def home():
    """Página principal"""
    propiedades = cargar_propiedades()
    ventas = len([p for p in propiedades if p.get('operacion') == 'venta'])
    alquileres = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏠 WhatsApp Bot - Dante Propiedades</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .test-btn {{ background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
            .test-btn:hover {{ background-color: #0056b3; }}
            .info-box {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .prop-stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; flex: 1; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <h1>🏠 WhatsApp Bot - Dante Propiedades</h1>
        
        <div class="info-box">
            <h3>🤖 Información del Bot Inmobiliario</h3>
            <p><strong>📞 Número Sandbox:</strong> +1 555 149 2382</p>
            <p><strong>📊 Propiedades cargadas:</strong> {len(propiedades)} propiedades disponibles</p>
            <p><strong>🚀 Instrucciones:</strong> Envía "Hola" al número de WhatsApp para comenzar</p>
        </div>
        
        <div class="prop-stats">
            <div class="stat-box">
                <h3>💰 VENTA</h3>
                <p style="font-size: 24px; font-weight: bold; color: #28a745;">{ventas}</p>
                <p>propiedades</p>
            </div>
            <div class="stat-box">
                <h3>🔑 ALQUILER</h3>
                <p style="font-size: 24px; font-weight: bold; color: #17a2b8;">{alquileres}</p>
                <p>propiedades</p>
            </div>
            <div class="stat-box">
                <h3>📋 TOTAL</h3>
                <p style="font-size: 24px; font-weight: bold; color: #6f42c1;">{len(propiedades)}</p>
                <p>propiedades</p>
            </div>
        </div>
        
        <h2>🔧 Pruebas del Sistema</h2>
        <button class="test-btn" onclick="testSend()">Probar envío manual</button>
        <button class="test-btn" onclick="testMenu()">Probar flujo de propiedades</button>
        <div id="testResult" style="margin-top: 10px;"></div>
        
        <h2>🔑 Estado del Token</h2>
        <div id="tokenStatus" class="status">Verificando token...</div>
        <p><a href="/token-help" target="_blank">📖 Instrucciones para renovar token</a></p>
        
        <h2>📊 Sistema y Propiedades</h2>
        <p>
            <a href="/health">Ver estado del sistema</a> | 
            <a href="/webhook" target="_blank">Verificar webhook</a> | 
            <a href="/propiedades-info">Ver propiedades cargadas</a>
        </p>
        
        <script>
            function checkToken() {{
                fetch('/token-status')
                    .then(r => r.json())
                    .then(data => {{
                        const tokenDiv = document.getElementById('tokenStatus');
                        if (data.valid) {{
                            tokenDiv.className = 'status success';
                            tokenDiv.innerHTML = '<strong>✅ TOKEN VÁLIDO:</strong> Conectado a Meta API<br>' +
                                                 '<strong>Nombre:</strong> ' + (data.name || 'N/A') + '<br>' +
                                                 '<strong>Número:</strong> ' + (data.number || 'N/A');
                        }} else {{
                            tokenDiv.className = 'status error';
                            tokenDiv.innerHTML = '<strong>❌ TOKEN INVÁLIDO:</strong> ' + (data.error || 'Error desconocido') +
                                                 '<br><strong>⚠️ El bot NO puede enviar mensajes</strong>';
                        }}
                    }});
            }}
            
            function testSend() {{
                const btn = document.querySelector('.test-btn');
                const resultDiv = document.getElementById('testResult');
                
                btn.disabled = true;
                btn.textContent = 'Enviando...';
                resultDiv.innerHTML = '<div class="status">Enviando prueba...</div>';
                
                fetch('/test')
                    .then(r => r.json())
                    .then(data => {{
                        if (data.result.status === 'success') {{
                            resultDiv.innerHTML = '<div class="status success">✅ Prueba enviada exitosamente</div>';
                        }} else {{
                            resultDiv.innerHTML = '<div class="status error">❌ Error en prueba: ' + (data.result.error_message || data.result.error || 'Error desconocido') + '</div>';
                        }}
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                        checkToken();
                    }})
                    .catch(error => {{
                        resultDiv.innerHTML = '<div class="status error">❌ Error de conexión: ' + error + '</div>';
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                    }});
            }}
            
            function testMenu() {{
                const resultDiv = document.getElementById('testResult');
                resultDiv.innerHTML = '<div class="status">Probando flujo de propiedades...</div>';
                
                fetch('/test-propiedades')
                    .then(r => r.json())
                    .then(data => {{
                        let html = '<h3>✅ Prueba de propiedades completada:</h3>';
                        html += '<div class="status success">';
                        html += '<strong>Propiedades cargadas:</strong> ' + data.total_propiedades + '<br>';
                        html += '<strong>En venta:</strong> ' + data.venta_count + '<br>';
                        html += '<strong>En alquiler:</strong> ' + data.alquiler_count + '<br>';
                        html += '<strong>Archivo:</strong> ' + data.archivo;
                        html += '</div>';
                        resultDiv.innerHTML = html;
                    }})
                    .catch(error => {{
                        resultDiv.innerHTML = '<div class="status error">❌ Error: ' + error + '</div>';
                    }});
            }}
            
            checkToken();
        </script>
    </body>
    </html>
    """
    return html, 200

# ========== RUTAS DEL PANEL ADMINISTRATIVO ==========
@app.route("/admin")
def admin_panel():
    """Sirve el panel de administración si la llave es correcta"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return "⚠️ Acceso No Autorizado. Por favor usa el enlace seguro.", 403
    return send_file("admin.html")

@app.route("/api/leads")
def api_leads():
    """Retorna los leads en formato JSON si la llave es correcta"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    leads = []
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        except Exception as e:
            log(f"Error leyendo leads para API: {e}")
            
    return jsonify({"leads": leads})

@app.route("/api/leads-file")
def api_leads_file():
    """Retorna el archivo Leads.xlsx si la llave es correcta"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    filename = "Leads.xlsx"
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    else:
        log(f"⚠️ Archivo {filename} no encontrado para descarga admin")
        return jsonify({"error": "File not found"}), 404

# ========== RUTA PARA IMÁGENES LOCALES ==========
@app.route('/imgs/<path:filename>')
def serve_image(filename):
    """Sirve imágenes desde la carpeta imgs con el tipo MIME correcto"""
    try:
        return send_from_directory('imgs', filename)
    except Exception as e:
        log(f"🔥 Error sirviendo imagen {filename}: {e}")
        return "Imagen no encontrada", 404

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook para recibir mensajes de WhatsApp"""
    if request.method == "GET":
        # Verificación del webhook (Meta requiere esto)
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log("=" * 60)
        log("🔍 SOLICITUD GET AL WEBHOOK (VERIFICACIÓN)")
        log(f"   Mode: {mode}")
        log(f"   Token: {token}")
        log(f"   Challenge: {challenge}")
        
        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                log("✅ ✅ ✅ WEBHOOK VERIFICADO EXITOSAMENTE")
                return challenge, 200
            else:
                log("❌ VERIFICACIÓN FALLIDA - Token incorrecto")
                return "Verification failed", 403
        
        log("ℹ️  Solicitud GET sin parámetros de verificación")
        return "Webhook endpoint", 200
    
    elif request.method == "POST":
        log("=" * 60)
        log("📨 📨 📨 NUEVO WEBHOOK POST RECIBIDO")
        log("=" * 60)
        
        try:
            data = request.get_json()
            
            if not data:
                log("❌ Datos JSON vacíos o inválidos")
                return jsonify({"status": "no_data"}), 200
            
            # Log básico de la estructura
            log(f"📦 Estructura recibida:")
            log(f"   Object: {data.get('object', 'N/A')}")
            
            if "entry" in data and data["entry"]:
                log(f"   Entries: {len(data['entry'])}")
            
            # Verificar que sea un webhook de WhatsApp Business
            if data.get("object") != "whatsapp_business_account":
                log("❌ No es un webhook de WhatsApp Business")
                return jsonify({"status": "not_whatsapp"}), 200
            
            # Procesar las entradas
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Verificar si hay mensajes
                    if "messages" in value:
                        messages = value["messages"]
                        log(f"   📨 Mensajes en webhook: {len(messages)}")
                        
                        for message in messages:
                            # Solo procesar mensajes de texto
                            if message.get("type") == "text":
                                message_id = message.get("id")
                                
                                # 🛑 DEDUPLICACIÓN: Verificar si el mensaje ya fue procesado
                                if message_id in processed_message_ids:
                                    log(f"🛑 MENSAJE DUPLICADO IGNORADO (ID: {message_id})")
                                    continue
                                    
                                # Agregar ID a la lista de procesados
                                processed_message_ids.append(message_id)
                                
                                from_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                
                                if from_number and message_text:
                                    log("=" * 40)
                                    log(f"👤 USUARIO: {from_number}")
                                    log(f"💬 TEXTO: {message_text}")
                                    log("=" * 40)
                                    
                                    # Obtener respuesta del bot usando el estado del usuario
                                    response_text = get_bot_response(message_text, from_number)
                                    
                                    # ✅ MODIFICACIÓN: Manejo especial para bienvenida con logo
                                    if response_text == "WELCOME_FLOW_TRIGGER":
                                        log("🎯 DETECTADA SOLICITUD DE BIENVENIDA")
                                        log("🔄 ENVIANDO FLUJO COMPLETO (logo + mensaje)")
                                        
                                        # Enviar flujo de bienvenida con logo
                                        result = send_welcome_flow(from_number)
                                        
                                        log("=" * 40)
                                        if result.get('status') == 'success':
                                            log("✅ ✅ ✅ BIENVENIDA ENVIADA EXITOSAMENTE")
                                            log("   📸 Logo + mensaje enviados")
                                        else:
                                            log("❌ ERROR EN BIENVENIDA")
                                    else:
                                        # Respuesta normal del bot (sin logo)
                                        if response_text == "WELCOME_FLOW_TRIGGER":
                                            # Esto es redundante por el block de arriba pero por si acaso
                                            result = send_welcome_flow(from_number)
                                        elif response_text and response_text.startswith("PHOTOS_TRIGGER|"):
                                            # Disparar hilo de fotos en segundo plano
                                            prop_id = response_text.split("|")[1]
                                            base_url = request.host_url.rstrip('/')
                                            if "onrender.com" in base_url and not base_url.startswith("https"):
                                                base_url = base_url.replace("http://", "https://")
                                            
                                            log(f"🚀 Iniciando hilo de fotos para propiedad {prop_id}")
                                            thread = threading.Thread(target=send_photos_async, args=(from_number, prop_id, base_url))
                                            thread.start()
                                            
                                            # Enviar confirmación inmediata de que se están enviando las fotos
                                            confirmacion = "📸 *Enviando fotos...* Esto puede tardar unos segundos.\n\nPara volver al menú, envía '1' | Para salir envía '0' ❌"
                                            result = send_whatsapp_message(from_number, confirmacion)
                                        elif response_text and response_text != "None":
                                            log(f"🤖 RESPUESTA GENERADA ({len(response_text)} caracteres)")
                                            result = send_whatsapp_message(from_number, response_text)
                                        else:
                                            log("⚠️ Respuesta vacía generada - No se envía mensaje")
                                            result = {"status": "skipped", "reason": "empty_response"}
                                    
                                    log("=" * 40)
                                    log(f"📊 RESULTADO FINAL: {result.get('status')}")
                                    if result.get('status') == 'success':
                                        log("✅ ✅ ✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
                                    else:
                                        log("❌ PROCESAMIENTO CON ERRORES")
                                    log("=" * 60)
                                    
                                    return jsonify({
                                        "status": "processed",
                                        "user": from_number,
                                        "result": result
                                    }), 200
                    
                    # Si hay notificaciones de estado (entregado, leído, etc.)
                    elif "statuses" in value:
                        statuses = value["statuses"]
                        for status in statuses:
                            log(f"📊 Estado de mensaje: {status.get('status', 'N/A')} para ID: {status.get('id', 'N/A')}")
                        # No necesitamos responder a notificaciones de estado
                        return jsonify({"status": "status_update"}), 200
            
            log("ℹ️  Webhook recibido pero sin mensajes de texto para procesar")
            return jsonify({"status": "no_text_messages"}), 200
            
        except Exception as e:
            log(f"❌ ERROR PROCESANDO WEBHOOK: {str(e)}")
            import traceback
            log(f"🔍 TRAZABILIDAD: {traceback.format_exc()[:500]}")
            return jsonify({"status": "error", "error": str(e)}), 500

# ========== GESTIÓN DE CITAS ==========
def cargar_citas():
    """Carga las citas existentes desde el archivo JSON"""
    try:
        if os.path.exists(CITAS_FILE):
            with open(CITAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        log(f"❌ Error cargando citas: {e}")
        return []

def guardar_citas(citas):
    """Guarda las citas en el archivo JSON"""
    try:
        with open(CITAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(citas, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log(f"❌ Error guardando citas: {e}")
        return False

def crear_cita(user_id, nombre, telefono, fecha, hora, propiedad_id, notas=""):
    """Crea una nueva cita"""
    try:
        citas = cargar_citas()
        
        nueva_cita = {
            'id': f"cita_{len(citas)+1:04d}",
            'user_id': user_id,
            'nombre': nombre,
            'telefono': telefono,
            'fecha': fecha,
            'hora': hora,
            'propiedad_id': propiedad_id,
            'estado': 'pendiente',  # pendiente | confirmada | cancelada | completada
            'notas': notas,
            'creacion': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat()
        }
        
        citas.append(nueva_cita)
        
        if guardar_citas(citas):
            log(f"✅ Cita creada: {nueva_cita['id']} para {nombre}")
            # Notificar al admin
            notificar_cita_admin(nueva_cita)
            return nueva_cita
        return None
    except Exception as e:
        log(f"❌ Error creando cita: {e}")
        return None

def notificar_cita_admin(cita):
    """Envía notificación de nueva cita al admin"""
    try:
        mensaje = f"📅 *NUEVA CITA AGENDADA*\n\n"
        mensaje += f"👤 *Cliente:* {cita['nombre']}\n"
        mensaje += f"📞 *Teléfono:* +{cita['telefono']}\n"
        mensaje += f"📅 *Fecha:* {cita['fecha']}\n"
        mensaje += f"⏰ *Hora:* {cita['hora']}\n"
        mensaje += f"🏠 *Propiedad ID:* {cita['propiedad_id']}\n"
        mensaje += f"🆔 *ID Cita:* {cita['id']}\n"
        mensaje += f"📝 *Notas:* {cita.get('notas', 'Sin notas')}\n\n"
        mensaje += f"📍 *Estado:* {cita['estado'].upper()}"
        
        return send_whatsapp_message(ADMIN_NUMBER, mensaje)
    except Exception as e:
        log(f"❌ Error notificando cita al admin: {e}")
        return False

def obtener_horarios_disponibles(fecha_str):
    """Obtiene horarios disponibles para una fecha específica"""
    try:
        # Convertir fecha string a objeto datetime
        fecha_deseada = datetime.strptime(fecha_str, "%Y-%m-%d")
        
        # Cargar citas existentes
        citas = cargar_citas()
        
        # Obtener horarios ocupados para esa fecha
        horarios_ocupados = []
        for cita in citas:
            if cita['fecha'] == fecha_str and cita['estado'] in ['pendiente', 'confirmada']:
                horarios_ocupados.append(cita['hora'])
        
        # Filtrar horarios disponibles
        horarios_disponibles = [hora for hora in CITAS_DISPONIBLES if hora not in horarios_ocupados]
        
        log(f"📅 Horarios disponibles para {fecha_str}: {len(horarios_disponibles)}/{len(CITAS_DISPONIBLES)}")
        return horarios_disponibles
    except Exception as e:
        log(f"❌ Error obteniendo horarios disponibles: {e}")
        return CITAS_DISPONIBLES  # Devuelve todos si hay error

def formatear_horarios_disponibles(horarios):
    """Formatea los horarios disponibles para mostrar en WhatsApp"""
    if not horarios:
        return "❌ *No hay horarios disponibles para esta fecha.*\nPor favor, elige otra fecha."
    
    mensaje = "⏰ *HORARIOS DISPONIBLES:*\n\n"
    
    # Agrupar horarios en grupos de 4 para mejor visualización
    grupos = [horarios[i:i+4] for i in range(0, len(horarios), 4)]
    
    for i, grupo in enumerate(grupos):
        for hora in grupo:
            emoji_hora = "🌅" if int(hora.split(':')[0]) < 12 else "🌞" if int(hora.split(':')[0]) < 17 else "🌇"
            mensaje += f"{emoji_hora} *{hora}*  "
        mensaje += "\n"
    
    mensaje += "\nPara seleccionar un horario, envía la hora (ej: '09:30' o '14:00')"
    mensaje += "\nPara volver atrás, envía 'Atrás'"
    
    return mensaje

@app.route("/test", methods=["GET"])
def test_send():
    """Endpoint de prueba manual"""
    log("=" * 60)
    log("🧪 INICIANDO PRUEBA MANUAL")
    log("=" * 60)
    
    test_number = "5491151511579"
    test_message = "✅ ¡Hola! Este es un mensaje de prueba desde el bot inmobiliario. El sistema de propiedades está funcionando correctamente. ¡Prueba enviando 'Hola' para ver el menú de propiedades!"
    
    result = send_whatsapp_message(test_number, test_message)
    
    log("=" * 60)
    log(f"🧪 RESULTADO DE PRUEBA: {result.get('status')}")
    log("=" * 60)
    
    return jsonify({
        "test": "completed",
        "timestamp": datetime.now().isoformat(),
        "number": test_number,
        "message": test_message,
        "result": result
    })

@app.route("/test-propiedades", methods=["GET"])
def test_propiedades():
    """Prueba la carga de propiedades"""
    propiedades = cargar_propiedades()
    
    venta_count = len([p for p in propiedades if p.get('operacion') == 'venta'])
    alquiler_count = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    
    return jsonify({
        "test": "propiedades_loaded",
        "total_propiedades": len(propiedades),
        "venta_count": venta_count,
        "alquiler_count": alquiler_count,
        "archivo": PROPIEDADES_FILE,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/propiedades-info", methods=["GET"])
def propiedades_info():
    """Muestra información sobre las propiedades cargadas"""
    propiedades = cargar_propiedades()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>📊 Propiedades Cargadas</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .prop-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }
            .venta { border-left: 5px solid #28a745; }
            .alquiler { border-left: 5px solid #17a2b8; }
            .stats { background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>📊 Propiedades Cargadas en el Sistema</h1>
    """
    
    if propiedades:
        html += f"""
        <div class="stats">
            <h3>📈 Estadísticas</h3>
            <p><strong>Total de propiedades:</strong> {len(propiedades)}</p>
            <p><strong>En venta:</strong> {len([p for p in propiedades if p.get('operacion') == 'venta'])}</p>
            <p><strong>En alquiler:</strong> {len([p for p in propiedades if p.get('operacion') == 'alquiler'])}</p>
        </div>
        """
        
        for prop in propiedades:
            operacion = prop.get('operacion', '')
            clase = 'venta' if operacion == 'venta' else 'alquiler'
            precio = prop.get('precio', 0)
            moneda = prop.get('moneda_precio', 'USD')
            precio_str = f"USD ${precio:,.0f}" if moneda == 'USD' else f"$ {precio:,.0f} ARS"
            
            html += f"""
            <div class="prop-card {clase}">
                <h3>{prop.get('titulo', 'Sin título')}</h3>
                <p><strong>ID:</strong> {prop.get('id_temporal', 'N/A')} | 
                   <strong>Operación:</strong> {operacion.upper()} | 
                   <strong>Barrio:</strong> {prop.get('barrio', 'N/A')}</p>
                <p><strong>Precio:</strong> {precio_str} | 
                   <strong>Ambientes:</strong> {prop.get('ambientes', 0)} | 
                   <strong>Metros:</strong> {prop.get('metros_cuadrados', 0)} m²</p>
                <p><strong>Tipo:</strong> {prop.get('tipo', 'N/A').capitalize()} | 
                   <strong>Estado:</strong> {prop.get('estado', 'N/A')}</p>
                <p><strong>Descripción:</strong> {prop.get('descripcion', 'Sin descripción')[:200]}...</p>
            </div>
            """
    else:
        html += "<div class='stats'><p>❌ No se pudieron cargar las propiedades</p></div>"
    
    html += """
        <p><a href="/">← Volver al inicio</a></p>
    </body>
    </html>
    """
    
    return html

@app.route("/token-status", methods=["GET"])
def token_status():
    """Verifica si el token es válido"""
    try:
        log("🔍 Verificando token de acceso...")
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Token válido - Nombre: {data.get('verified_name', 'N/A')}")
            return jsonify({
                "valid": True,
                "status": response.status_code,
                "name": data.get('verified_name'),
                "number": data.get('display_phone_number')
            })
        else:
            log(f"❌ Token inválido - Status: {response.status_code}")
            return jsonify({
                "valid": False,
                "status": response.status_code,
                "error": response.text[:200] if response.text else "No response"
            })
    except Exception as e:
        log(f"🔥 Error verificando token: {str(e)}")
        return jsonify({"valid": False, "error": str(e)})

@app.route("/token-help", methods=["GET"])
def token_help():
    """Muestra instrucciones para renovar el token"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔄 Instrucciones para renovar token</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .step { background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0; }
            .important { background-color: #fff3cd; border-left: 4px solid #ffc107; }
            .success { background-color: #d4edda; border-left: 4px solid #28a745; }
            code { background-color: #f1f1f1; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🔄 Renovar Token de Acceso de WhatsApp</h1>
        
        <div class="step">
            <h3>Paso 1: Ve a Meta Developers</h3>
            <p><a href="https://developers.facebook.com/apps/" target="_blank">https://developers.facebook.com/apps/</a></p>
        </div>
        
        <div class="step">
            <h3>Paso 2: Accede a tu aplicación</h3>
            <p>Selecciona tu aplicación de WhatsApp</p>
        </div>
        
        <div class="step">
            <h3>Paso 3: Ve a WhatsApp > Getting Started</h3>
            <p>En el menú lateral izquierdo, selecciona "WhatsApp"</p>
        </div>
        
        <div class="step">
            <h3>Paso 4: Busca "Access Tokens"</h3>
            <p>En la sección de configuración, busca el token de acceso</p>
        </div>
        
        <div class="step important">
            <h3>Paso 5: Haz clic en "Renew" o "Generate"</h3>
            <p>Genera un nuevo token de acceso</p>
        </div>
        
        <div class="step">
            <h3>Paso 6: Copia el nuevo token</h3>
            <p>El token empieza con <code>EAA...</code></p>
        </div>
        
        <div class="step success">
            <h3>Paso 7: Actualiza el código</h3>
            <p>Reemplaza la variable ACCESS_TOKEN en main.py con el nuevo token</p>
            <p><strong>Token actual (inicio):</strong> <code>""" + ACCESS_TOKEN[:50] + """...</code></p>
            <p><strong>Instrucción:</strong> Busca <code>ACCESS_TOKEN = "EAAJYsGl5pHgBQg...</code> en el código y reemplázala.</p>
        </div>
        
        <div class="step">
            <h3>Paso 8: Reinicia el servicio</h3>
            <p>El bot funcionará automáticamente con el nuevo token</p>
        </div>
        
        <h3>📋 Estado Actual del Token</h3>
        <div id="tokenStatus">Verificando...</div>
        
        <script>
            fetch('/token-status')
                .then(r => r.json())
                .then(data => {
                    const tokenDiv = document.getElementById('tokenStatus');
                    if (data.valid) {
                        tokenDiv.innerHTML = '<div style="background-color: #d4edda; padding: 10px; border-radius: 5px;">' +
                                            '<strong>✅ TOKEN VÁLIDO</strong><br>' +
                                            'Nombre: ' + (data.name || 'N/A') + '<br>' +
                                            'Número: ' + (data.number || 'N/A') + '</div>';
                    } else {
                        tokenDiv.innerHTML = '<div style="background-color: #f8d7da; padding: 10px; border-radius: 5px;">' +
                                            '<strong>❌ TOKEN INVÁLIDO</strong><br>' +
                                            'Error: ' + (data.error || 'Desconocido') + '</div>';
                    }
                });
        </script>
        
        <p><a href="/">← Volver al inicio</a></p>
    </body>
    </html>
    """, 200

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    token_valid, _ = check_token_validity()
    propiedades = cargar_propiedades()
    
    return jsonify({
        "status": "healthy" if token_valid else "unhealthy_token",
        "service": "whatsapp-bot-inmobiliario",
        "version": "2.1",
        "timestamp": datetime.now().isoformat(),
        "token_valid": token_valid,
        "propiedades_cargadas": len(propiedades),
        "venta_count": len([p for p in propiedades if p.get('operacion') == 'venta']),
        "alquiler_count": len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    })

# ========== RUTAS API PARA PANEL DE CITAS ==========
@app.route("/api/citas", methods=["GET"])
def api_citas():
    """Retorna todas las citas en formato JSON"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    citas = cargar_citas()
    return jsonify(citas)

@app.route("/api/citas/<cita_id>/estado", methods=["PUT"])
def actualizar_estado_cita(cita_id):
    """Actualiza el estado de una cita"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    nuevo_estado = request.args.get('estado')
    if nuevo_estado not in ['pendiente', 'confirmada', 'cancelada']:
        return jsonify({"error": "Estado inválido"}), 400
    
    try:
        citas = cargar_citas()
        cita_encontrada = False
        
        for cita in citas:
            if cita['id'] == cita_id:
                cita['estado'] = nuevo_estado
                cita['ultima_actualizacion'] = datetime.now().isoformat()
                cita_encontrada = True
                break
        
        if not cita_encontrada:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        if guardar_citas(citas):
            log(f"✅ Estado actualizado: {cita_id} -> {nuevo_estado}")
            return jsonify({"status": "success", "message": "Estado actualizado"})
        else:
            return jsonify({"error": "Error guardando cambios"}), 500
            
    except Exception as e:
        log(f"❌ Error actualizando estado de cita: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/citas/recordatorio/<cita_id>", methods=["POST"])
def enviar_recordatorio_cita(cita_id):
    """Envía un recordatorio de cita por WhatsApp"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        citas = cargar_citas()
        cita = next((c for c in citas if c['id'] == cita_id), None)
        
        if not cita:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # Formatear fecha para el mensaje
        fecha_obj = datetime.strptime(cita['fecha'], "%Y-%m-%d")
        fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        
        mensaje = f"🔔 *RECORDATORIO DE CITA - DANTE PROPIEDADES*\n\n"
        mensaje += f"👤 *Cliente:* {cita['nombre']}\n"
        mensaje += f"📅 *Fecha:* {fecha_formateada}\n"
        mensaje += f"⏰ *Hora:* {cita['hora']}\n"
        mensaje += f"🏠 *Propiedad:* {cita['propiedad_id']}\n\n"
        mensaje += f"📍 *Instrucciones:*\n"
        mensaje += f"• Llega 10 minutos antes\n"
        mensaje += f"• Trae tu documento de identidad\n"
        mensaje += f"• Contacto: +{ADMIN_NUMBER}\n\n"
        mensaje += f"¡Te esperamos! 🏠🗝️"
        
        # Enviar mensaje al cliente
        result = send_whatsapp_message(cita['telefono'], mensaje)
        
        if result.get('status') == 'success':
            log(f"✅ Recordatorio enviado a {cita['telefono']}")
            return jsonify({"status": "success", "message": "Recordatorio enviado"})
        else:
            return jsonify({"error": "Error enviando mensaje", "details": result}), 500
            
    except Exception as e:
        log(f"❌ Error enviando recordatorio: {e}")
        return jsonify({"error": str(e)}), 500

# Agregar también la función para ver el panel de citas
@app.route("/admin/citas")
def admin_citas_panel():
    """Sirve el panel de administración de citas"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return "⚠️ Acceso No Autorizado. Por favor usa el enlace seguro.", 403
    return send_file("admin_citas.html")

# También modificar la función cargar_citas para mejor manejo de errores
def cargar_citas():
    """Carga las citas existentes desde el archivo JSON"""
    try:
        if os.path.exists(CITAS_FILE):
            with open(CITAS_FILE, 'r', encoding='utf-8') as f:
                citas = json.load(f)
                # Asegurar que cada cita tenga todos los campos necesarios
                for cita in citas:
                    if 'telefono' not in cita and 'user_id' in cita:
                        cita['telefono'] = cita['user_id']
                    if 'notas' not in cita:
                        cita['notas'] = 'Sin notas'
                return citas
        return []
    except Exception as e:
        log(f"❌ Error cargando citas: {e}")
        return []


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🏠 🏠 🏠 WHATSAPP BOT INMOBILIARIO - VERSIÓN 2.1")
    print("=" * 60)
    
    propiedades = cargar_propiedades()
    print(f"📊 Propiedades cargadas: {len(propiedades)}")
    
    if propiedades:
        ventas = len([p for p in propiedades if p.get('operacion') == 'venta'])
        alquileres = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
        print(f"💰 En venta: {ventas} propiedades")
        print(f"🔑 En alquiler: {alquileres} propiedades")
    
    token_valid, token_info = check_token_validity()
    if token_valid:
        print(f"✅ TOKEN VÁLIDO")
        print(f"   📞 Número: {token_info.get('display_phone_number', 'N/A')}")
        print(f"   📛 Nombre: {token_info.get('verified_name', 'N/A')}")
    else:
        print(f"❌❌❌ TOKEN INVÁLIDO O EXPIRADO ❌❌❌")
        print(f"   ⚠️  El bot NO PODRÁ ENVIAR MENSAJES")
        print(f"   ℹ️  Visita: https://meta-chat-npbx.onrender.com/token-help")
    
    print(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    print(f"📁 Propiedades: {PROPIEDADES_FILE}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)