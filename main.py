from config import *
from utils import *
from database import *
from whatsapp_api import *
from tasaciones import *
from citas import *
from menu_handlers import *
# key = request.args.get('key')
    # if key != ADMIN_ACCESS_KEY:
    #     return jsonify({"error": "Unauthorized"}), 403




from config import ADMIN_NUMBER # El emisor (...6523)
from flask import Flask, request, jsonify, send_from_directory, send_file
import requests
import os
import json
import re
from datetime import datetime, timedelta
from collections import deque
import threading
import pandas as pd
from io import BytesIO
from googleapiclient.discovery import build
from google.oauth2 import service_account
# from pdf_generator import generar_pdf_propiedad


# ========== CONFIGURACIÓN GOOGLE CALENDAR ==========
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_calendar_key.json'


try:
    import psycopg2
except ImportError:
    print("❌ ERROR: No se encontró 'psycopg2'. Asegúrate de que 'psycopg2-binary' esté en requirements.txt")
    # En algunos entornos locales podría ser necesario instalarlo manualmente
    # o usar un fallback si fuera crítico, pero en Render debe venir de requirements.txt
    psycopg2 = None

from functools import lru_cache
import time




app = Flask(__name__)


# ========== CACHE TOKEN WHATSAPP ==========
whatsapp_token_cache = {"valid": False, "expires_at": 0}
whatsapp_token_lock = threading.Lock()


# Los valores de configuración se importan desde 'config.py'
# VERIFY_TOKEN, ACCESS_TOKEN, PHONE_NUMBER_ID, ADMIN_NUMBER, etc.
BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
BASE_URL_AI = os.environ.get("BASE_URL_AI", "http://localhost:8001")
LEADS_FILE = "leads.json"
# ADMIN_ACCESS_KEY = "dante2026"
ADMIN_ACCESS_KEY = os.getenv('ADMIN_KEY', 'dante_admin_2024')
CITAS_FILE = "citas.json"
HORARIOS_FILE = "dias-horarios-visitas.json"
FICHAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas")
os.makedirs(FICHAS_DIR, exist_ok=True)


# ========== CONFIGURACIÓN DE CITAS ==========
CITAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]

# ========== FUNCIONES UTILITARIAS ==========

# ========== ENDPOINT PARA FICHAS PDF ==========
@app.route('/fichas/<prop_id>')
def serve_ficha_pdf(prop_id):
    """Sirve la ficha técnica en PDF de una propiedad (debe estar pre-generada)"""
    try:
        # Limpiar el ID por si viene con .pdf o espacios
        prop_id = prop_id.replace('.pdf', '').strip()
        log(f"📂 Solicitud de ficha para: '{prop_id}' (DIR: {FICHAS_DIR})")
        
        # Intentar varias combinaciones de nombres
        posibles_rutas = [
            os.path.join(FICHAS_DIR, f"{prop_id}.pdf"),
            os.path.join(FICHAS_DIR, f"FICHA_{prop_id}.pdf"),
            os.path.join(FICHAS_DIR, f"{prop_id.upper()}.pdf"),
            os.path.join(FICHAS_DIR, f"FICHA_{prop_id.upper()}.pdf")
        ]
        
        filepath = None
        for ruta in posibles_rutas:
            log(f"🔍 Buscando ficha en: {ruta}")
            if os.path.exists(ruta):
                filepath = ruta
                break
        
        # Verificar si existe el archivo
        if not filepath:
            log(f"❌ FICHA NO ENCONTRADA tras agotar opciones para: {prop_id}", "ERROR")
            # Listar qué archivos hay para depurar
            try:
                archivos = os.listdir(FICHAS_DIR)
                log(f"📁 Archivos disponibles en {FICHAS_DIR}: {archivos[:10]}...")
            except: pass
            
            return f"La ficha técnica para {prop_id} no está disponible actualmente. Un asesor puede enviártela manualmente.", 404
        
        return send_file(filepath, mimetype='application/pdf')
    except Exception as e:
        log(f"❌ Error sirviendo PDF {prop_id}: {e}", "ERROR")
        return "Error al acceder al documento", 500

# ========== SERVIDOR DE IMÁGENES PARA CATÁLOGO ==========
@app.route('/imgs/<path:filename>')
def serve_image(filename):
    """Sirve imágenes de la carpeta imgs/ para que Meta las pueda descargar"""
    return send_from_directory('imgs', filename)

# ========== DATA FEED PARA CATÁLOGO DE META ==========
@app.route('/api/catalog/feed')
def catalog_feed():
    """Genera un archivo CSV compatible con Meta Commerce Manager (Home Listings)"""
    try:
        import csv
        from io import StringIO
        
        propiedades = cargar_propiedades_cached()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Encabezados oficiales de Meta para Inmuebles (Home Listings)
        headers = [
            'home_listing_id', 'name', 'availability', 'address', 'neighborhood',
            'city', 'region', 'country', 'price', 'image_link', 'link',
            'description', 'property_type', 'num_rooms', 'area_size', 'area_unit'
        ]
        writer.writerow(headers)
        
        for p in propiedades:
            # Mapeo de campos
            pid = p.get('id_temporal', '')
            name = p.get('titulo', 'Sin Titulo')
            
            # Disponibilidad
            op = p.get('operacion', '').lower()
            availability = 'for_sale' if op == 'venta' else 'for_rent' if op == 'alquiler' else 'for_sale'
            
            # Precio (Formato: 100000.00 USD)
            precio = p.get('precio', 0)
            moneda = p.get('moneda_precio', 'USD')
            price_str = f"{precio:.2f} {moneda}"
            
            # Imagen (Usar la primera foto si existe)
            fotos = p.get('fotos', [])
            image_link = ""
            if fotos:
                # Fotos suelen venir como "imgs/nombre.jpg"
                foto_name = os.path.basename(fotos[0])
                image_link = f"{BASE_URL}/imgs/{foto_name}"
            
            # Link a la ficha (usamos el PDF como destino)
            link = f"{BASE_URL}/fichas/{pid}"
            
            # Ubicación
            direccion = p.get('direccion_completa', p.get('direccion', 'Capital Federal, Argentina'))
            barrio = p.get('barrio', 'Buenos Aires')
            
            # Tipo de propiedad (Mapeo a valores Meta)
            tipo_orig = p.get('tipo', '').lower()
            if 'departam' in tipo_orig: p_type = 'apartment'
            elif 'casa' in tipo_orig: p_type = 'house'
            elif 'ph' in tipo_orig: p_type = 'house' # O 'apartment'
            elif 'terreno' in tipo_orig: p_type = 'land'
            else: p_type = 'other'
            
            writer.writerow([
                pid,
                name,
                availability,
                direccion,
                barrio,
                'Buenos Aires', 'CABA', 'AR', # Valores por defecto para la zona
                price_str,
                image_link,
                link,
                p.get('descripcion', '')[:1000], # Limitar descripción
                p_type,
                p.get('ambientes', 1),
                p.get('metros_cuadrados', 0),
                'sq m'
            ])
            
        csv_data = output.getvalue()
        return csv_data, 200, {'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename=catalog_feed.csv'}
        
    except Exception as e:
        log(f"❌ Error generando Feed de Catálogo: {e}", "ERROR")
        return "Error interno", 500


# ========== GESTIÓN DE ESTADO DE USUARIOS ==========
estados_usuarios = {}
processed_message_ids = deque(maxlen=1000)  # Aumentado para manejar más mensajes

# ========== CONEXIÓN A POSTGRESQL (Render) ==========



    
    
    
    
# ========== FUNCIONES MEJORADAS CON CACHÉ ==========



            
            
# ========== GESTIÓN DE LEADS MEJORADA ==========

        # NO fallar completamente, solo loguear error

# ========== CARGAR PROPIEDADES CON VALIDACIÓN ==========
PROPIEDADES_FILE = "propiedades.json"


# ========== LOGGING MEJORADO ==========

# ========== FUNCIONES PARA PROPIEDADES OPTIMIZADAS ==========




# ========== HANDLER DE IA PORTALES ==========
def manejar_charla_ia_portal(text, estado_usuario, user_id):
    import portal_ia
    from database import cargar_propiedades_cached

    prop_id = estado_usuario.get('propiedad_ia_id')
    historial = estado_usuario.get('historial_ia', [])
    
    # Generar respuesta
    respuesta, intencion = portal_ia.generar_respuesta_ia(text, historial, prop_id)
    
    # Actualizar historial
    historial.append({"role": "user", "content": text})
    historial.append({"role": "assistant", "content": respuesta})
    
    if intencion == "AGENDAR":
        # Limpiar estado IA para devolverlo al flujo normal pero mandar el trigger
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['historial_ia'] = []
        
        # Configurar la propiedad guardada para que si el cliente acepta, sepa cual es
        propiedades = cargar_propiedades_cached()
        prop = next((p for p in propiedades if p.get('id_temporal') == prop_id), None)
        
        if prop:
            # Setear ultimo indice como si lo hubiera elegido en listado
            for i, p in enumerate(propiedades, 1):
                if p.get('id_temporal') == prop_id:
                    estado_usuario['ultimo_indice_preguntado'] = i
                    break
            estado_usuario['propiedades_filtradas'] = propiedades
            prop_titulo = prop.get('titulo')
        else:
            prop_titulo = "Propiedad seleccionada"
            
        actualizar_estado_usuario(user_id, estado_usuario)
        return f"OFFER_MEETING_TRIGGER|{prop_titulo}"

    # Si la charla sigue, guardar historial
    estado_usuario['historial_ia'] = historial[-10:] # Max 10 ultimos
    actualizar_estado_usuario(user_id, estado_usuario)
    return respuesta

# ========== BOT OPTIMIZADO ==========
def get_bot_response(text, user_id):
    """Responde con un mensaje simple, manteniendo estado de usuario"""
    try:
        start_time = time.time()
        text_lower = text.lower().strip()
        
        estado_usuario = obtener_estado_usuario(user_id)
        log(f"👤 Usuario {user_id}: {estado_usuario['paso']}")
        
        # 1. COMANDOS UNIVERSALES
        if text_lower in ["9", "menu", "principal", "inicio"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': [],
                'ultimo_indice_preguntado': None,
                'timestamp': datetime.now().isoformat()
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "WELCOME_FLOW_TRIGGER"
        
        if text_lower in ["0", "salir", "exit"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': []
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"

        # Comandos de compatibilidad
        if text_lower in ["hola", "hi", "hello", "volver", "atras"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': [],
                'ultimo_indice_preguntado': None,
                'timestamp': datetime.now().isoformat()
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "WELCOME_FLOW_TRIGGER"
        
        # 2. ACCIONES ESPECIALES
        if text_lower == "8":
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            
            if indice and 1 <= indice <= len(propiedades):
                propiedad = propiedades[indice - 1]
                log(f"🎯 ACCIÓN: Me interesa (Prop ID: {propiedad.get('id_temporal')})")
                estado_usuario['paso'] = 'esperando_nombre_lead'
                actualizar_estado_usuario(user_id, estado_usuario)
                
                # REGISTRAR LEAD INMEDIATAMENTE - FIX PostgreSQL
                try:
                    registrar_lead(user_id, propiedad.get('id_temporal'), 'click_me_interesa', f"Interés expresado en Propiedad: {propiedad.get('titulo')}")
                    # NOTIFICACIÓN INMEDIATA AL AGENTE
                    notificar_agente(f"👀 *INTERÉS INICIAL*\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad.get('titulo')}\n_(Esperando que el usuario ingrese su nombre...)_")
                except Exception as e:
                    log(f"⚠️ Error registrando lead inicial: {e}")
                    
                return f"✅ ¡Genial! Me interesa la propiedad: *{propiedad.get('titulo')}*.\n\nPor favor, decime tu *Nombre y Apellido* para que un asesor te contacte."
            else:
                return "⚠️ Por favor, primero selecciona una propiedad del listado."

        if text_lower == "f":
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            if indice and 1 <= indice <= len(propiedades):
                propiedad = propiedades[indice - 1]
                return f"PHOTOS_TRIGGER|{propiedad.get('id_temporal')}"
            else:
                return "⚠️ Por favor, primero selecciona una propiedad del listado para ver las fotos."
        
        if text_lower == "p":
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            if indice and 1 <= indice <= len(propiedades):
                propiedad = propiedades[indice - 1]
                prop_id = propiedad.get('id_temporal')
                return f"📄 *Aquí tenés la ficha técnica oficial de {prop_id} para descargar:*\n{BASE_URL}/fichas/{prop_id}"
            else:
                return "⚠️ Por favor, primero selecciona una propiedad del listado para obtener el PDF."
                
        # 2.5 LÓGICA DE PORTALES E IA
        import portal_ia
        paso = estado_usuario.get('paso', 'menu_principal')
        
        # Si entra un link de portal O el usuario está en medio de la charla IA
        if portal_ia.es_consulta_portal(text_lower) or paso == 'charla_ia_portal':
            if portal_ia.es_consulta_portal(text_lower):
                from database import cargar_propiedades_cached
                propiedades = cargar_propiedades_cached()
                prop_id = portal_ia.extraer_id_propiedad_con_ia(text, propiedades)
                
                if prop_id:
                    estado_usuario.update({
                        'paso': 'charla_ia_portal',
                        'propiedad_ia_id': prop_id,
                        'historial_ia': []
                    })
                    actualizar_estado_usuario(user_id, estado_usuario)
                    return manejar_charla_ia_portal(text, estado_usuario, user_id)
                # Si falló la extracción, sigue el flujo normal como búsqueda o fallback
            elif paso == 'charla_ia_portal':
                return manejar_charla_ia_portal(text, estado_usuario, user_id)
        
        # 3. LÓGICA POR ESTADO
        
        if paso == 'submenu_consultar':
            return manejar_submenu_consultar(text_lower, estado_usuario, user_id)
            
        elif paso == 'submenu_visita':
            return manejar_submenu_visita(text_lower, estado_usuario, user_id)
            
        elif paso == 'submenu_asesor':
            return manejar_submenu_asesor(text_lower, estado_usuario, user_id)

        elif paso == 'filtro_tipo':
            return manejar_filtro_tipo(text_lower, estado_usuario, user_id)
            
        elif paso == 'filtro_ambientes':
            return manejar_filtro_ambientes(text_lower, estado_usuario, user_id)

        elif paso == 'listado_propiedades':
            return manejar_listado_propiedades(text_lower, estado_usuario, user_id)
        
        elif paso == 'detalle_propiedad':
            return manejar_detalle_propiedad(text_lower, estado_usuario, user_id)
        
        elif paso == 'esperando_nombre_lead':
            return manejar_nombre_lead(text, estado_usuario, user_id)
        
        elif paso == 'ofrecer_cita':
            return manejar_ofrecer_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'solicitar_fecha_cita':
            return manejar_solicitar_fecha_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'seleccionar_hora_cita':
            return manejar_seleccionar_hora_cita(text, estado_usuario, user_id)
            
        elif paso == 'confirmar_cita':
            return manejar_confirmar_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'esperando_email_cita':
            return manejar_email_cita(text, estado_usuario, user_id)
        
        elif paso == 'esperando_feedback':
            return manejar_respuesta_feedback(text, estado_usuario, user_id)
        
        elif paso == 'esperando_confirmacion_recordatorio':
            return manejar_confirmacion_recordatorio(text, estado_usuario, user_id)
        
        elif paso == 'tasacion_operacion':
            return manejar_tasacion_operacion(text_lower, estado_usuario, user_id)
        
        elif paso == 'tasacion_barrio':
            return manejar_tasacion_barrio(text, estado_usuario, user_id)
            
        elif paso == 'tasacion_tipo':
            return manejar_tasacion_tipo(text_lower, estado_usuario, user_id)
            
        elif paso == 'tasacion_m2':
            return manejar_tasacion_m2(text, estado_usuario, user_id)
            
        elif paso == 'tasacion_ambientes':
            return manejar_tasacion_ambientes(text, estado_usuario, user_id)
            
        elif paso == 'tasacion_estado':
            return manejar_tasacion_estado(text_lower, estado_usuario, user_id)
            
        elif paso == 'tasacion_esperando_contacto':
            return manejar_tasacion_contacto(text_lower, estado_usuario, user_id)
        
        elif paso == 'vista_fotos':
            return "Para ver fotos, envía 'F' cuando estés en el detalle de una propiedad."

        # 4. BUSCADOR POR TEXTO (Nuevo) - SOLAMENTE SI NO HAY ESTADO ACTIVO PRIORITARIO
        # Y si el paso es menu_principal o resultado_busqueda
        if text_lower.startswith("buscar ") or (len(text_lower) > 3 and paso == 'menu_principal' and not text_lower.isdigit()):
            # DETECTAR SI ES UNA FECHA PERO SE PERDIÓ EL CONTEXTO
            fecha_detectada = analizar_fecha(text_lower)
            if fecha_detectada and len(text_lower.split()) <= 3: # Si es una fecha corta
                return """⚠️ *Sesión expirada o contexto perdido*
                
Parece que querías agendar una fecha, pero no tengo seleccionada ninguna propiedad en este momento.

Por favor:
1. Envía 'Hola' para ver el menú
2. Busca la propiedad nuevamente
3. Selecciona 'Agendar Cita'"""

            termino = text_lower.replace("buscar ", "").strip()
            return manejar_busqueda_keywords(termino, estado_usuario, user_id)

        # 5. OPCIONES DEL MENÚ PRINCIPAL
        if paso == 'menu_principal':
            return manejar_menu_principal(text_lower, estado_usuario, user_id)
        
        # Respuesta por defecto
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log(f"🔥 ERROR EN get_bot_response: {e}\n{error_trace}")
        return "❌ *Lo siento, ocurrió un error interno.*\n\nPor favor, intenta de nuevo enviando 'Hola' o contacta al administrador."


# ========== MANEJADORES DE ESTADO ==========

# ========== MANEJADORES DE TASACIÓN ==========











# ========== MANEJADORES DE SUBMENÚS ==========



def manejar_respuesta_feedback(text, estado_usuario, user_id):
    """Maneja la respuesta del usuario al mensaje de feedback"""
    # Defensive: data might be a string if parsing failed elsewhere
    data_obj = estado_usuario.get('data', {})
    if isinstance(data_obj, str):
        try:
            data_obj = json.loads(data_obj)
        except:
            data_obj = {}
            
    propiedad = data_obj.get('propiedad_feedback', 'la propiedad')
    nombre = estado_usuario.get('nombre_cliente', 'Cliente')
    
    log(f"📩 FEEDBACK RECIBIDO de {user_id}: {text}")
    
    # Notificar al agente
    mensaje_agente = f"🚩 *NUEVO FEEDBACK RECIBIDO*\n\n"
    mensaje_agente += f"👤 *Cliente:* {nombre} ({user_id})\n"
    mensaje_agente += f"🏠 *Propiedad:* {propiedad}\n"
    mensaje_agente += f"💬 *Respuesta:* {text}"
    
    try:
        notificar_agente(mensaje_agente)
    except Exception as e:
        log(f"⚠️ Error notificando feedback al agente: {e}")
    
    # Reset estado a menú principal
    estado_usuario.update({
        'paso': 'menu_principal',
        'operacion_seleccionada': None,
        'timestamp': datetime.now().isoformat()
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return f"¡Muchas gracias por tu respuesta, *{nombre}*! 🙌 Ya le pasé tus comentarios al asesor responsable. Se va a estar contactando con vos a la brevedad. 😊\n\n¿En qué más te puedo ayudar?\n\n1️⃣ Ver más propiedades\n9️⃣ Volver al menú principal"








def mostrar_panel_admin():
    """Muestra el panel administrativo para Dante"""
    return f"""🔐 *PANEL ADMINISTRATIVO*

Hola Dante 👋

Opciones disponibles:

📊 *1. Ver dashboard principal*
📅 *2. Gestionar citas*
👥 *3. Ver leads*
🏠 *4. Gestionar propiedades*
📈 *5. Ver estadísticas*

📱 *0. Volver al menú principal*"""










# Helper para mostrar horarios (extraído para reusar)


def manejar_busqueda_keywords(termino, estado_usuario, user_id):
    """Busca propiedades por palabras clave y actualiza el estado"""
    global propiedades
    propiedades = cargar_propiedades_cached()
        
    terminos = termino.lower().split()
    resultados = []
    
    for p in propiedades:
        match_score = 0
        texto_busqueda = f"{p.get('titulo', '')} {p.get('descripcion', '')} {p.get('barrio', '')} {p.get('tipo', '')}".lower()
        
        for t in terminos:
            if t in texto_busqueda:
                match_score += 1
        
        if match_score >= len(terminos): # Deben coincidir todas las palabras clave
            resultados.append(p)
            
    if not resultados:
        return f"🔍 No encontré propiedades que coincidan con *'{termino}*. \n\nIntentá con otras palabras (ej: 'casa parque') o enviá 'Hola' para ver todo.\n0️⃣ *❌ SALIR*"
        
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'propiedades_filtradas': resultados,
        'operacion_seleccionada': 'busqueda'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    mensaje = f"🔎 *Resultados para: {termino}* ({len(resultados)})\n\n"
    for i, p in enumerate(resultados[:5]):
        mensaje += f"*{i+1}️⃣ {p.get('titulo')}*\n📍 {p.get('barrio', 'S/D')} - ${p.get('precio', 'S/D')}\n\n"
    
    if len(resultados) > 5:
        mensaje += "📝 _Mostrando los primeros 5 resultados..._\n"
        
    mensaje += "\n👉 *Respondé con el número* (1, 2, 3...) para ver más detalle.\n"
    mensaje += "0️⃣ *❌ SALIR*"
    return mensaje


# ========== FUNCIONES DE WHATSAPP API MEJORADAS ==========
# def check_token_validity():
#     """Verifica si el token de acceso es válido"""
#     try:
#         url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
#         headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
#         response = requests.get(url, headers=headers, timeout=10)
        
#         if response.status_code == 200:
#             data = response.json()
#             log(f"✅ Token válido: {data.get('verified_name', 'N/A')}")
#             return True, data
#         else:
#             error_data = response.json() if response.content else {}
#             log(f"❌ Token inválido: Status {response.status_code}")
#             return False, error_data
            
#     except Exception as e:
#         log(f"🔥 Error verificando token: {e}")
#         return False, {"error": str(e)}


def check_token_validity():
    """Verifica si el token de acceso es válido"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}?fields=verified_name"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            log(f"✅ Token válido. Verified name: {data.get('verified_name', 'N/A')}")
            return True, data

        else:
            error_data = response.json() if response.content else {}
            log(f"❌ Token inválido o sin permisos. Status {response.status_code}")
            log(f"Detalles: {error_data}")
            return False, error_data

    except Exception as e:
        log(f"🔥 Error verificando token: {e}")
        return False, {"error": str(e)}
    
    


# def notificar_agente(mensaje):
#     """
#     Envía una notificación al Agente (Dante).
#     Prioriza la variable de Render, luego la de config, y finalmente el hardcode.
#     """
#     # 1. Intentamos leer de Render directamente para evitar cache del config
#     # 2. Si no está en Render, buscamos si existe en el objeto config
#     # 3. Si todo falla, usamos tu número personal directamente.
    
#     try:
#         from config import AGENT_NUMBER
#     except ImportError:
#         AGENT_NUMBER = "5491136809319"

#     # VALIDACIÓN DINÁMICA: 
#     # Si la variable es igual al emisor, la forzamos al número correcto.
#     destino = os.getenv("AGENT_NUMBER", AGENT_NUMBER)
    
#     if destino == ADMIN_NUMBER or destino == "5491176596523":
#         log(f"⚠️ Detectado conflicto de números. Forzando destino al personal.")
#         destino = "5491136809319"

#     log(f"📢 Preparando notificación para el agente ({destino}): {mensaje[:30]}...")
    
#     # Armamos el texto final
#     texto_alerta = f"🔔 *ALERTA DANTE PROPIEDADES*\n\n{mensaje}"
    
#     # Llamamos a la función de envío original
#     resultado = send_whatsapp_message(destino, texto_alerta)
    
#     if resultado.get("status") == "success":
#         log(f"✅ Notificación enviada al agente: {resultado.get('message_id')}")
#     else:
#         log(f"❌ Error notificando al agente: {resultado.get('error_message')}", "ERROR")
        
#     return resultado






# ========== RUTAS PRINCIPALES ==========
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route("/")
def home():
    """Página principal"""
    propiedades = cargar_propiedades_cached()
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
                const btn = event.target;
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



@app.route("/debug/postgresql", methods=["GET"])
def debug_pg():
    """Depurar conexión a PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"conexion": "fallida", "error": "No se pudo conectar"}), 500
            
        cursor = conn.cursor()
        
        # 2. Ver tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tablas = [t[0] for t in cursor.fetchall()]
        
        # 3. Ver estructura de leads si existe
        estructura_leads = []
        if 'leads' in tablas:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'leads'
                ORDER BY ordinal_position
            """)
            estructura_leads = cursor.fetchall()
        
        # 4. Contar registros
        total_leads = 0
        if 'leads' in tablas:
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
        
        # 5. Probar inserción de prueba
        test_insert = False
        test_id = None
        try:
            cursor.execute("""
                INSERT INTO leads (telefono, nombre, accion, detalles)
                VALUES ('test_5491151511579', 'TEST DEBUG', 'debug_test', 'Prueba desde /debug/postgresql')
                RETURNING id
            """)
            test_id = cursor.fetchone()[0]
            conn.commit()
            test_insert = True
        except Exception as e:
            conn.rollback()
            test_error = str(e)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "conexion": "exitosa",
            "tablas": tablas,
            "estructura_leads": estructura_leads,
            "total_leads": total_leads,
            "test_insert": test_insert,
            "test_id": test_id if test_insert else None,
            "test_error": test_error if not test_insert else None,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "conexion": "fallida",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
        
@app.route("/debug/save-test", methods=["GET"])
def debug_save_test():
    """Probar guardado manual en PostgreSQL"""
    try:
        result = guardar_en_postgresql(
            telefono="5491151511579",
            nombre="TEST MANUAL",
            accion="test_manual",
            detalles="Prueba manual desde /debug/save-test"
        )
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Lead guardado manualmente en PostgreSQL",
                "lead_id": result,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No se pudo guardar en PostgreSQL",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# @app.route("/webhook", methods=["GET", "POST"])
# def webhook():
#     """Webhook para recibir mensajes de WhatsApp"""
#     log(f"🔔 WEBHOOK RECIBIDO - Método: {request.method}")
#     if request.method == "GET":
#         mode = request.args.get("hub.mode")
#         token = request.args.get("hub.verify_token")
#         challenge = request.args.get("hub.challenge")
        
#         log("🔍 Solicitud GET al webhook")
#         log(f"   Mode: {mode}, Token: {token}")
        
#         if mode and token:
#             if mode == "subscribe" and token == VERIFY_TOKEN:
#                 log("✅ Webhook verificado exitosamente")
#                 return challenge, 200
#             else:
#                 log("❌ Verificación fallida - Token incorrecto")
#                 return "Verification failed", 403
        
#         return "Webhook endpoint", 200
    
#     elif request.method == "POST":
#         # === LOG DE DIAGNÓSTICO EXTREMO ===
#         print("=" * 60)
#         print(f"🔔 WEBHOOK POST RECIBIDO - {datetime.now()}")
#         print(f"📋 HEADERS: {dict(request.headers)}")
        
#         # Obtener el body crudo
#         raw_body = request.get_data(as_text=True)
#         print(f"📦 RAW BODY (primeros 500 chars): {raw_body[:500]}")
#         print("=" * 60)
        
#         # También usar tu función log existente
#         log("📨 Nuevo webhook POST recibido")
#         log(f"📦 Body completo (primeros 500): {raw_body[:500]}")
        
#         try:
#             data = request.get_json()
            
#             if not data:
#                 log("❌ Datos JSON vacíos")
#                 print("❌ ERROR: Datos JSON vacíos")
#                 return jsonify({"status": "no_data"}), 200
            
#             print(f"✅ JSON parseado exitosamente")
#             log(f"📊 Estructura JSON: {json.dumps(data, indent=2)[:1000]}")
            
#             if data.get("object") != "whatsapp_business_account":
#                 log("❌ No es un webhook de WhatsApp Business")
#                 print("❌ ERROR: No es un webhook de WhatsApp Business")
#                 return jsonify({"status": "not_whatsapp"}), 200
            
#             # Contador de mensajes procesados
#             mensajes_procesados = 0
            
#             for entry in data.get("entry", []):
#                 for change in entry.get("changes", []):
#                     value = change.get("value", {})
                    
#                     if "messages" in value:
#                         messages = value["messages"]
#                         print(f"📨 Se encontraron {len(messages)} mensajes en el webhook")
#                         log(f"📨 Se encontraron {len(messages)} mensajes")
                        
#                         for message in messages:
#                             mensajes_procesados += 1
#                             message_id = message.get("id")
                            
#                             # Log detallado del mensaje
#                             print(f"\n--- Mensaje #{mensajes_procesados} ---")
#                             print(f"🆔 ID: {message_id}")
#                             print(f"👤 From: {message.get('from')}")
#                             print(f"📝 Type: {message.get('type')}")
#                             print(f"📦 Mensaje completo: {json.dumps(message, indent=2)}")
                            
#                             if message_id in processed_message_ids:
#                                 log(f"🛑 Mensaje duplicado ignorado: {message_id}")
#                                 print(f"🛑 Mensaje duplicado ignorado: {message_id}")
#                                 continue
                                
#                             processed_message_ids.append(message_id)
                            
#                             from_number = message.get("from")
#                             message_text = ""
                            
#                             # Procesar mensajes de texto plano
#                             if message.get("type") == "text":
#                                 message_text = message.get("text", {}).get("body", "")
#                                 print(f"💬 Texto recibido: '{message_text}'")
#                                 log(f"💬 Texto recibido de {from_number}: '{message_text}'")
                            
#                             # Procesar mensajes interactivos (Botones nativos o Listas)
#                             elif message.get("type") == "interactive":
#                                 interactive = message.get("interactive", {})
#                                 int_type = interactive.get("type")
#                                 print(f"🔘 Mensaje interactivo tipo: {int_type}")
                                
#                                 if int_type == "button_reply":
#                                     message_text = interactive.get("button_reply", {}).get("id", "")
#                                     log(f"🔘 Botón presionado: {message_text}")
#                                     print(f"🔘 Botón presionado ID: {message_text}")
                                    
#                                 elif int_type == "list_reply":
#                                     message_text = interactive.get("list_reply", {}).get("id", "")
#                                     log(f"📋 Opción de lista seleccionada: {message_text}")
#                                     print(f"📋 Lista seleccionada ID: {message_text}")
                            
#                             else:
#                                 print(f"⚠️ Tipo de mensaje no manejado: {message.get('type')}")
#                                 log(f"⚠️ Tipo de mensaje no manejado: {message.get('type')}")
                            
#                             if from_number and message_text:
#                                 # Convertir IDs de botones a los comandos originales numéricos para compatibilidad
#                                 boton_a_numero = {
#                                     "opcion_1": "1",  # Ventas
#                                     "opcion_2": "2",  # Alquiler
#                                     "opcion_3": "3",  # Sitio Web
#                                     "opcion_4": "4",  # Mis Citas
#                                     "opcion_5": "5",  # Hablar Asesor
#                                     "opcion_6": "6",  # FAQs
#                                     "opcion_7": "7",  # Todos los Inmuebles
#                                     "opcion_tasacion": "10", # Tasación
#                                     "volver_menu": "9",
#                                     "salir_chat": "0"
#                                 }
                                
#                                 # Si el mensaje fue un botón/lista del menú principal, traducirlo
#                                 if message_text in boton_a_numero:
#                                     original_text = message_text
#                                     message_text = boton_a_numero[message_text]
#                                     print(f"🔄 Traduciendo botón: '{original_text}' → '{message_text}'")
                                
#                                 print(f"👤 Usuario: {from_number}, Input Procesado: '{message_text}'")
#                                 log(f"👤 Usuario: {from_number}, Input Procesado: {message_text}")
                                
#                                 # Llamar a get_bot_response
#                                 print(f"🤖 Llamando a get_bot_response con input: '{message_text}'")
#                                 response_text = get_bot_response(message_text, from_number)
#                                 print(f"🤖 Respuesta del bot: {response_text[:100]}..." if response_text else "🤖 Respuesta vacía")
                                
#                                 if response_text == "WELCOME_FLOW_TRIGGER":
#                                     log("🎯 Enviando flujo de bienvenida interactivo")
#                                     print("🎯 Enviando flujo de bienvenida interactivo")
#                                     result = send_welcome_flow(from_number)
#                                 elif response_text and response_text.startswith("OFFER_MEETING_TRIGGER|"):
#                                     prop_titulo = response_text.split("|")[1]
#                                     text_body = f"✅ *¡Perfecto!*\n\nHemos registrado tu interés en:\n🏠 *{prop_titulo}*\n\n📅 *¿Te gustaría agendar una cita para visitar la propiedad?*"
#                                     botones = [
#                                         {"id": "agendar", "title": "📅 SÍ, AGENDAR CITA"},
#                                         {"id": "solo info", "title": "📋 Solo información"},
#                                         {"id": "ofertar", "title": "💰 Quiero ofertar"}
#                                     ]
#                                     result = send_whatsapp_interactive_buttons(from_number, text_body, botones)
#                                 elif response_text and response_text.startswith("CONFIRM_MEETING_TRIGGER|"):
#                                     partes = response_text.split("|")
#                                     fecha_display = partes[1]
#                                     hora = partes[2]
#                                     email = partes[3]
                                    
#                                     text_body = f"📅 *RESUMEN DE TU VISITA*\n\n📅 Fecha: *{fecha_display}*\n⏰ Hora: *{hora} hs*\n📧 Email: *{email}*\n\n¿Confirmas la cita?"
#                                     botones = [
#                                         {"id": "confirmar", "title": "✅ Confirmar cita"},
#                                         {"id": "cambiar", "title": "🔄 Cambiar hora"},
#                                         {"id": "cancelar", "title": "❌ Cancelar"}
#                                     ]
#                                     result = send_whatsapp_interactive_buttons(from_number, text_body, botones)
#                                 elif response_text and response_text.startswith("PHOTOS_TRIGGER|"):
#                                     prop_id = response_text.split("|")[1]
#                                     base_url = request.host_url.rstrip('/')
#                                     if "onrender.com" in base_url and not base_url.startswith("https"):
#                                         base_url = base_url.replace("http://", "https://")
                                    
#                                     log(f"🚀 Iniciando hilo de fotos para propiedad {prop_id}")
#                                     print(f"🚀 Iniciando hilo de fotos para propiedad {prop_id}")
#                                     thread = threading.Thread(target=send_photos_async, args=(from_number, prop_id, base_url))
#                                     thread.start()
                                    
#                                     confirmacion = "📸 *Enviando fotos...* Esto puede tardar unos segundos.\n\nEnvía 'Hola' para volver al menú."
#                                     result = send_whatsapp_message(from_number, confirmacion)
#                                 elif response_text:
#                                     print(f"📤 Enviando mensaje: {response_text[:100]}...")
#                                     result = send_whatsapp_message(from_number, response_text)
#                                 else:
#                                     print("⚠️ response_text vacío, omitiendo envío")
#                                     result = {"status": "skipped", "reason": "empty_response"}
                                
#                                 print(f"📊 Resultado envío: {result.get('status')}")
#                                 log(f"📊 Resultado: {result.get('status')}")
#                                 return jsonify({
#                                     "status": "processed",
#                                     "user": from_number,
#                                     "result": result
#                                 }), 200
#                             else:
#                                 print(f"⚠️ Mensaje sin contenido procesable: from_number={from_number}, message_text='{message_text}'")
#                                 log(f"⚠️ Mensaje sin contenido procesable: from={from_number}, text={message_text}")
                    
#                     elif "statuses" in value:
#                         for status in value["statuses"]:
#                             log(f"📊 Estado de mensaje: {status.get('status')} para ID: {status.get('id')}")
#                             print(f"📊 Estado update: {status.get('status')} - ID: {status.get('id')}")
#                         return jsonify({"status": "status_update"}), 200
            
#             if mensajes_procesados == 0:
#                 print("ℹ️ Webhook sin mensajes para procesar")
#                 log("ℹ️ Webhook sin mensajes de texto para procesar")
#                 return jsonify({"status": "no_text_messages"}), 200
#             else:
#                 print(f"✅ Procesados {mensajes_procesados} mensajes")
#                 return jsonify({"status": "processed", "count": mensajes_procesados}), 200
                
#         except Exception as e:
#             print(f"❌ ERROR EXCEPCIÓN: {str(e)}")
#             import traceback
#             print(f"❌ TRACEBACK: {traceback.format_exc()}")
#             log(f"❌ Error procesando webhook: {str(e)}")
#             log(f"❌ Traceback: {traceback.format_exc()}")
#             return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook para recibir mensajes de WhatsApp - Versión Asincrónica"""
    if request.method == "GET":
        # Mantenemos tu lógica de verificación intacta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            log("✅ Webhook verificado exitosamente")
            return challenge, 200
        return "Verification failed", 403
    
    elif request.method == "POST":
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "no_data"}), 200

        # === EL CAMBIO CLAVE ===
        # Lanzamos toda tu lógica pesada en un hilo separado
        # Esto permite responderle a Meta '200 OK' en milisegundos
        threading.Thread(target=procesar_logica_pesada_dante, args=(data,)).start()
        
        # Le decimos a Meta: "Recibido, gracias". La conexión se cierra acá.
        return jsonify({"status": "received"}), 200

def procesar_logica_pesada_dante(data):
    """Aquí se mudaron tus 200 líneas de lógica original"""
    try:
        # Usamos un context manager si es necesario para Flask (opcional según tu config)
        # with app.app_context(): 
        
        log("📨 Procesando mensaje en segundo plano...")
        
        if data.get("object") != "whatsapp_business_account":
            return

        mensajes_procesados = 0
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Manejo de estados (leído, entregado, etc)
                if "statuses" in value:
                    for status in value["statuses"]:
                        log(f"📊 Estado: {status.get('status')} - ID: {status.get('id')}")
                    continue

                # Manejo de mensajes reales
                if "messages" in value:
                    for message in value["messages"]:
                        mensajes_procesados += 1
                        message_id = message.get("id")
                        
                        # Evitar duplicados
                        if message_id in processed_message_ids:
                            continue
                        processed_message_ids.append(message_id)
                        
                        from_number = message.get("from")
                        message_text = ""
                        
                        # --- TU LÓGICA DE TEXTO E INTERACTIVOS (INTACTA) ---
                        if message.get("type") == "text":
                            message_text = message.get("text", {}).get("body", "")
                        elif message.get("type") == "interactive":
                            interactive = message.get("interactive", {})
                            int_type = interactive.get("type")
                            if int_type == "button_reply":
                                message_text = interactive.get("button_reply", {}).get("id", "")
                            elif int_type == "list_reply":
                                message_text = interactive.get("list_reply", {}).get("id", "")

                        if from_number and message_text:
                            # Tu diccionario de traducción de botones
                            boton_a_numero = {
                                "opcion_1": "1", "opcion_2": "2", "opcion_3": "3",
                                "opcion_4": "4", "opcion_5": "5", "opcion_6": "6",
                                "opcion_7": "7", "opcion_tasacion": "10",
                                "volver_menu": "9", "salir_chat": "0"
                            }
                            if message_text in boton_a_numero:
                                message_text = boton_a_numero[message_text]

                            # Llamada a la IA y envío de respuestas
                            response_text = get_bot_response(message_text, from_number)
                            
                            # --- TUS TRIGGERS DE FLUJOS (BIENVENIDA, CITAS, FOTOS) ---
                            if response_text == "WELCOME_FLOW_TRIGGER":
                                send_welcome_flow(from_number)
                            elif response_text and response_text.startswith("OFFER_MEETING_TRIGGER|"):
                                # ... tu lógica de botones de cita ...
                                prop_titulo = response_text.split("|")[1]
                                text_body = f"✅ *¡Perfecto!*\n\nHemos registrado tu interés en:\n🏠 *{prop_titulo}*\n\n📅 *¿Te gustaría agendar una cita?*"
                                botones = [{"id": "agendar", "title": "📅 SÍ, AGENDAR"}, {"id": "solo info", "title": "📋 Solo info"}]
                                send_whatsapp_interactive_buttons(from_number, text_body, botones)
                            elif response_text and response_text.startswith("PHOTOS_TRIGGER|"):
                                prop_id = response_text.split("|")[1]
                                # Usamos tu lógica de thread para fotos también
                                threading.Thread(target=send_photos_async, args=(from_number, prop_id, "https://meta-rjpb.onrender.com")).start()
                            elif response_text:
                                send_whatsapp_message(from_number, response_text)

        log(f"✅ Hilo finalizado: {mensajes_procesados} mensajes procesados.")

    except Exception as e:
        log(f"❌ Error en hilo de procesamiento: {str(e)}")
        print(traceback.format_exc())



# ========== GESTIÓN DE CITAS ==========





def manejar_confirmacion_recordatorio(text, estado_usuario, user_id):
    """Maneja la respuesta del usuario al recordatorio de cita"""
    text = text.strip()
    
    # Intentar extraer ID de la cita del mensaje
    import re
    match = re.search(r'(CONFIRMAR|CANCELAR|REPROGRAMAR)[-\s]*(\d+)', text.upper())
    
    if match:
        comando = match.group(1)
        cita_id = int(match.group(2))
        log(f"🔍 Respuesta con ID específico: {comando} para cita {cita_id}")
        cita = buscar_cita_por_id(cita_id)
    else:
        # Tipeo simple: CONFIRMAR, CANCELAR, REPROGRAMAR
        text_upper = text.upper()
        if text_upper in ["CONFIRMAR", "CANCELAR", "REPROGRAMAR"]:
            comando = text_upper
            # Prioridad: usar el ID guardado en DATA al enviar el recordatorio
            data_obj = estado_usuario.get('data', {})
            if isinstance(data_obj, str):
                try: data_obj = json.loads(data_obj)
                except: data_obj = {}
                
            cita_id = data_obj.get('ultimo_recordatorio_cita_id')
            if cita_id:
                log(f"🔍 Tipeo simple '{comando}', usando ID del estado guardado: {cita_id}")
                cita = buscar_cita_por_id(cita_id)
            else:
                log(f"⚠️ Tipeo simple '{comando}' sin ID en data, buscando cita activa...")
                cita = buscar_cita_activa_usuario(user_id)
        else:
            # Fallback total: palabras clave sueltas
            log("⚠️ Respuesta no estructurada, buscando cita activa por keywords...")
            cita = buscar_cita_activa_usuario(user_id)
            if cita:
                if any(word in text.lower() for word in ["confirm", "si", "sí", "voy", "dale", "ok"]):
                    comando = "CONFIRMAR"
                elif any(word in text.lower() for word in ["cancel", "no voy", "baja"]):
                    comando = "CANCELAR"
                elif any(word in text.lower() for word in ["reprogramar", "cambiar", "otro dia"]):
                    comando = "REPROGRAMAR"
                else:
                    comando = "DESCONOCIDO"
            else:
                comando = "DESCONOCIDO"
    
    if cita:
        cita_id = cita['id']
    
    if not cita:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "No encontré una cita pendiente para vos. ¿En qué puedo ayudarte? Envía 'Hola' para ver el menú."

    # Procesar según el comando
    if comando == "CONFIRMAR":
        actualizar_cita_db(cita_id, nuevo_estado='confirmada', nuevas_notas="Usuario confirmó la visita")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"✅ *CITA CONFIRMADA*\n👤 {cita['nombre']}\n📅 {cita['fecha']} {cita['hora']}")
        
        return f"✅ ¡Muchas gracias, *{cita['nombre']}*! Hemos registrado tu confirmación. Nos vemos el {datetime.strptime(cita['fecha'], '%Y-%m-%d').strftime('%d/%m')} a las {cita['hora']} hs. 👋"

    elif comando == "CANCELAR":
        actualizar_cita_db(cita_id, nuevo_estado='cancelada', nuevas_notas="Usuario canceló la visita")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"❌ *CITA CANCELADA*\n👤 {cita['nombre']}\n📅 {cita['fecha']} {cita['hora']}")
        
        return "Entiendo. Hemos cancelado la visita. Si en otro momento deseas agendar nuevamente, no dudes en avisarnos. ¡Que tengas un buen día! 🏠"

    elif comando == "REPROGRAMAR":
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        estado_usuario['cita_reprogramando_id'] = cita_id  # Guardar qué cita se reprograma
        props = cargar_propiedades_cached()
        for i, p in enumerate(props, 1):
            if p.get('id_temporal') == cita['propiedad_id']:
                estado_usuario['ultimo_indice_preguntado'] = i
                estado_usuario['propiedades_filtradas'] = props
                break
        
        actualizar_cita_db(cita_id, nuevas_notas=f"Usuario solicitó reprogramar")
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"🔄 *SOLICITUD DE REPROGRAMACIÓN*\n👤 {cita['nombre']}\n📅 Original: {cita['fecha']} {cita['hora']}")
        
        return "No hay problema, podemos reprogramarla. 😊 ¿Para qué día y horario te quedaría mejor? (ej: 'El jueves a las 11')"

    else:
        return "Por favor, respondé con *CONFIRMAR*, *CANCELAR* o *REPROGRAMAR* para gestionar tu cita."








# ========== RUTAS API ==========

@app.route("/api/enviar-recordatorios-manual", methods=["POST"])
def enviar_recordatorios_manual():
    """Endpoint para activar manualmente el envío de recordatorios"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Ejecutar script de recordatorios en segundo plano para evitar timeout
        import subprocess
        subprocess.Popen(['python', 'recordatorio_citas.py'])
        
        return jsonify({
            "status": "success",
            "message": "Proceso de recordatorios iniciado en segundo plano."
        })
        
    except Exception as e:
        log(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
def actualizar_ids_json():  # ← ELIMINADO 'async'
    """Actualiza el archivo JSON con los IDs reales de PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            log("⚠️ No se pudo conectar a PostgreSQL")
            return
            
        cursor = conn.cursor()
        
        # Obtener todas las citas de PostgreSQL
        cursor.execute("SELECT id, telefono, fecha_cita, hora_cita FROM citas")
        citas_db = cursor.fetchall()
        
        # Cargar JSON actual
        if not os.path.exists('citas.json'):
            log("⚠️ citas.json no encontrado")
            cursor.close()
            conn.close()
            return
            
        with open('citas.json', 'r', encoding='utf-8') as f:
            citas_json = json.load(f)
        
        # Actualizar IDs
        actualizadas = 0
        for cita_json in citas_json:
            for cita_db in citas_db:
                if (cita_json.get('telefono') == cita_db[1] and 
                    cita_json.get('fecha') == cita_db[2].strftime('%Y-%m-%d') and 
                    cita_json.get('hora') == cita_db[3]):
                    cita_json['id'] = f"pg_{cita_db[0]}"
                    actualizadas += 1
                    break
        
        # Guardar JSON actualizado
        with open('citas.json', 'w', encoding='utf-8') as f:
            json.dump(citas_json, f, indent=4, ensure_ascii=False)
            
        cursor.close()
        conn.close()
        log(f"✅ IDs de PostgreSQL actualizados en citas.json ({actualizadas} citas)")
        
    except Exception as e:
        log(f"⚠️ Error actualizando IDs en JSON: {e}")

@app.route("/api/sincronizar/citas", methods=["POST"])
def sincronizar_citas_manual():
    """Sincroniza citas entre JSON y PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a PostgreSQL"}), 500
        
        cursor = conn.cursor()
        
        # Verificar si existe citas.json
        if not os.path.exists('citas.json'):
            return jsonify({"error": "Archivo citas.json no encontrado"}), 404
            
        with open('citas.json', 'r', encoding='utf-8') as f:
            citas_json = json.load(f)
        
        if not citas_json:
            return jsonify({"message": "No hay citas en JSON", "creadas": 0, "actualizadas": 0})
        
        sincronizadas = 0
        creadas = 0
        errores = []
        
        for cita in citas_json:
            try:
                # Verificar si ya existe
                cursor.execute("""
                    SELECT id FROM citas 
                    WHERE telefono = %s AND fecha_cita = %s AND hora_cita = %s
                """, (
                    cita.get('telefono'), 
                    cita.get('fecha'), 
                    cita.get('hora')
                ))
                
                if not cursor.fetchone():
                    # Insertar nueva
                    cursor.execute("""
                        INSERT INTO citas (
                            nombre, telefono, email, fecha_cita, hora_cita,
                            propiedad_id, estado, notas, fecha_creacion
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        cita.get('nombre', 'Cliente'),
                        cita.get('telefono'),
                        cita.get('email', ''),
                        cita.get('fecha'),
                        cita.get('hora'),
                        cita.get('propiedad_id', ''),
                        cita.get('estado', 'pendiente'),
                        cita.get('notas', ''),
                        cita.get('creacion', datetime.now().isoformat())
                    ))
                    creadas += 1
                else:
                    # Actualizar existente
                    cursor.execute("""
                        UPDATE citas SET 
                            estado = %s, 
                            notas = %s,
                            email = %s
                        WHERE telefono = %s AND fecha_cita = %s AND hora_cita = %s
                    """, (
                        cita.get('estado', 'pendiente'),
                        cita.get('notas', ''),
                        cita.get('email', ''),
                        cita.get('telefono'),
                        cita.get('fecha'),
                        cita.get('hora')
                    ))
                    sincronizadas += 1
                    
            except Exception as e:
                errores.append(f"Error con cita {cita.get('id', 'desconocida')}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Sincronización completada",
            "creadas": creadas,
            "actualizadas": sincronizadas,
            "errores": errores if errores else None
        })
        
    except Exception as e:
        log(f"❌ Error en sincronización: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500
    

@app.route("/api/citas/<int:cita_id>", methods=["DELETE"])
def eliminar_cita(cita_id):
    """Elimina una cita permanentemente"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM citas WHERE id = %s RETURNING id", (cita_id,))
        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not deleted:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # También eliminar de JSON
        try:
            if os.path.exists('citas.json'):
                with open('citas.json', 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                citas_json = [c for c in citas_json 
                             if c.get('id') != cita_id 
                             and c.get('id') != f"cita_{cita_id:04d}"
                             and c.get('id') != f"pg_{cita_id}"]
                
                with open('citas.json', 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
        except Exception as json_e:
            log(f"⚠️ Error eliminando de JSON: {json_e}")
        
        log(f"✅ Cita {cita_id} eliminada")
        return jsonify({"status": "success", "message": "Cita eliminada"})
        
    except Exception as e:
        log(f"❌ Error eliminando cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500



@app.route("/api/citas/<int:cita_id>", methods=["GET"])
def obtener_cita_por_id(cita_id):
    """Obtiene los datos de una cita específica por su ID"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, email, fecha_cita, hora_cita,
                propiedad_id, estado, notas
            FROM citas 
            WHERE id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not cita:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # Formatear respuesta
        return jsonify({
            "id": cita[0],
            "nombre": cita[1],
            "telefono": cita[2],
            "email": cita[3] or "",
            "fecha": cita[4].strftime('%Y-%m-%d') if cita[4] else None,
            "hora": cita[5],
            "propiedad_id": cita[6] or "",
            "estado": cita[7] or "pendiente",
            "notas": cita[8] or ""
        })
        
    except Exception as e:
        log(f"❌ Error obteniendo cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/api/citas/<int:cita_id>", methods=["PUT"])
def actualizar_cita(cita_id):
    """Actualiza los datos de una cita"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    log(f"📝 Solicitud de edición para cita {cita_id}")
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        # Validar fecha para evitar errores de tipo DATE en PG
        fecha_valida = data.get('fecha')
        if not fecha_valida or fecha_valida == "" or fecha_valida == "null":
            fecha_valida = None

        cursor.execute("""
            UPDATE citas 
            SET nombre = %s, email = %s, fecha_cita = %s, 
                hora_cita = %s, notas = %s, estado = %s,
                propiedad_id = %s
            WHERE id = %s
        """, (
            data.get('nombre'),
            data.get('email'),
            fecha_valida,
            data.get('hora'),
            data.get('notas'),
            data.get('estado', 'pendiente'),
            data.get('propiedad_id'),
            cita_id
        ))
        
        filas = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if filas == 0:
            return jsonify({"error": "Cita no encontrada"}), 404
            
        log(f"✅ Cita {cita_id} actualizada correctamente")
        return jsonify({"status": "success", "message": "Cita actualizada"})
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        log(f"❌ Error actualizando cita {cita_id}: {error_msg}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        return jsonify({"error": error_msg, "traceback": traceback.format_exc()}), 500


@app.route("/api/citas/<int:cita_id>/estado", methods=["PUT"])
def cambiar_estado_cita(cita_id):
    """Cambia el estado de una cita (pendiente, confirmada, cancelada, completada)"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    nuevo_estado = request.args.get('estado')
    if not nuevo_estado or nuevo_estado not in ['pendiente', 'confirmada', 'completada', 'cancelada']:
        return jsonify({"error": "Estado inválido"}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE citas 
            SET estado = %s
            WHERE id = %s
            RETURNING id, nombre, estado
        """, (nuevo_estado, cita_id))
        
        updated = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not updated:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # También actualizar en JSON si existe
        try:
            if os.path.exists('citas.json'):
                with open('citas.json', 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                for c in citas_json:
                    if c.get('id') == cita_id or c.get('id') == f"cita_{cita_id:04d}" or c.get('id') == f"pg_{cita_id}":
                        c['estado'] = nuevo_estado
                        c['ultima_actualizacion'] = datetime.now().isoformat()
                        break
                
                with open('citas.json', 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
        except Exception as json_e:
            log(f"⚠️ Error actualizando JSON: {json_e}")
        
        log(f"✅ Estado de cita {cita_id} cambiado a {nuevo_estado}")
        
        return jsonify({
            "status": "success",
            "message": f"Estado cambiado a {nuevo_estado}",
            "cita": {
                "id": updated[0],
                "nombre": updated[1],
                "estado": updated[2]
            }
        })
        
    except Exception as e:
        log(f"❌ Error cambiando estado de cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/run-daily-tasks', methods=['POST'])
def run_daily_tasks():
    """Ejecutar las tareas diarias manualmente"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import subprocess
        log("👨‍💻 Administrador inició ejecución manual de tareas diarias")
        
        if os.name == 'nt':
            subprocess.Popen(['python', 'cron_diario.py'], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(['python', 'cron_diario.py'], preexec_fn=os.setpgrp)
            
        return jsonify({
            "status": "success", 
            "message": "Las tareas diarias (recordatorios y seguimientos) han comenzado a ejecutarse en segundo plano."
        })
    except Exception as e:
        log(f"Error ejecutando tareas diarias: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/sync-calendar-all', methods=['POST'])
def sync_calendar_all():
    """Ejecutar la sincronización masiva de citas con Google Calendar"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import subprocess
        log("👨‍💻 Administrador inició sincronización masiva con Google Calendar")
        
        if os.name == 'nt':
            subprocess.Popen(['python', 'sincronizar_calendar.py'], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(['python', 'sincronizar_calendar.py'], preexec_fn=os.setpgrp)
            
        return jsonify({
            "status": "success", 
            "message": "La sincronización masiva con Google Calendar ha comenzado en segundo plano."
        })
    except Exception as e:
        log(f"Error ejecutando sincronización de calendario: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/admin")
def admin_panel():
    """Sirve el panel de administración con mejor manejo de errores"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return "⚠️ Acceso No Autorizado. Por favor usa el enlace seguro.", 403
    
    # Intentar diferentes rutas posibles
    possible_paths = [
        'admin.html',
        './admin.html',
        '/opt/render/project/src/admin.html',
        os.path.join(os.getcwd(), 'admin.html')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                return send_file(path)
            except Exception as e:
                log(f"❌ Error enviando archivo {path}: {e}")
                continue
    
    # Si no se encuentra, mostrar información de debug
    import glob
    all_html = glob.glob('*.html')
    
    return jsonify({
        "error": "Archivo admin.html no encontrado",
        "current_directory": os.getcwd(),
        "files_in_directory": os.listdir('.'),
        "html_files_found": all_html,
        "possible_paths_tried": possible_paths
    }), 404

@app.route("/api/leads", methods=["GET"])
def api_leads():
    """Retorna todos los leads desde PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, fecha, telefono, nombre, propiedad_id, propiedad_titulo, accion, detalles
            FROM leads 
            ORDER BY fecha DESC
            LIMIT 1000
        """)
        
        leads = cursor.fetchall()
        
        leads_formateados = []
        for lead in leads:
            leads_formateados.append({
                "id": lead[0],
                "timestamp": lead[1].isoformat() if lead[1] else None,
                "user_id": lead[2],
                "nombre": lead[3],
                "propiedad_id": lead[4],
                "propiedad_titulo": lead[5],
                "accion": lead[6],
                "detalle": lead[7]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({"leads": leads_formateados})
        
    except Exception as e:
        log(f"❌ Error en api_leads: {e}", "ERROR")
        return jsonify({"error": str(e), "leads": []}), 500

@app.route('/api/leads/<string:lead_id>', methods=['DELETE'])
def eliminar_lead(lead_id):
    """Eliminar un lead"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Manejar prefijo pg_
        if lead_id.startswith('pg_'):
            internal_id = lead_id[3:]
        else:
            internal_id = lead_id

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No db connection"}), 500
            
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = %s", (internal_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": f"Lead #{lead_id} eliminado"})
    except Exception as e:
        log(f"Error eliminando lead: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<string:lead_id>', methods=['PUT'])
def actualizar_lead(lead_id):
    """Actualizar datos de un lead"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Manejar prefijo pg_
        if lead_id.startswith('pg_'):
            internal_id = lead_id[3:]
        else:
            internal_id = lead_id

        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No db connection"}), 500
            
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET nombre = %s, detalles = %s
            WHERE id = %s
        """, (data.get('nombre'), data.get('detalles'), internal_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": f"Lead #{lead_id} actualizado"})
    except Exception as e:
        log(f"Error actualizando lead: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500





# ========== RUTAS DE PRUEBA ==========
@app.route("/test", methods=["GET"])
def test_send():
    """Endpoint de prueba manual"""
    test_number = "5491151511579"
    test_message = "✅ ¡Hola! Este es un mensaje de prueba desde el bot inmobiliario."
    
    result = send_whatsapp_message(test_number, test_message)
    
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
    propiedades = cargar_propiedades_cached()
    
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

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    token_valid, _ = check_token_validity()
    propiedades = cargar_propiedades_cached()
    
    return jsonify({
        "status": "healthy" if token_valid else "unhealthy_token",
        "service": "whatsapp-bot-inmobiliario",
        "version": "2.2",
        "timestamp": datetime.now().isoformat(),
        "token_valid": token_valid,
        "propiedades_cargadas": len(propiedades),
        "venta_count": len([p for p in propiedades if p.get('operacion') == 'venta']),
        "alquiler_count": len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    })


def debug_postgresql():
    """Debug detallado de PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        log("🔍 DEBUG: Conectado a PostgreSQL...")
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        tablas = cursor.fetchall()
        log(f"📊 DEBUG: Tablas en PostgreSQL: {[t[0] for t in tablas]}")
        
        # Verificar estructura de tabla leads
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'leads'
        """)
        
        columnas = cursor.fetchall()
        log(f"📊 DEBUG: Columnas en tabla 'leads': {columnas}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        log(f"📊 DEBUG: Total leads en PostgreSQL: {total}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log(f"❌ DEBUG ERROR PostgreSQL: {e}")
        import traceback
        log(f"🔍 DEBUG TRACEBACK: {traceback.format_exc()}")
        return False





def probar_conexion_postgresql():
    """Probar conexión a PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        # Asegurar esquema al inicio
        init_db(conn)
        
        cursor = conn.cursor()
        
        # Verificar si la tabla leads existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'leads'
            )
        """)
        
        tabla_existe = cursor.fetchone()[0]
        
        if tabla_existe:
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
            log(f"✅ PostgreSQL: Tabla 'leads' existe con {total_leads} registros")
        else:
            log("⚠️ PostgreSQL: Tabla 'leads' NO existe")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log(f"❌ Error conectando a PostgreSQL: {e}")
        return False


@app.route("/test-pg-now", methods=["GET"])
def test_pg_now():
    """Probar PostgreSQL inmediatamente"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "No se pudo conectar"}), 500
            
        cursor = conn.cursor()
        
        # Insertar registro de prueba
        cursor.execute("""
            INSERT INTO leads (telefono, nombre, accion, detalles)
            VALUES ('test_5491151511579', 'TEST INMEDIATO', 'test_inmediato', 'Prueba desde endpoint /test-pg-now')
            RETURNING id, fecha
        """)
        
        result = cursor.fetchone()
        lead_id = result[0]
        fecha = result[1]
        
        conn.commit()
        
        # Contar total
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "✅ PostgreSQL funcionando correctamente",
            "lead_id": lead_id,
            "fecha": fecha.isoformat(),
            "total_leads": total,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ PostgreSQL error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route("/debug/leads", methods=["GET"])
def debug_leads():
    """Depurar leads"""
    leads_json = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'r', encoding='utf-8') as f:
            leads_json = json.load(f)
    
    # Probar conexión PostgreSQL
    try:
        conn = get_db_connection()
        if not conn:
            total_pg = "Error de conexión"
        else:
            cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_pg = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except Exception as e:
        total_pg = f"Error: {str(e)}"
    
    return jsonify({
        "leads_json": len(leads_json),
        "leads_postgresql": total_pg,
        "ultimo_lead": leads_json[-1] if leads_json else None,
        "archivo": os.path.exists(LEADS_FILE)
    })


@app.route("/api/internal/send-feedback", methods=["POST"])
def send_appointment_feedback():
    """
    Endpoint interno para enviar mensajes de feedback post-visita.
    Invocado por el script de seguimiento automático.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
            
        user_id = data.get("user_id")
        nombre = data.get("nombre", "Cliente")
        propiedad = data.get("propiedad", "la propiedad")
        cita_id = data.get("cita_id")
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
            
        log(f"✉️ Preparando mensaje de feedback para {nombre} ({user_id})")
        
        # Mensaje de feedback amigable
        mensaje = f"¡Hola *{nombre}*! 👋 Soy el asistente de *Dante Propiedades*.\n\n"
        mensaje += f"¿Qué te pareció la visita a la propiedad *{propiedad}*? 🏠\n\n"
        mensaje += "¿Te gustaría hacer una oferta, te interesaría verla de nuevo o prefieres que busquemos algo más para vos? 😊"
        
        # Enviar vía WhatsApp
        resultado = send_whatsapp_message(user_id, mensaje)
        
        if resultado.get("status") == "success":
            log(f"✅ Feedback enviado correctamente a {user_id}")
            
            # Actualizar estado del usuario a 'esperando_feedback'
            try:
                estado = obtener_estado_usuario(user_id)
                estado['paso'] = 'esperando_feedback'
                
                # Asegurar que 'data' sea un diccionario
                if 'data' not in estado or not isinstance(estado['data'], dict):
                    estado['data'] = {}
                
                estado['data']['propiedad_feedback'] = propiedad
                actualizar_estado_usuario(user_id, estado)
                log(f"🔄 Estado de {user_id} cambiado a 'esperando_feedback'")
            except Exception as e:
                log(f"⚠️ No se pudo actualizar el estado del usuario: {e}", "WARNING")

            # Registrar en DB si viene cita_id
            if cita_id:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE citas 
                        SET feedback_enviado = TRUE, 
                            feedback_enviado_en = NOW() 
                        WHERE id = %s
                    """, (cita_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
            
            return jsonify({
                "status": "success",
                "message": f"Feedback enviado a {user_id}",
                "whatsapp_id": resultado.get("message_id")
            })
        else:
            error_msg = resultado.get("error") or resultado.get("error_message") or "Error desconocido"
            log(f"❌ Error enviando feedback a {user_id}: {error_msg}", "ERROR")
            return jsonify({
                "status": "error",
                "message": "Error enviando WhatsApp",
                "details": error_msg
            }), 500
            
    except Exception as e:
        log(f"❌ Error en endpoint de feedback: {e}", "ERROR")
        import traceback
        log(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/api/internal/send-reminder", methods=["POST"])
def send_appointment_reminder():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_id = data.get('user_id')
        nombre = data.get('nombre', 'Cliente')
        fecha = data.get('fecha')
        hora = data.get('hora')
        propiedad = data.get('propiedad', 'la propiedad')
        cita_id = data.get('cita_id')  # ← NUEVO: recibir el ID de la cita
        
        # Validar campos
        missing = []
        if not user_id:
            missing.append('user_id')
        if not fecha:
            missing.append('fecha')
        if not hora:
            missing.append('hora')
        if not cita_id:
            missing.append('cita_id')  # ← NUEVO: validar ID
            
        if missing:
            return jsonify({"error": "Missing fields", "missing": missing}), 400
        
        # Formatear mensaje con el ID de la cita
        mensaje = f"""🔔 *RECORDATORIO DANTE PROPIEDADES*

Hola *{nombre}*! 😊

Te escribo para recordarte tu cita de mañana:

📅 *Fecha:* {fecha}
⏰ *Hora:* {hora} hs
🏠 *Propiedad:* {propiedad}

📍 Te esperamos. Para responder, escribí:

✅ *CONFIRMAR* o *CONFIRMAR-{cita_id}* para confirmar
❌ *CANCELAR* o *CANCELAR-{cita_id}* si no podrás asistir
🔄 *REPROGRAMAR* para cambiar fecha/hora

¡Gracias por confiar en Dante Propiedades! 🏠🗝️"""
        
        # Enviar mensaje
        result = send_whatsapp_message(user_id, mensaje)
        
        # Setear estado
        estado = obtener_estado_usuario(user_id)
        estado['paso'] = 'esperando_confirmacion_recordatorio'
        
        # Guardar el ID dentro de 'data' para que se persista en DB
        if 'data' not in estado or not isinstance(estado['data'], dict):
            estado['data'] = {}
        
        estado['data']['ultimo_recordatorio_cita_id'] = cita_id
        actualizar_estado_usuario(user_id, estado)
        
        log(f"🔔 Recordatorio enviado a {user_id} ({nombre}) para cita {cita_id}")
        return jsonify({
            "status": "success",
            "whatsapp_id": result.get('message_id')
        }), 200
        
    except Exception as e:
        log(f"❌ Error inesperado: {e}")
        return jsonify({"error": str(e)}), 500
    
    

# 🔥 NUEVOS ENDPOINTS PARA DIAGNÓSTICO
@app.route("/version-actual", methods=["GET"])
def version_actual():
    """Muestra la versión actual del bot"""
    return """
    <h1>✅ VERSIÓN CORRECTA - BOT INMOBILIARIO COMPLETO</h1>
    <p>Este es el código completo con sistema de citas, propiedades y PostgreSQL</p>
    <p><a href="/">Volver al inicio</a></p>
    <p><a href="/token-status">Verificar token</a></p>
    <p><a href="/debug-token-env">Debug variables</a></p>
    """

@app.route("/token-status", methods=["GET"])
def token_status():
    """Verifica el estado del token"""
    token_valid, token_info = check_token_validity()
    
    if token_valid:
        return jsonify({
            "valid": True,
            "status": 200,
            "name": token_info.get('verified_name', 'N/A'),
            "number": token_info.get('display_phone_number', 'N/A')
        })
    else:
        return jsonify({
            "valid": False,
            "error": "Token inválido o expirado",
            "details": token_info
        }), 401

@app.route("/debug-token-env", methods=["GET"])
def debug_token_env():
    """Muestra información de la variable de entorno del token"""
    token_from_env = os.environ.get("WHATSAPP_TOKEN", "NO_ENV_VAR")
    token_from_code = ACCESS_TOKEN
    
    return jsonify({
        "env_var_exists": "WHATSAPP_TOKEN" in os.environ,
        "token_from_env_preview": token_from_env[:20] + "..." if len(token_from_env) > 20 else token_from_env,
        "token_from_code_preview": token_from_code[:20] + "...",
        "tokens_match": token_from_env == token_from_code if token_from_env != "NO_ENV_VAR" else False,
        "environment_keys": list(os.environ.keys())
    })

@app.route("/check-code", methods=["GET"])
def check_code():
    """Verifica que el código es la versión correcta"""
    return "✅ CÓDIGO CORRECTO - Versión completa con sistema de citas"

@app.route("/test-envio", methods=["GET"])
def test_envio_simple():
    """Endpoint ultra simple para probar envío directo"""
    try:
        numero = "5411515151579"  # Formato directo sin 9
        mensaje = "🔔 PRUEBA DIRECTA - BOT INMOBILIARIO COMPLETO"
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": mensaje}
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return jsonify({
            "status_code": response.status_code,
            "respuesta": response.json(),
            "token_usado": ACCESS_TOKEN[:30] + "..."
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MAIN

@app.route("/debug-version", methods=["GET"])
def debug_version():
    """Muestra información de la versión del código"""
    import hashlib
    import os
    
    # Hash del archivo actual
    with open(__file__, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    # Verificar si existen los endpoints
    endpoints = {
        "version-actual": "version_actual" in dir(),
        "token-status": "token_status" in dir(),
        "debug-token-env": "debug_token_env" in dir(),
        "test-envio": "test_envio_simple" in dir()
    }
    
    # Última modificación del archivo
    mod_time = os.path.getmtime(__file__)
    mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        "status": "debug",
        "file_hash": file_hash,
        "last_modified": mod_date,
        "endpoints_presentes": endpoints,
        "python_version": os.environ.get('PYTHON_VERSION', 'unknown'),
        "render_deploy": os.environ.get('RENDER_DEPLOY', 'unknown')
    })

@app.route("/debug-python", methods=["GET"])
def debug_python():
    """Muestra la versión de Python que está usando Render"""
    import sys
    import platform
    
    return jsonify({
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
        "runtime_txt_content": open('runtime.txt').read().strip() if os.path.exists('runtime.txt') else 'No existe',
        "timestamp": datetime.now().isoformat()
    })

@app.route("/debug-db", methods=["GET"])
def debug_db():
    """Diagnóstico detallado de la conexión a PostgreSQL"""
    import psycopg2
    import os
    
    resultados = {
        "variable_db_url": "NO CONFIGURADA",
        "intento_conexion": False,
        "error_detalle": None,
        "timestamp": datetime.now().isoformat()
    }
    
    # 1. Verificar variable de entorno
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        resultados["variable_db_url"] = "CONFIGURADA (oculta)"
        # Mostrar solo los primeros caracteres por seguridad
        resultados["db_url_preview"] = db_url[:30] + "..." + db_url[-10:]
    else:
        resultados["variable_db_url"] = "NO EXISTE"
        return jsonify(resultados)
    
    # 2. Intentar conexión
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Probar consulta simple
        cursor.execute("SELECT 1")
        resultado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        resultados["intento_conexion"] = True
        resultados["consulta_prueba"] = resultado[0] == 1
        resultados["mensaje"] = "✅ Conexión exitosa"
        
    except Exception as e:
        resultados["intento_conexion"] = False
        resultados["error_detalle"] = str(e)
        resultados["tipo_error"] = type(e).__name__
    
    return jsonify(resultados)




@app.route("/api/citas", methods=["GET"])
def api_citas():
    """Retorna todas las citas desde PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a la base de datos", "citas": []}), 500
        
        cursor = conn.cursor()
        
        # Verificar si la tabla citas existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'citas'
            )
        """)
        tabla_existe = cursor.fetchone()[0]
        
        if not tabla_existe:
            cursor.close()
            conn.close()
            return jsonify({"error": "La tabla 'citas' no existe", "citas": []}), 200
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, fecha_cita, hora_cita,
                propiedad_id, estado, notas, fecha_creacion, email
            FROM citas 
            ORDER BY fecha_cita DESC, hora_cita DESC
        """)
        
        citas = cursor.fetchall()
        
        citas_formateadas = []
        for cita in citas:
            try:
                # Extraer campos con cuidado
                c_id = cita[0]
                nombre = cita[1] or "Sin nombre"
                telefono = cita[2] or ""
                f_cita = cita[3]
                hora = cita[4] or ""
                p_id = cita[5] or ""
                estado = cita[6] or "pendiente"
                notas = cita[7] or ""
                f_creacion = cita[8]
                email = cita[9] or ""
                
                # Formatear fechas de forma segura
                try:
                    fecha_str = f_cita.strftime('%Y-%m-%d') if hasattr(f_cita, 'strftime') else str(f_cita) if f_cita else None
                except:
                    fecha_str = str(f_cita) if f_cita else None
                
                try:
                    creacion_str = f_creacion.isoformat() if hasattr(f_creacion, 'isoformat') else str(f_creacion) if f_creacion else None
                except:
                    creacion_str = str(f_creacion) if f_creacion else None
                    
                citas_formateadas.append({
                    "id": c_id,
                    "nombre": nombre,
                    "telefono": telefono,
                    "fecha": fecha_str,
                    "hora": hora,
                    "propiedad_id": p_id,
                    "propiedad_titulo": "Propiedad",
                    "estado": estado,
                    "notas": notas,
                    "fecha_creacion": creacion_str,
                    "email": email
                })
            except Exception as item_e:
                log(f"⚠️ Error procesando cita individual: {item_e}")
                continue
        
        cursor.close()
        conn.close()
        return jsonify(citas_formateadas)
        
    except Exception as e:
        log(f"❌ Error en api_citas: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    
    
    
@app.route("/api/db-status", methods=["GET"])
def db_status():
    """Verifica el estado de la conexión a PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    status = {
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "connection_test": False,
        "tables": {},
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        conn = get_db_connection()
        if conn:
            status["connection_test"] = True
            cursor = conn.cursor()
            
            # Verificar tablas
            cursor.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            for table in cursor.fetchall():
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                status["tables"][table[0]] = {
                    "columns": table[1],
                    "rows": count
                }
            
            cursor.close()
            conn.close()
            status["message"] = "✅ Conexión exitosa"
        else:
            status["message"] = "❌ No se pudo conectar"
            
    except Exception as e:
        status["error"] = str(e)
        status["message"] = "❌ Error en la conexión"
    
    return jsonify(status)


@app.route("/api/propiedades", methods=["GET"])
def api_propiedades():
    """Retorna la lista de propiedades para el buscador del panel admin"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if os.path.exists("propiedades.json"):
            with open("propiedades.json", 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
            
            # Solo enviar los campos necesarios para el buscador
            propiedades_simplificadas = []
            for p in propiedades:
                propiedades_simplificadas.append({
                    "id": p.get("id_temporal"),
                    "titulo": p.get("titulo"),
                    "direccion": p.get("direccion"),
                    "barrio": p.get("barrio"),
                    "tipo": p.get("tipo"),
                    "operacion": p.get("operacion"),
                    "precio": p.get("precio"),
                    "moneda": p.get("moneda_precio"),
                    "m2": p.get("metros_cuadrados"),
                    "ambientes": p.get("ambientes")
                })
            
            return jsonify(propiedades_simplificadas)
        else:
            return jsonify([])
            
    except Exception as e:
        log(f"❌ Error en api_propiedades: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500

@app.route("/send-message", methods=["POST"])
def api_send_manual_message_main():
    """Endpoint para enviar mensajes manuales vía WhatsApp"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if not data or 'to' not in data or 'message' not in data:
        return jsonify({"error": "Datos incompletos"}), 400
    
    # send_whatsapp_message ya está disponible por el import global
    to_number = data['to']
    message_text = data['message']
    
    log(f"📝 Envío manual solicitado para {to_number}")
    resultado = send_whatsapp_message(to_number, message_text)
    
    if resultado.get("status") == "success":
        return jsonify(resultado), 200
    else:
        return jsonify(resultado), 500

@app.route("/api/config/horarios", methods=["GET"])
def api_config_horarios():
    """Obtiene la configuración de horarios"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if os.path.exists("dias-horarios-visitas.json"):
            with open("dias-horarios-visitas.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            # Configuración por defecto
            default_config = {
                "configuracion_global": {
                    "dias_habiles": [0, 1, 2, 3, 4],
                    "horarios": [
                        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                        "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
                        "17:00", "17:30", "18:00", "18:30"
                    ]
                },
                "propiedades": {}
            }
            return jsonify(default_config)
            
    except Exception as e:
        log(f"❌ Error en api_config_horarios: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/api/diagnostico-citas", methods=["GET"])
def diagnostico_citas():
    """Endpoint para diagnosticar citas para mañana"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, fecha_cita, hora_cita,
                estado, recordatorio_enviado, recordatorio_enviado_en
            FROM citas 
            WHERE fecha_cita = %s
            ORDER BY id
        """, (manana,))
        
        citas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "fecha": manana,
            "total_citas": len(citas),
            "citas": [{
                "id": c[0],
                "nombre": c[1],
                "telefono": c[2],
                "fecha": str(c[3]),
                "hora": c[4],
                "estado": c[5],
                "recordatorio_enviado": c[6],
                "recordatorio_enviado_en": str(c[7]) if c[7] else None
            } for c in citas]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db-check", methods=["GET"])
def db_check():
    """Verificación rápida de la base de datos"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    results = {}
    
    # Verificar variables de entorno
    results["database_url_exists"] = bool(os.getenv("DATABASE_URL"))
    
    # Intentar conexión
    try:
        conn = get_db_connection()
        results["connection_success"] = conn is not None
        
        if conn:
            cursor = conn.cursor()
            
            # Listar tablas
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [t[0] for t in cursor.fetchall()]
            results["tables"] = tables
            
            # Contar registros en citas
            if 'citas' in tables:
                cursor.execute("SELECT COUNT(*) FROM citas")
                results["citas_count"] = cursor.fetchone()[0]
            
            # Contar registros en leads
            if 'leads' in tables:
                cursor.execute("SELECT COUNT(*) FROM leads")
                results["leads_count"] = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            results["message"] = "✅ Conexión exitosa"
        else:
            results["message"] = "❌ No se pudo conectar"
            
    except Exception as e:
        results["error"] = str(e)
        results["message"] = "❌ Error"
    
    return jsonify(results)

@app.route("/debug-files", methods=["GET"])
def debug_files():
    """Muestra los archivos disponibles en el servidor"""
    import os
    files = os.listdir('.')
    html_files = [f for f in files if f.endswith('.html')]
    return jsonify({
        "current_directory": os.getcwd(),
        "all_files": files[:20],  # Primeros 20 archivos
        "html_files": html_files,
        "admin_html_exists": os.path.exists('admin.html'),
        "admin_html_size": os.path.getsize('admin.html') if os.path.exists('admin.html') else 0,
        "cwd": os.getcwd()
    })




@app.route('/api/enviar-seguimiento-manual', methods=['POST'])
def enviar_seguimiento_manual():
    """Endpoint para activar manualmente el envío de seguimientos post-visita"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import subprocess
        log("👨‍💻 Iniciando seguimiento post-visita manualmente")
        
        if os.name == 'nt':
            subprocess.Popen(['python', 'seguimiento_citas.py'], 
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(['python', 'seguimiento_citas.py'], 
                           preexec_fn=os.setpgrp)
        
        return jsonify({
            "status": "success",
            "message": "Proceso de seguimiento post-visita iniciado en segundo plano."
        })
        
    except Exception as e:
        log(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ CORRECCIÓN: El decorador debe estar al mismo nivel que la función
@app.route('/api/ejecutar-cron-diario', methods=['POST'])
def ejecutar_cron_diario():
    """Ejecuta el proceso diario completo (recordatorios + seguimiento)"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import subprocess
        import os
        log("📅 Ejecutando CRON DIARIO completo (recordatorios + seguimiento)")
        
        if os.name == 'nt':
            subprocess.Popen(['python', 'cron_diario.py'], 
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(['python', 'cron_diario.py'], 
                           preexec_fn=os.setpgrp)
        
        return jsonify({
            "status": "success",
            "message": "Cron diario iniciado (recordatorios + seguimiento)"
        })
        
    except Exception as e:
        log(f"❌ Error ejecutando cron diario: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE EXPORTACIÓN Y CALENDARIO ADICIONALES ==========

@app.route('/api/exportar/leads', methods=['GET'])
def export_leads_main():
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY: return jsonify({"error": "Unauthorized"}), 403
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        conn = get_db_connection()
        query = "SELECT fecha, telefono, nombre, propiedad_id, propiedad_titulo, accion, detalles FROM leads WHERE telefono IS NOT NULL"
        params = []
        if desde:
            query += " AND fecha >= %s"; params.append(desde)
        if hasta:
            query += " AND fecha <= %s"; params.append(f"{hasta} 23:59:59")
        query += " ORDER BY fecha DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Leads', index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'leads_dante_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/exportar/citas', methods=['GET'])
def export_citas_main():
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY: return jsonify({"error": "Unauthorized"}), 403
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        conn = get_db_connection()
        query = "SELECT id, nombre, email, telefono, fecha_cita as fecha, hora_cita as hora, propiedad_id, propiedad_titulo, estado, notas FROM citas WHERE 1=1"
        params = []
        if desde:
            query += " AND fecha_cita >= %s"; params.append(desde)
        if hasta:
            query += " AND fecha_cita <= %s"; params.append(hasta)
        query += " ORDER BY fecha_cita DESC, hora_cita DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Citas', index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'citas_dante_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/calendar/sync/<string:cita_id>', methods=['POST'])
def sync_calendar_main(cita_id):
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY: return jsonify({"error": "Unauthorized"}), 403
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email, telefono, fecha_cita, hora_cita, propiedad_titulo, notas FROM citas WHERE id = %s", (cita_id,))
        cita = cursor.fetchone()
        cursor.close(); conn.close()
        if not cita: return jsonify({"error": "No encontrada"}), 404
        service = get_calendar_service()
        if not service: return jsonify({"error": "Configura google_calendar_key.json"}), 500
        start_time = f"{cita[4]}T{cita[5]}:00"
        dt_start = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_time = (dt_start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        event = {
            'summary': f'Cita Inmobiliaria: {cita[1]}',
            'location': cita[6],
            'description': f'Tel: {cita[3]}\nEmail: {cita[2]}\nNotas: {cita[7]}',
            'start': {'dateTime': start_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({"status": "success", "link": event.get('htmlLink')})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/debug/calendar-key-status", methods=["GET"])
def debug_calendar_key_status():
    """Verifica el estado de la clave de Google Calendar"""
    import base64, json
    
    result = {
        "env_var_exists": False,
        "valid_base64": False,
        "valid_json": False,
        "has_private_key": False,
        "details": {}
    }
    
    b64_data = os.environ.get("GOOGLE_CALENDAR_KEY_B64")
    if b64_data:
        result["env_var_exists"] = True
        result["raw_length"] = len(b64_data)
        result["padding"] = len(b64_data) % 4
        
        try:
            # Intentar decodificar tal cual
            decoded = base64.b64decode(b64_data).decode('utf-8')
            creds = json.loads(decoded)
            result["valid_base64"] = True
            result["valid_json"] = True
            result["has_private_key"] = "private_key" in creds
            result["details"]["client_email"] = creds.get("client_email")
        except Exception as e:
            result["error"] = str(e)
            
            # Intentar con corrección de padding
            try:
                b64_fixed = b64_data.strip()
                missing = len(b64_fixed) % 4
                if missing:
                    b64_fixed += '=' * (4 - missing)
                decoded = base64.b64decode(b64_fixed).decode('utf-8')
                creds = json.loads(decoded)
                result["fixed_works"] = True
                result["fixed_padding_added"] = 4 - missing if missing else 0
            except:
                result["fixed_works"] = False
    
    return jsonify(result)



if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("🏠 🏠 🏠 WHATSAPP BOT INMOBILIARIO - VERSIÓN 2.1")
    print("=" * 60)
    
    # DEBUG: Probar PostgreSQL
    print("🔍 DEBUG: Probando PostgreSQL...")
    debug_postgresql()
    
    propiedades = cargar_propiedades()
    print(f"📊 Propiedades cargadas: {len(propiedades)}")

    
    # Probar conexión a PostgreSQL
    print("🔍 Probando conexión a PostgreSQL...")
    conexion_pg = probar_conexion_postgresql()
    
    
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
    
    print(f"🌐 URL: https://meta-rjpb.onrender.com")
    print(f"📁 Propiedades: {PROPIEDADES_FILE}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if conexion_pg:
        print("✅ PostgreSQL: Conectado correctamente")
    else:
        print("⚠️ PostgreSQL: No se pudo conectar (leads solo en JSON)")
    
    print("=" * 60 + "\n")
    
    
    # if __name__ == "__main__":
    #   app.run(debug=False)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)