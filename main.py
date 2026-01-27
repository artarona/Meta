from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQjsCSZCAdHAhzfIzNoxOkmmZCeJsIfwq1dUZACprtfgfzW5luQ5YPgesCI88pr0DcLgZB7h3SHWWrRZBNsJe5B2xZC53gyVZAw6ZByGYP423Q1PfnBvgDLIEXScE0xndl9bG8oB38NZBmO73MfqCmSv7oprGlwG7YuRq4eoXSTmlugqvO4i7mEQhYa38eXqPRMAlnqXAttszya7KqZCZBt2Bi7FzTVW2fL4BIoeZC9q0xZASud4oq0T2RASCMzWMbWfAoCmbWuZBjRPytSiUBXj1fFJFLbmvIZD"
PHONE_NUMBER_ID = "1000705633118215"

def log(message):
    """Función para logging con flush automático"""
    print(message, flush=True)

def send_whatsapp_reply(to_number, text):
    """Envía un mensaje de respuesta por WhatsApp"""
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
            "type": "text",
            "text": {"body": text}
        }
        
        log("=" * 40)
        log(f"📤 ENVIANDO RESPUESTA A WHATSAPP:")
        log(f"   Para: {to_number}")
        log(f"   Mensaje: {text}")
        log("=" * 40)
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        log(f"   ✅ Estado: {response.status_code}")
        if response.status_code == 200:
            log(f"   📨 Mensaje ID: {result.get('messages', [{}])[0].get('id', 'Desconocido')}")
        else:
            log(f"   ❌ Error: {result}")
            
            # Manejo específico de errores comunes
            if response.status_code == 401:
                log("   ⚠️  TOKEN EXPIRADO - Necesitas generar nuevo token:")
                log("      https://developers.facebook.com/apps/")
                log("      WhatsApp → API Setup → Generate new token")
            elif response.status_code == 400 and '131030' in str(result):
                log("   ⚠️  NÚMERO NO AUTORIZADO - Agrega el número a lista blanca:")
                log("      Meta Developers → WhatsApp → Configuration")
                log("      Busca 'Test Phone Numbers' o 'Allowed Numbers'")
        
        return result
        
    except Exception as e:
        log(f"🔥 ERROR CRÍTICO enviando mensaje: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========== RUTAS ==========
@app.route("/")
def home():
    return """
    <h1>🤖 WhatsApp Bot RESPONDIENDO</h1>
    <p><strong>Estado:</strong> ✅ Bot activo con respuestas automáticas</p>
    <p><strong>Envía "Hola" al +1 555 149 2382</strong></p>
    <p>El bot te responderá automáticamente</p>
    <p><strong>Token actualizado:</strong> ✅ Funcionando</p>
    <p><strong>Última actualización:</strong> 27/01/2026</p>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log(f"🔍 Verificación: mode={mode}, token={token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            log("✅ Webhook verificado por Meta")
            return challenge, 200
        return "Error", 403
    
    elif request.method == "POST":
        log("=" * 60)
        log("📨 ¡NUEVO WEBHOOK RECIBIDO!")
        log("=" * 60)
        
        try:
            data = request.get_json()
            
            # Log detallado para diagnóstico
            log("📊 Datos recibidos (estructura):")
            log(f"   Tiene 'object': {'object' in data}")
            log(f"   Tiene 'entry': {'entry' in data}")
            
            if "entry" in data and data["entry"]:
                log(f"   Entries: {len(data['entry'])}")
                if "changes" in data["entry"][0]:
                    log(f"   Changes: {len(data['entry'][0]['changes'])}")
            
            # VERIFICAR SI HAY MENSAJES
            if "entry" not in data or not data["entry"]:
                log("⚠️  No hay 'entry' en los datos o está vacío")
                return jsonify({"status": "no_entry", "message": "No entry data"}), 200
                
            entry = data["entry"][0]
            
            if "changes" not in entry or not entry["changes"]:
                log("⚠️  No hay 'changes' en entry")
                return jsonify({"status": "no_changes", "message": "No changes data"}), 200
                
            value = entry["changes"][0].get("value", {})
            
            # VERIFICAR SI ES UN MENSAJE O OTRO TIPO DE WEBHOOK
            if "messages" not in value:
                log("ℹ️  Webhook sin 'messages' (puede ser verificación o status)")
                log(f"   Campos disponibles: {list(value.keys())}")
                return jsonify({"status": "no_messages", "type": "other_webhook"}), 200
            
            # EXTRAER INFORMACIÓN DEL MENSAJE
            messages = value["messages"]
            
            if not messages:
                log("⚠️  Lista de mensajes vacía")
                return jsonify({"status": "empty_messages"}), 200
                
            # Verificar estructura del mensaje
            if "from" not in messages[0]:
                log("⚠️  Mensaje sin campo 'from'")
                return jsonify({"status": "no_sender"}), 200
                
            if "text" not in messages[0]:
                log("⚠️  Mensaje sin campo 'text' (puede ser multimedia)")
                return jsonify({"status": "no_text", "type": "media_message"}), 200
            
            from_number = messages[0]["from"]
            message_text = messages[0]["text"]["body"]
            
            log("=" * 60)
            log("📨 ¡NUEVO MENSAJE DE WHATSAPP!")
            log("=" * 60)
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            
            # ========== ¡AQUÍ GENERAMOS LA RESPUESTA! ==========
            response_text = ""
            
            if message_text.lower() in ["hola", "hi", "hello", "holaaaa"]:
                response_text = f"¡Hola! 👋\nGracias por tu mensaje: '{message_text}'\n\nSoy tu bot de WhatsApp funcionando en Render.\n\nEscribe 'ayuda' para ver comandos."
            
            elif message_text.lower() in ["hora", "time", "fecha"]:
                now = datetime.now()
                response_text = f"🕐 Fecha y hora actual:\n{now.strftime('%A, %d de %B de %Y')}\n{now.strftime('%H:%M:%S')}"
            
            elif message_text.lower() in ["ayuda", "help", "comandos"]:
                response_text = "📚 Comandos disponibles:\n• Hola - Saludo\n• Hora - Fecha y hora actual\n• Ayuda - Esta ayuda\n• Cualquier texto - Eco inteligente"
            
            else:
                response_text = f"✅ Mensaje recibido: '{message_text}'\n\nHe procesado tu solicitud correctamente. ¿En qué más puedo ayudarte?\n\n(Escribe 'ayuda' para ver opciones)"
            
            log(f"   🤖 Respuesta generada: {response_text}")
            
            # ========== ¡ENVIAR LA RESPUESTA A WHATSAPP! ==========
            log("   🚀 Enviando respuesta a WhatsApp API...")
            send_whatsapp_reply(from_number, response_text)
            
            log("=" * 60)
            log("✅ Proceso completado - Respuesta enviada")
            log("=" * 60)
            
            return jsonify({"status": "success", "response_sent": True}), 200
            
        except KeyError as e:
            log(f"❌ Error de clave faltante: {e}")
            log("📊 Datos completos recibidos:")
            log(json.dumps(request.get_json(), indent=2))
            return jsonify({"status": "key_error", "error": str(e)}), 200
            
        except Exception as e:
            log(f"❌ Error general: {e}")
            import traceback
            log("🔍 Traceback completo:")
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return "Método no permitido", 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    log("=" * 60)
    log("🚀 WHATSAPP BOT CON RESPUESTAS AUTOMÁTICAS")
    log("=" * 60)
    log(f"📞 Número Sandbox: +1 555 149 2382")
    log(f"🔑 Token: {VERIFY_TOKEN}")
    log(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    log(f"📱 Phone Number ID: {PHONE_NUMBER_ID}")
    log("=" * 60)
    log("✅ Listo para recibir y RESPONDER mensajes")
    log("   Envía 'Hola' al +1 555 149 2382")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)