from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime
import time
import hashlib

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQgxlj7yZA7a2wSWyWxTxoOFsMoefYOqxKIMjLkuZBiZBQZBIRorwAuHkomzJSsAEy2PuA3gFnlLYaLDKTRUhIcHZCx429QbTc3t7MGpt7OvI8QaNBnAl2sFm41W2zitSAWODVC2Miv16IIZBJMiZBOJYeKGv3F1ZCKUKev3iVKUqZC9ZCL3qXMD1zq7i7iOEncYsin6JjqlgHpEabykLccCJRKZBh9fKuKoVA9HSX38D9h0A4mWdaspK8TyNFU76Gz2Nclu4ZBPks3OdLMUX03F13eZATnwZDZD"
PHONE_NUMBER_ID = "1000705633118215"

def log(message, force_flush=True):
    """Función para logging con flush automático"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} {message}", flush=force_flush)

# ========== SIMPLE RESPONSE BOT ==========
def get_bot_response(text):
    """Responde con un mensaje simple"""
    text_lower = text.lower().strip()
    
    if text_lower in ["hola", "hi", "hello"]:
        return """¡Hola! Soy el asistente inmobiliario de Dante Propiedades. 😊

Decime qué operación necesitás:
Escribí el número de tu opción

1. 💰 Venta
2. 🔑 Alquiler
3. 📍 Búsqueda por zona
4. 🔍 Búsqueda libre
5. 📋 Ver todas
6. ℹ️ Información"""
    
    elif text_lower == "1":
        return "Has seleccionado Venta. Próximamente tendrás acceso a nuestras propiedades en venta."
    
    elif text_lower == "2":
        return "Has seleccionado Alquiler. Próximamente tendrás acceso a nuestras propiedades en alquiler."
    
    else:
        return f"Gracias por tu mensaje: '{text}'. Pronto tendremos más funcionalidades disponibles."

# ========== SEND WHATSAPP MESSAGE ==========
def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de WhatsApp usando texto directo"""
    try:
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
            "to": to_number,  # Usar el número directamente SIN transformar
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        log(f"📤 Enviando mensaje a {to_number}")
        log(f"💬 Mensaje: {message_text[:50]}...")
        
        # Enviar la solicitud
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        log(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Mensaje enviado exitosamente. ID: {message_id}")
            return {
                "status": "success",
                "message_id": message_id
            }
        else:
            error_data = result.get('error', {})
            error_code = error_data.get('code', 'N/A')
            error_message = error_data.get('message', 'Error desconocido')
            
            log(f"❌ Error: {error_code} - {error_message}")
            
            # Si falla el mensaje directo, intentamos con la plantilla hello_world
            if error_code in [131051, 132018]:
                log("🔄 Intentando con plantilla hello_world...")
                return send_hello_world_template(to_number)
            
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_message
            }
            
    except Exception as e:
        log(f"🔥 Error inesperado: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def send_hello_world_template(to_number):
    """Envía la plantilla hello_world como fallback"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"}
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            log("✅ Plantilla hello_world enviada exitosamente")
            return {
                "status": "success",
                "template_used": "hello_world"
            }
        else:
            log(f"❌ Error con plantilla: {response.status_code}")
            return {
                "status": "error",
                "details": response.json()
            }
            
    except Exception as e:
        log(f"🔥 Error con plantilla: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# ========== RUTAS PRINCIPALES ==========
@app.route("/")
def home():
    return """
    <h1>🤖 WhatsApp Bot RESPONDIENDO</h1>
    <p><strong>Estado:</strong> ✅ Bot activo</p>
    <p><strong>Envía 'Hola' al +1 555 149 2382</strong></p>
    <p>El bot responderá con mensajes directos</p>
    <p><strong>Token:</strong> <span id="tokenStatus">Verificando...</span></p>
    <script>
        fetch('/token-status').then(r => r.json()).then(data => {
            document.getElementById('tokenStatus').textContent = 
                data.valid ? '✅ Válido' : '❌ Inválido';
        });
    </script>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación del webhook (Meta requiere esto)
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                log("✅ Webhook verificado exitosamente")
                return challenge, 200
            else:
                log("❌ Verificación fallida")
                return "Verification failed", 403
        return "Hello from webhook!", 200
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            log("📨 Webhook recibido")
            
            # Verificar si es un mensaje
            if "entry" in data and data["entry"]:
                entry = data["entry"][0]
                if "changes" in entry and entry["changes"]:
                    value = entry["changes"][0].get("value", {})
                    
                    # Procesar mensajes
                    if "messages" in value and value["messages"]:
                        message = value["messages"][0]
                        
                        # Verificar que sea mensaje de texto
                        if message.get("type") == "text" and "text" in message:
                            from_number = message["from"]
                            message_text = message["text"]["body"]
                            
                            log(f"👤 De: {from_number}")
                            log(f"💬 Mensaje: {message_text}")
                            
                            # Obtener respuesta del bot
                            response_text = get_bot_response(message_text)
                            
                            # Enviar respuesta
                            result = send_whatsapp_message(from_number, response_text)
                            
                            if result["status"] == "success":
                                return jsonify({"status": "ok"}), 200
                            else:
                                return jsonify({"status": "error", "details": result}), 200
            
            return jsonify({"status": "ignored"}), 200
            
        except Exception as e:
            log(f"❌ Error procesando webhook: {str(e)}")
            return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/token-status")
def token_status():
    """Verifica si el token es válido"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        return jsonify({
            "valid": response.status_code == 200,
            "status": response.status_code
        })
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})

@app.route("/test", methods=["GET"])
def test_send():
    """Endpoint de prueba"""
    test_number = "5491151511579"
    test_message = "✅ Este es un mensaje de prueba desde el bot"
    
    log("🧪 Probando envío de mensaje...")
    result = send_whatsapp_message(test_number, test_message)
    
    return jsonify({
        "test": "completed",
        "result": result,
        "number": test_number
    })

if __name__ == "__main__":
    # Mostrar información inicial
    log("=" * 60)
    log("🚀 WhatsApp Bot Iniciado")
    log("=" * 60)
    log(f"📞 Número Sandbox: +1 555 149 2382")
    log(f"🔑 Verify Token: {VERIFY_TOKEN}")
    log(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    log("=" * 60)
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)