from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQn9BBvVZB4hfFq5SPiUYldPN82k8P1UTZCrC7f1ifZAXIAde4odV6TnfObqyyS84qzJfsvBdkBNtqeAvgLyNXhXZCAjEh7myM684ploZCJDgr5CNpUZCJhMOoIIA4qAgIJ40rthiypz21TrH7aqEZB87zt6rwF7YTo58DqZCp1MWXrXB1yvzXC0R5W7mDtk88ZAx17FunC9Od42ZBIy8qPWdj4Rvn3afOast0zq80PAYmHJAtCGhA0wrniRTxYOf0wJl2fjxIR0gJQi9q4kLJZBUmFJPAZDZD"
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
        log("📨 ¡NUEVO MENSAJE DE WHATSAPP!")
        log("=" * 60)
        
        try:
            data = request.get_json()
            
            # Extraer información del mensaje
            messages = data["entry"][0]["changes"][0]["value"]["messages"]
            from_number = messages[0]["from"]
            message_text = messages[0]["text"]["body"].strip('"')  # Quitar comillas
            
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            
            # ========== ¡AQUÍ GENERAMOS LA RESPUESTA! ==========
            response_text = ""
            
            if message_text.lower() in ["hola", "hi", "hello"]:
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
            
        except Exception as e:
            log(f"❌ Error: {e}")
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
    log("=" * 60)
    log("✅ Listo para recibir y RESPONDER mensajes")
    log("   Envía 'Hola' al +1 555 149 2382")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)