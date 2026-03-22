import requests
import json
import time
from config import *
from utils import log, normalizar_numero_argentina
from io import BytesIO
from database import registrar_lead, cargar_propiedades_cached

processed_message_ids = set()

def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de WhatsApp usando texto directo"""
    try:
        token_valid, token_info = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar mensaje", "ERROR")
            return {"status": "error", "error_message": "Token inválido"}
        
        transformed_number = normalizar_numero_argentina(to_number)
        log(f"📤 Enviando mensaje a: {transformed_number}")
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "text",
            "text": {"preview_url": False, "body": message_text}
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Mensaje enviado exitosamente - ID: {message_id}")
            return {"status": "success", "message_id": message_id}
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Error desconocido')
            log(f"❌ Error API WhatsApp: {error_msg}", "ERROR")
            return {"status": "error", "error_message": error_msg}
            
    except Exception as e:
        log(f"🔥 Error inesperado enviando WhatsApp: {str(e)}", "ERROR")
        return {"status": "error", "error": str(e)}


def send_photos_async(user_id, propiedad_id, base_url):
    """Tarea ejecutada en hilo secundario para enviar fotos"""
    try:
        propiedades = cargar_propiedades_cached()
        propiedad = next((p for p in propiedades if p.get('id_temporal') == propiedad_id), None)
        
        if not propiedad:
            log(f"❌ No se encontró propiedad {propiedad_id}")
            return

        fotos = propiedad.get('fotos', [])
        if not fotos:
            send_whatsapp_message(user_id, "⚠️ No hay fotos disponibles para esta propiedad.")
            return

        send_whatsapp_message(user_id, f"📸 *Enviando {len(fotos)} fotos...*")

        for foto_path in fotos:
            img_url = f"{base_url}/{foto_path.lstrip('/')}"
            send_whatsapp_image(user_id, img_url)
            
        notificar_agente(f"👤 Cliente {user_id} está viendo fotos de: {propiedad.get('titulo')}")
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_fotos")
        
        send_whatsapp_message(user_id, "✅ *¡Fotos enviadas!*\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*")
        
        log(f"✅ Envío de fotos completado para {user_id}")
    except Exception as e:
        log(f"🔥 Error en hilo de fotos: {e}")


def send_whatsapp_image(to_number, image_url, caption=""):
    """Envía una imagen por WhatsApp"""
    try:
        token_valid, _ = check_token_validity()
        if not token_valid:
            return False
        
        # 🔥 MISMA TRANSFORMACIÓN PARA IMÁGENES
        def transform_number(number):
            # En producción usamos el número tal cual (formato E.164)
            return ''.join(filter(str.isdigit, str(number)))

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
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            log(f"✅ Imagen enviada: {image_url}")
            return True
        else:
            log(f"❌ Error enviando imagen")
            return False
            
    except Exception as e:
        log(f"🔥 Error enviando imagen: {str(e)}")
        return False


def send_whatsapp_interactive_buttons(to_number, text_body, buttons, header_text=None, footer_text=None):
    """Envía un mensaje con botones interactivos (máximo 3 botones).
    buttons: list de dicts [{"id": "btn_1", "title": "Opción 1"}, ...]"""
    try:
        token_valid, _ = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar botones", "ERROR")
            return {"status": "error", "error_message": "Token inválido"}

        transformed_number = normalizar_numero_argentina(to_number)
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Validar máximo 3 botones
        if len(buttons) > 3:
            log("⚠️ Se intentó mandar más de 3 botones. Recortando a 3.", "WARNING")
            buttons = buttons[:3]

        interactive_content = {
            "type": "button",
            "body": {"text": text_body[:1024]},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn.get("id")[:256],
                            "title": btn.get("title")[:20]
                        }
                    } for btn in buttons
                ]
            }
        }
        
        if header_text:
            interactive_content["header"] = {"type": "text", "text": header_text[:60]}
        if footer_text:
            interactive_content["footer"] = {"text": footer_text[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "interactive",
            "interactive": interactive_content
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Botones interactivos enviados a {transformed_number} - ID: {message_id}")
            return {"status": "success", "message_id": message_id}
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Error desconocido')
            log(f"❌ Error API WhatsApp (Botones): {error_msg}", "ERROR")
            return {"status": "error", "error_message": error_msg}
            
    except Exception as e:
        log(f"🔥 Error enviando botones interactivos: {str(e)}", "ERROR")
        return {"status": "error", "error": str(e)}


def send_whatsapp_list_menu(to_number, text_body, button_text, sections, header_text=None, footer_text=None):
    """Envía un menú de lista desplegable (hasta 10 opciones).
    sections: list de dicts [{"title": "Sección 1", "rows": [{"id": "id1", "title": "Op 1", "description": "Desc"}]}]"""
    try:
        token_valid, _ = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar lista", "ERROR")
            return {"status": "error", "error_message": "Token inválido"}

        transformed_number = normalizar_numero_argentina(to_number)
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        interactive_content = {
            "type": "list",
            "body": {"text": text_body[:1024]},
            "action": {
                "button": button_text[:20],
                "sections": []
            }
        }
        
        for idx, sec in enumerate(sections[:10]):
            section_data = {
                "title": sec.get("title", f"Sección {idx+1}")[:24],
                "rows": []
            }
            for row in sec.get("rows", [])[:10]:
                row_data = {
                    "id": row.get("id")[:200],
                    "title": row.get("title")[:24]
                }
                if "description" in row and row["description"]:
                    row_data["description"] = row["description"][:72]
                section_data["rows"].append(row_data)
            interactive_content["action"]["sections"].append(section_data)

        if header_text:
            interactive_content["header"] = {"type": "text", "text": header_text[:60]}
        if footer_text:
            interactive_content["footer"] = {"text": footer_text[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "interactive",
            "interactive": interactive_content
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Lista interactiva enviada a {transformed_number} - ID: {message_id}")
            return {"status": "success", "message_id": message_id}
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Error desconocido')
            log(f"❌ Error API WhatsApp (Lista): {error_msg}", "ERROR")
            return {"status": "error", "error_message": error_msg}
            
    except Exception as e:
        log(f"🔥 Error enviando lista interactiva: {str(e)}", "ERROR")
        return {"status": "error", "error": str(e)}


# def send_welcome_flow(user_id):
#     """Envía el flujo completo de bienvenida usando un Menú de Lista Interactivo"""
#     text_body = """🏠🗝️ *DANTE PROPIEDADES*

# ¡Hola! Soy el asistente inmobiliario de Dante Propiedades.
# *¿Cómo podemos ayudarte hoy?*"""
    
#     sections = [
#         {
#             "title": "Propiedades",
#             "rows": [
#                 {"id": "opcion_1", "title": "🏠 En Venta", "description": "Ver inmuebles disponibles para compra"},
#                 {"id": "opcion_2", "title": "🔑 En Alquiler", "description": "Ver inmuebles disponibles para alquiler"},
#                 {"id": "opcion_7", "title": "🏢 Todos los Inmuebles", "description": "Ver catálogo completo de propiedades"},
#                 {"id": "opcion_tasacion", "title": "📈 Tasación Virtual", "description": "Valora tu propiedad con nuestra IA"}
#             ]
#         },
#         {
#             "title": "Gestión y Contacto",
#             "rows": [
#                 {"id": "opcion_4", "title": "📋 Mis Citas", "description": "Ver mis visitas programadas"},
#                 {"id": "opcion_6", "title": "❓ Requisitos / FAQs", "description": "Dudas frecuentes al alquilar o comprar"},
#                 {"id": "opcion_5", "title": "👤 Hablar con asesor", "description": "Contacto directo con un humano"},
#                 {"id": "opcion_3", "title": "🌐 Sitio Web", "description": "Visitar dantepropiedades.com.ar"}
#             ]
#         }
#     ]
    
#     return send_whatsapp_list_menu(
#         to_number=user_id,
#         text_body=text_body,
#         button_text="Opciones",
#         sections=sections,
#         footer_text="Selecciona una opción del menú 👇"
#     )


def send_welcome_flow(user_id):
    """Envía el flujo completo de bienvenida usando un Menú de Lista Interactivo"""
    text_body = """🏠🗝️ *DANTE PROPIEDADES*

¡Hola! Soy el asistente inmobiliario de Dante Propiedades.
*¿Cómo podemos ayudarte hoy?*"""
    
    sections = [
        {
            "title": "Propiedades",
            "rows": [
                {"id": "opcion_1", "title": "🏠 En Venta", "description": "Ver inmuebles disponibles para compra"},
                {"id": "opcion_2", "title": "🔑 En Alquiler", "description": "Ver inmuebles disponibles para alquiler"},
                {"id": "opcion_7", "title": "🏢 Todos los Inmuebles", "description": "Ver catálogo completo de propiedades"},
                {"id": "opcion_tasacion", "title": "📈 Tasación Virtual", "description": "Valora tu propiedad con nuestra IA"}
            ]
        },
        {
            "title": "Gestión y Contacto",
            "rows": [
                {"id": "opcion_4", "title": "📋 Mis Citas", "description": "Ver mis visitas programadas"},
                {"id": "opcion_6", "title": "❓ Requisitos / FAQs", "description": "Dudas frecuentes al alquilar o comprar"},
                {"id": "opcion_5", "title": "👤 Hablar con asesor", "description": "Contacto directo con un humano"},
                {"id": "opcion_3", "title": "🌐 Sitio Web", "description": "Visitar dantepropiedades.com.ar"}
            ]
        }
    ]
    
    return send_whatsapp_list_menu(
        to_number=user_id,
        text_body=text_body,
        button_text="Opciones",
        sections=sections,
        footer_text="Selecciona una opción del menú 👇"
    )



def notificar_agente(mensaje):
    """Envía una notificación al número de Dante (ADMIN_NUMBER)"""
    log(f"📢 Preparando notificación para el agente ({ADMIN_NUMBER}): {mensaje[:50]}...")
    resultado = send_whatsapp_message(ADMIN_NUMBER, f"🔔 *ALERTA DANTE-INSIGHTS*\n{mensaje}")
    if resultado.get("status") == "success":
        log(f"✅ Notificación enviada al agente: {resultado.get('message_id')}")
    else:
        log(f"❌ Error notificando al agente: {resultado.get('error_message')}", "ERROR")
    return resultado
