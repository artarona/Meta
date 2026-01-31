from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQmMrZCpN1uiDJ2KzZBkug9t3WrXQIvUzQSGhgZBLQoJkAykO1STvWkkaMjwffvIF8ZCU48MtcwLh8246cN7rbmjvzz5VXJIQ1CGsR9hhOBZCPW979OZAEoMMeTKDbi1UEjRAh1IciWdXBWSyLQZCszfgiGDZBnbMe0vJywjQ7a72j8J0XgDNkUomVEIXCGbLIWINzlBEOnwze6K5KDBtKB8WdRLphtcCy3Ye1HtrgEKulvuD6AIvcGNh90RItrQCJKbvsGXvZBZBJImOUMHaLzrSs7DU8ZD"
PHONE_NUMBER_ID = "1000705633118215"

# ========== URL DEL LOGO ==========
#LOGO_URL = "https://meta-chat-npbx.onrender.com/llave.png"
# ========== URL DEL LOGO ==========
# LOGO_URL = "https://images.weserv.nl/?url=i.ibb.co/XZkNL0GJ/llave.png&w=200&output=png"

# ========== GESTIÓN DE ESTADO DE USUARIOS ==========
estados_usuarios = {}

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
    estados_usuarios[user_id] = nuevo_estado
    # Limpiar estados antiguos (más de 1 hora)
    usuarios_a_eliminar = []
    for uid, estado in estados_usuarios.items():
        if 'timestamp' in estado:
            try:
                timestamp = datetime.fromisoformat(estado['timestamp'])
                if (datetime.now() - timestamp).seconds > 3600:  # 1 hora
                    usuarios_a_eliminar.append(uid)
            except:
                usuarios_a_eliminar.append(uid)
    
    for uid in usuarios_a_eliminar:
        del estados_usuarios[uid]

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
        listado += f"*[{i}]* {prop.get('titulo', 'Sin título')}\n"
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
    
    listado += "\nPara ver detalles de una propiedad, responde con el número entre corchetes [1], [2], etc.\n"
    listado += "O envía *0* para ❌ SALIR"
    
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
    detalle += "Para volver al menú, envía 'Hola' | Para salir envía '0' ❌"
    
    return detalle




# ========== BOT CON PROPIEDADES ==========
def get_bot_response(text, user_id):
    """Responde con un mensaje simple, manteniendo estado de usuario"""
    text_lower = text.lower().strip()
    
    # Obtener estado actual del usuario
    estado_usuario = obtener_estado_usuario(user_id)
    # log(f"👤 Estado usuario {user_id}: {estado_usuario['paso']} - Operación: {estado_usuario['operacion_seleccionada']}")
    log(f"👤 Estado usuario {user_id}: {estado_usuario['paso']}")
    
    # MENÚ PRINCIPAL - Resetear estado SOLO cuando se envía explícitamente "Hola"
    if text_lower in ["hola", "hi", "hello", "hola bot", "inicio", "menu", "volver", "atras"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # RETORNAR SEÑAL ESPECIAL PARA BIENVENIDA
        return "WELCOME_FLOW_TRIGGER"
    
    
    # MENÚ PRINCIPAL - Resetear estado SOLO cuando se envía explícitamente "Hola"
    if text_lower in ["hola", "hi", "hello", "hola bot", "inicio", "menu", "volver", "atras"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return """¡Hola! Soy el asistente inmobiliario de Dante Propiedades. 🏠

*¿Qué tipo de operación te interesa?*
Escribí el número de tu opción:

1️⃣ *💰 VENTA* - Propiedades en venta
2️⃣ *🔑 ALQUILER* - Propiedades en alquiler
3️⃣ *📍 Búsqueda por zona* (próximamente)
4️⃣ *🔍 Búsqueda libre* (próximamente)
5️⃣ *📋 Ver todas las propiedades*
6️⃣ *ℹ️ Información* (próximamente)
0️⃣ *❌ SALIR*

Para seleccionar, solo envía el número (ej: "1" o "0")"""
    
    # OPCIÓN 0: SALIR (Universal)
    if text_lower in ["0", "salir", "exit", "chau", "adios", "basta", "fin"]:
        # Resetear todo
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return "👋 ¡Gracias por contactarnos! Si necesitas algo más, solo escribe 'Hola' nuevamente. | 🔑🏠 DANTE PROPIEDADES."
    
    # IMPORTANTE: Verificar primero si está en modo listado y el usuario envía un número
    # Esto debe estar ANTES de verificar "1" para venta
    if estado_usuario['paso'] == 'listado_propiedades' and text_lower.isdigit():
        try:
            indice = int(text_lower)
            propiedades = estado_usuario['propiedades_filtradas']
            
            if not propiedades:
                estado_usuario['paso'] = 'menu_principal'
                estado_usuario['timestamp'] = datetime.now().isoformat()
                actualizar_estado_usuario(user_id, estado_usuario)
                return "⚠️ No hay propiedades disponibles. Envía 'Hola' para volver al menú."
            
            if 1 <= indice <= len(propiedades):
                propiedad = obtener_detalle_propiedad(propiedades, indice)
                if propiedad:
                    estado_usuario['paso'] = 'detalle_propiedad'
                    estado_usuario['ultimo_indice_preguntado'] = indice
                    estado_usuario['timestamp'] = datetime.now().isoformat()
                    actualizar_estado_usuario(user_id, estado_usuario)
                    
                    # Determinar operación para el título
                    operacion = propiedad.get('operacion', '')
                    if operacion == 'venta':
                        titulo_op = "💰 VENTA"
                    elif operacion == 'alquiler':
                        titulo_op = "🔑 ALQUILER"
                    else:
                        titulo_op = "🏠 PROPIEDAD"
                    
                    mensaje = f"{titulo_op}\n"
                    mensaje += "─" * 30 + "\n"
                    mensaje += formatear_detalle_propiedad(propiedad)
                    
                    return mensaje
            else:
                return f"❌ El número {indice} está fuera de rango. Por favor, elige un número entre 1 y {len(propiedades)}."
                
        except ValueError:
            pass
    
    # SOLO si está en menú principal o detalle_propiedad, procesar opciones normales
    # OPCIÓN 1: VENTA
    elif text_lower == "1" and estado_usuario['paso'] in ['menu_principal', 'detalle_propiedad']:
        estado_usuario['paso'] = 'listado_propiedades'
        estado_usuario['operacion_seleccionada'] = 'venta'
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['timestamp'] = datetime.now().isoformat()
        
        # Cargar propiedades de venta
        propiedades_venta = filtrar_propiedades_por_operacion('venta')
        estado_usuario['propiedades_filtradas'] = propiedades_venta
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if not propiedades_venta:
            return "📭 *No hay propiedades en venta disponibles en este momento.*\n\nEnvía 'Hola' para volver al menú principal."
        
        mensaje = f"💰 *PROPIEDADES EN VENTA*\n"
        mensaje += f"Encontramos *{len(propiedades_venta)}* propiedades disponibles:\n\n"
        mensaje += generar_listado_propiedades(propiedades_venta)
        
        return mensaje
    
    # OPCIÓN 2: ALQUILER
    elif text_lower == "2" and estado_usuario['paso'] in ['menu_principal', 'detalle_propiedad']:
        estado_usuario['paso'] = 'listado_propiedades'
        estado_usuario['operacion_seleccionada'] = 'alquiler'
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['timestamp'] = datetime.now().isoformat()
        
        # Cargar propiedades de alquiler
        propiedades_alquiler = filtrar_propiedades_por_operacion('alquiler')
        estado_usuario['propiedades_filtradas'] = propiedades_alquiler
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if not propiedades_alquiler:
            return "📭 *No hay propiedades en alquiler disponibles en este momento.*\n\nEnvía 'Hola' para volver al menú principal."
        
        mensaje = f"🔑 *PROPIEDADES EN ALQUILER*\n"
        mensaje += f"Encontramos *{len(propiedades_alquiler)}* propiedades disponibles:\n\n"
        mensaje += generar_listado_propiedades(propiedades_alquiler)
        
        return mensaje
    
    # Si está en detalle de propiedad y envía un número (para ver otra propiedad)
    elif estado_usuario['paso'] == 'detalle_propiedad' and text_lower.isdigit():
        try:
            indice = int(text_lower)
            propiedades = estado_usuario['propiedades_filtradas']
            
            if 1 <= indice <= len(propiedades):
                propiedad = obtener_detalle_propiedad(propiedades, indice)
                if propiedad:
                    estado_usuario['ultimo_indice_preguntado'] = indice
                    estado_usuario['timestamp'] = datetime.now().isoformat()
                    actualizar_estado_usuario(user_id, estado_usuario)
                    
                    operacion = propiedad.get('operacion', '')
                    if operacion == 'venta':
                        titulo_op = "💰 VENTA"
                    elif operacion == 'alquiler':
                        titulo_op = "🔑 ALQUILER"
                    else:
                        titulo_op = "🏠 PROPIEDAD"
                    
                    mensaje = f"{titulo_op}\n"
                    mensaje += "─" * 30 + "\n"
                    mensaje += formatear_detalle_propiedad(propiedad)
                    
                    return mensaje
            else:
                return f"❌ El número {indice} está fuera de rango. Elige entre 1 y {len(propiedades)}."
        except ValueError:
            pass
    
    # Si está en detalle de propiedad y quiere volver
    elif estado_usuario['paso'] == 'detalle_propiedad':
        if text_lower.isdigit():
            try:
                indice = int(text_lower)
                propiedades = estado_usuario['propiedades_filtradas']
                
                if 1 <= indice <= len(propiedades):
                    propiedad = obtener_detalle_propiedad(propiedades, indice)
                    if propiedad:
                        estado_usuario['ultimo_indice_preguntado'] = indice
                        estado_usuario['timestamp'] = datetime.now().isoformat()
                        actualizar_estado_usuario(user_id, estado_usuario)
                        
                        operacion = propiedad.get('operacion', '')
                        if operacion == 'venta':
                            titulo_op = "💰 VENTA"
                        elif operacion == 'alquiler':
                            titulo_op = "🔑 ALQUILER"
                        else:
                            titulo_op = "🏠 PROPIEDAD"
                        
                        mensaje = f"{titulo_op}\n"
                        mensaje += "─" * 30 + "\n"
                        mensaje += formatear_detalle_propiedad(propiedad)
                        
                        return mensaje
            except ValueError:
                pass
    
    # OPCIONES 3, 4, 6 (próximamente)
    elif text_lower == "3":
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📍 *Búsqueda por zona* - Esta funcionalidad estará disponible próximamente.\n\nEnvía 'Hola' para volver al menú."
    
    elif text_lower == "4":
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🔍 *Búsqueda libre* - Esta funcionalidad estará disponible próximamente.\n\nEnvía 'Hola' para volver al menú."
    
    elif text_lower == "6":
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        return "ℹ️ *Información* - Esta funcionalidad estará disponible próximamente.\n\nEnvía 'Hola' para volver al menú."
    
    
    
    # MENSAJE NO RECONOCIDO
    else:
        estado_usuario['timestamp'] = datetime.now().isoformat()
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if estado_usuario['paso'] == 'menu_principal':
            # Resetear estado y mostrar bienvenida para cualquier mensaje en el menú principal
            # Esto permite "activar" el bot con cualquier texto
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['operacion_seleccionada'] = None
            estado_usuario['propiedades_filtradas'] = []
            estado_usuario['ultimo_indice_preguntado'] = None
            estado_usuario['timestamp'] = datetime.now().isoformat()
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return "WELCOME_FLOW_TRIGGER"
        elif estado_usuario['paso'] == 'listado_propiedades':
            return f"Por favor, elige un número del listado o envía 'Hola' para volver al menú."
        elif estado_usuario['paso'] == 'detalle_propiedad':
            return f"Para ver otra propiedad, elige un número del listado o envía 'Hola' para volver al menú."
        else:
            return f"No entendí tu mensaje. Para volver al inicio, envía 'Hola'."





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
        
        # ========== TRANSFORMAR NÚMERO PARA SANDBOX ==========
        def transform_number(number):
            if number == "5491151511579":
                return "54111551511579"
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
            if error_code == 10:  # Token expirado
                log("⚠️  TOKEN EXPIRADO - Debes renovarlo en Meta Developers")
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "Token expirado. Renueva el token en Meta Developers.",
                    "details": "Ve a: https://developers.facebook.com/apps/"
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


def send_whatsapp_image(to_number, image_url, caption=""):
    """Envía una imagen por WhatsApp"""
    try:
        # Verificar token primero
        token_valid, _ = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar imagen")
            return False
        
        # Transformar número si es necesario
        def transform_number(number):
            if number == "5491151511579":
                return "54111551511579"
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
    welcome_message = """🔑🏠 *DANTE PROPIEDADES*

¡Hola! Soy el asistente inmobiliario de Dante Propiedades.

*¿Qué tipo de operación te interesa?*
Escribí el número de tu opción:

1️⃣ *💰 VENTA* - Propiedades en venta
2️⃣ *🔑 ALQUILER* - Propiedades en alquiler
3️⃣ *📍 Búsqueda por zona* (próximamente)
4️⃣ *🔍 Búsqueda libre* (próximamente)
5️⃣ *📋 Ver todas las propiedades*
6️⃣ *ℹ️ Información* (próximamente)
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
                                        log(f"🤖 RESPUESTA GENERADA ({len(response_text)} caracteres)")
                                        
                                        # Enviar respuesta normal
                                        result = send_whatsapp_message(from_number, response_text)
                                    
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