from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQkOBQLeYlzhRZA79oJ9uh7eLzajlz5ic29kg5K0mUCV9L7CtiU6EMmaXAZAPD8ktojjtZCOxPH1RggyzpfUNAw3L6NfgQnG2u9sEY4yvVjU4VPl5PzwgyPeZCnjp0e0TZCCCr571UwDRU9wWy1FTbtBLlrnqSxO5uZAZCoMhasxxezJI3brUmuX3mweHlmoonrdOxmnfVM0nuXAkctpd7q0ztyvcZBGPBIGvnLtHwzHkWOZAB7xHd3ZAi6UyxNZALJYwnEENZA9CVzmSvO2kxSfppEcN4dkZD"
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
        
        # Determinar tipo de mensaje para parámetros
        if "hola" in text.lower():
            param1 = "Usuario"
            param2 = "SALUDO"
            param3 = "¡Te damos la bienvenida!"
        elif "hora" in text.lower() or "fecha" in text.lower():
            param1 = "Consulta"
            param2 = "HORA"
            param3 = datetime.now().strftime("%d/%m/%Y %H:%M")
        elif "ayuda" in text.lower():
            param1 = "Ayuda"
            param2 = "HELP"
            param3 = "Comandos disponibles"
        else:
            param1 = f"Usuario {to_number[-4:]}"
            param2 = f"MSG{int(datetime.now().timestamp()) % 1000:03d}"
            param3 = text[:25] + ("..." if len(text) > 25 else "")
        
        payload = {
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
                            {"type": "text", "text": param1},
                            {"type": "text", "text": param2},
                            {"type": "text", "text": param3}
                        ]
                    }
                ]
            }
        }
        
        log("=" * 40)
        log(f"📤 ENVIANDO PLANTILLA:")
        log(f"   Para: {to_number}")
        log(f"   Parámetros: {param1}, {param2}, {param3}")
        log("=" * 40)
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        log(f"   📊 Estado: {response.status_code}")
        if response.status_code == 200:
            log(f"   ✅ Éxito - ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
            # WhatsApp puede normalizar el número
            if 'contacts' in result and result['contacts']:
                actual_waid = result['contacts'][0].get('wa_id', 'N/A')
                log(f"   🔄 WhatsApp normalizó a: {actual_waid}")
        else:
            log(f"   ❌ Error: {result}")
        
        return result
            
    except Exception as e:
        log(f"🔥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


# ========== RUTAS ==========
@app.route("/")
def home():
    return """
    <h1>🤖 WhatsApp Bot RESPONDIENDO (SANDBOX)</h1>
    <p><strong>Estado:</strong> ✅ Bot activo usando plantillas</p>
    <p><strong>Envía cualquier mensaje al +1 555 149 2382</strong></p>
    <p>El bot responderá con plantilla de confirmación</p>
    <p><strong>Modo:</strong> Sandbox (solo plantillas funcionan)</p>
    <p><strong>Plantilla:</strong> jaspers_market_order_confirmation_v1</p>
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
            
            # Log básico
            if "object" in data:
                log(f"   Object: {data['object']}")
            if "entry" in data and data["entry"]:
                log(f"   Entries: {len(data['entry'])}")
            
            # VERIFICAR ESTRUCTURA
            if "entry" not in data or not data["entry"]:
                log("⚠️  No hay 'entry'")
                return jsonify({"status": "no_entry"}), 200
                
            entry = data["entry"][0]
            
            if "changes" not in entry or not entry["changes"]:
                log("⚠️  No hay 'changes'")
                return jsonify({"status": "no_changes"}), 200
                
            value = entry["changes"][0].get("value", {})
            
            # VERIFICAR SI ES MENSAJE
            if "messages" not in value:
                log("ℹ️  Webhook sin 'messages'")
                return jsonify({"status": "no_messages"}), 200
            
            messages = value["messages"]
            
            if not messages:
                log("⚠️  Mensajes vacíos")
                return jsonify({"status": "empty_messages"}), 200
                
            # EXTRAER INFORMACIÓN
            if "from" not in messages[0]:
                log("⚠️  Sin remitente")
                return jsonify({"status": "no_sender"}), 200
                
            if "text" not in messages[0]:
                log("⚠️  Mensaje sin texto")
                return jsonify({"status": "no_text"}), 200
            
            from_number = messages[0]["from"]
            message_text = messages[0]["text"]["body"]
            
            log("=" * 60)
            log("📨 ¡MENSAJE PROCESADO!")
            log("=" * 60)
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            
            # ========== GENERAR RESPUESTA ==========
            response_text = ""
            
            if message_text.lower() in ["hola", "hi", "hello", "holaaaa"]:
                response_text = f"¡Hola! 👋\nGracias por tu mensaje: '{message_text}'"
            
            elif message_text.lower() in ["hora", "time", "fecha"]:
                now = datetime.now()
                response_text = f"🕐 Fecha y hora: {now.strftime('%d/%m/%Y %H:%M:%S')}"
            
            elif message_text.lower() in ["ayuda", "help", "comandos"]:
                response_text = "📚 Comandos: Hola, Hora, Ayuda"
            
            else:
                response_text = f"✅ Mensaje: '{message_text}'"
            
            log(f"   🤖 Respuesta generada: {response_text}")
            
            # ========== ENVIAR RESPUESTA (SOLO PLANTILLA) ==========
            log("   🚀 Enviando plantilla...")
            send_whatsapp_reply(from_number, response_text)
            
            log("=" * 60)
            log("✅ Proceso completado")
            log("=" * 60)
            
            return jsonify({"status": "success", "response_sent": True}), 200
            
        except KeyError as e:
            log(f"❌ Error de clave: {e}")
            return jsonify({"status": "key_error"}), 200
            
        except Exception as e:
            log(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error"}), 500
    
    return "Método no permitido", 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    log("=" * 60)
    log("🚀 WHATSAPP BOT - MODO SANDBOX")
    log("=" * 60)
    log(f"📞 Número Sandbox: +1 555 149 2382")
    log(f"🔑 Token: {VERIFY_TOKEN}")
    log(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    log(f"📱 Phone Number ID: {PHONE_NUMBER_ID}")
    log("=" * 60)
    log("✅ Bot activo - Usando SOLO plantillas")
    log("   Plantilla: jaspers_market_order_confirmation_v1")
    log("   Envía mensaje al +1 555 149 2382")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)