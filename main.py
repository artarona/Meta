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
    """Envía un mensaje de respuesta por WhatsApp usando plantilla disponible"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # OPCIÓN 1: Intentar mensaje de texto normal (puede fallar en sandbox)
        payload_text = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": text}
        }
        
        log("=" * 40)
        log(f"📤 INTENTANDO MENSAJE DE TEXTO:")
        log(f"   Para: {to_number}")
        log(f"   Mensaje: {text[:50]}...")
        log("=" * 40)
        
        response = requests.post(url, json=payload_text, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            log(f"   ✅ Estado: {response.status_code}")
            log(f"   📨 Mensaje ID: {result.get('messages', [{}])[0].get('id', 'Desconocido')}")
            return result
        
        # Si falla con error 131030 (número no autorizado), usar plantilla
        result = response.json()
        error_code = str(result.get('error', {}).get('code', ''))
        
        if response.status_code == 400 and '131030' in error_code:
            log(f"   ❌ Error 131030 - Usando plantilla alternativa...")
            
            # OPCIÓN 2: Plantilla que sabemos funciona
            # Esta plantilla existe según tu prueba exitosa
            payload_template = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": "jaspers_market_order_confirmation_v1",
                    "language": {"code": "en_US"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": "Usuario de Bot"},  # Nombre
                                {"type": "text", "text": "BOT-001"},         # ID
                                {"type": "text", "text": datetime.now().strftime("%d/%m/%Y")}  # Fecha
                            ]
                        }
                    ]
                }
            }
            
            log(f"   🔄 Enviando plantilla 'jaspers_market_order_confirmation_v1'...")
            response2 = requests.post(url, json=payload_template, headers=headers)
            result2 = response2.json()
            
            log(f"   📊 Estado plantilla: {response2.status_code}")
            if response2.status_code == 200:
                log(f"   ✅ Plantilla enviada exitosamente")
            else:
                log(f"   ❌ Error plantilla: {result2}")
            
            return result2
        else:
            log(f"   ❌ Error diferente: {result}")
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
    <p>El bot responderá con plantilla (sandbox)</p>
    <p><strong>Token:</strong> ✅ Funcionando</p>
    <p><strong>Plantilla disponible:</strong> jaspers_market_order_confirmation_v1</p>
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
            
            # Log básico de estructura
            if "object" in data:
                log(f"   Object: {data['object']}")
            if "entry" in data and data["entry"]:
                log(f"   Entries recibidas: {len(data['entry'])}")
            
            # VERIFICAR SI HAY MENSAJES
            if "entry" not in data or not data["entry"]:
                log("⚠️  No hay 'entry' en los datos")
                return jsonify({"status": "no_entry"}), 200
                
            entry = data["entry"][0]
            
            if "changes" not in entry or not entry["changes"]:
                log("⚠️  No hay 'changes' en entry")
                return jsonify({"status": "no_changes"}), 200
                
            value = entry["changes"][0].get("value", {})
            
            # VERIFICAR SI ES UN MENSAJE
            if "messages" not in value:
                log("ℹ️  Webhook sin 'messages' (puede ser status)")
                return jsonify({"status": "no_messages"}), 200
            
            messages = value["messages"]
            
            if not messages:
                log("⚠️  Lista de mensajes vacía")
                return jsonify({"status": "empty_messages"}), 200
                
            # Extraer información
            if "from" not in messages[0]:
                log("⚠️  Mensaje sin remitente")
                return jsonify({"status": "no_sender"}), 200
                
            if "text" not in messages[0]:
                log("⚠️  Mensaje sin texto (puede ser multimedia)")
                return jsonify({"status": "no_text"}), 200
            
            from_number = messages[0]["from"]
            message_text = messages[0]["text"]["body"]
            
            log("=" * 60)
            log("📨 ¡NUEVO MENSAJE DE WHATSAPP!")
            log("=" * 60)
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            
            # ========== GENERAR RESPUESTA ==========
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
            
            # ========== ENVIAR RESPUESTA ==========
            log("   🚀 Enviando respuesta a WhatsApp API...")
            send_whatsapp_reply(from_number, response_text)
            
            log("=" * 60)
            log("✅ Proceso completado")
            log("=" * 60)
            
            return jsonify({"status": "success", "response_sent": True}), 200
            
        except KeyError as e:
            log(f"❌ Error de clave: {e}")
            return jsonify({"status": "key_error", "error": str(e)}), 200
            
        except Exception as e:
            log(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error"}), 500
    
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
    log("✅ Bot activo - Usando plantilla para respuestas")
    log("   Envía 'Hola' al +1 555 149 2382")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)