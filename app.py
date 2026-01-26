from flask import Flask, request, jsonify
import json
import requests
import os

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQvIVNY1WkaenzL97TBUambpTjEtGx1NDrOUcF6QZB4PRyPSZB7InX4ZCbvZBZBZAZCA8rOpq2PQiHH3Fd4iVk3TBCaNfuSfslfnaNtu7yD0qoKKFjNguZCl4LEt4d0Mi268SYFcfSq503wwzQ4bAsMFBDAZB8QwxyjNQtGZBBdzh0XZAVLFYazSeCbgZAiR0igYi4iqRoUK3xtllUZABk3L91bb4QV7ODCRTw9GzDfbPtuBFhJjdKrSyVacBFWTKRMfmxty1fYB0fDZAsGRRWf9KzBueuvEwZDZD"
PHONE_NUMBER_ID = "1000705633118215"

# ========== RUTAS ==========
@app.route("/")
def home():
    return """
    <h1>✅ WhatsApp Webhook Funcionando</h1>
    <p><strong>Webhook URL:</strong> https://meta-chat-npbx.onrender.com/webhook</p>
    <p><strong>Token:</strong> mi_token_secreto_123</p>
    <p><strong>Estado:</strong> Listo para recibir y responder mensajes</p>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación de Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        print(f"🔍 GET - Mode: {mode}, Token: {token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook VERIFICADO por Meta")
            return challenge, 200
        return "Falla de verificación", 403
    
    elif request.method == "POST":
        # Mensaje entrante de WhatsApp
        data = request.get_json()
        print("=" * 50)
        print("📨 MENSAJE RECIBIDO DE WHATSAPP")
        print("=" * 50)
        
        try:
            # 1. Loguear el JSON completo (para debugging)
            print(json.dumps(data, indent=2))
            
            # 2. Extraer información importante
            entry = data.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})
            
            # Verificar si es un mensaje
            if "messages" in value:
                message = value["messages"][0]
                from_number = message["from"]
                message_id = message["id"]
                
                # Tipo de mensaje
                if message["type"] == "text":
                    message_text = message["text"]["body"]
                    print(f"💬 MENSAJE TEXTO:")
                    print(f"   De: {from_number}")
                    print(f"   ID: {message_id}")
                    print(f"   Texto: {message_text}")
                    
                    # 3. ¡RESPONDER AUTOMÁTICAMENTE!
                    send_whatsapp_reply(from_number, f"✅ Recibí tu mensaje: '{message_text}'")
                    
                else:
                    print(f"📎 MENSAJE DE TIPO: {message['type']}")
                    send_whatsapp_reply(from_number, f"📎 Recibí un mensaje de tipo: {message['type']}")
            
            # 3. Siempre responder OK a Meta
            return jsonify({"status": "ok"}), 200
            
        except Exception as e:
            print(f"⚠️ ERROR procesando mensaje: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return "Método no permitido", 405

# ========== FUNCIÓN PARA ENVIAR RESPUESTAS ==========
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
        
        print(f"📤 ENVIANDO RESPUESTA A {to_number}:")
        print(f"   Texto: {text}")
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        print(f"   Estado: {response.status_code}")
        print(f"   Respuesta Meta: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR enviando mensaje: {e}")
        return None

# ========== INICIAR SERVIDOR ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor Flask iniciado en puerto {port}")
    print(f"🔧 Token: {VERIFY_TOKEN}")
    print(f"📱 Phone Number ID: {PHONE_NUMBER_ID}")
    app.run(host="0.0.0.0", port=port)