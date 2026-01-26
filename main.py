from flask import Flask, request, jsonify
import json
import os
import sys
import requests  # ← IMPORTANTE: Para enviar respuestas a WhatsApp

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQvIVNY1WkaenzL97TBUambpTjEtGx1NDrOUcF6QZB4PRyPSZB7InX4ZCbvZBZBZAZCA8rOpq2PQiHH3Fd4iVk3TBCaNfuSfslfnaNtu7yD0qoKKFjNguZCl4LEt4d0Mi268SYFcfSq503wwzQ4bAsMFBDAZB8QwxyjNQtGZBBdzh0XZAVLFYazSeCbgZAiR0igYi4iqRoUK3xtllUZABk3L91bb4QV7ODCRTw9GzDfbPtuBFhJjdKrSyVacBFWTKRMfmxty1fYB0fDZAsGRRWf9KzBueuvEwZDZD"
PHONE_NUMBER_ID = "1000705633118215"

def log(message):
    """Función para logging con flush automático"""
    print(message, flush=True)

def send_whatsapp_message(to_number, text):
    """Envía un mensaje de WhatsApp usando la API de Meta"""
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
        
        log(f"📤 ENVIANDO RESPUESTA A {to_number}:")
        log(f"   Texto: {text}")
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        log(f"   Estado: {response.status_code}")
        log(f"   Respuesta Meta: {json.dumps(result, indent=4)}")
        
        return result
        
    except Exception as e:
        log(f"❌ ERROR enviando mensaje: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========== RUTAS ==========
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>✅ WhatsApp Bot con Respuestas Automáticas</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .success {
                color: #28a745;
                font-size: 24px;
            }
            .feature {
                background: #e7f3ff;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                border-left: 4px solid #007bff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">🤖 WhatsApp Bot con Respuestas Automáticas</h1>
            
            <div class="feature">
                <strong>✨ NUEVA FUNCIÓN ACTIVADA:</strong> Ahora el bot RESPONDE automáticamente
            </div>
            
            <h3>🔗 Configuración:</h3>
            <ul>
                <li><strong>URL Webhook:</strong> https://meta-chat-npbx.onrender.com/webhook</li>
                <li><strong>Token:</strong> mi_token_secreto_123</li>
                <li><strong>Número Sandbox:</strong> +1 555 149 2382</li>
            </ul>
            
            <h3>🎯 Para probar:</h3>
            <ol>
                <li>Envía un WhatsApp al <strong>+1 555 149 2382</strong></li>
                <li>El bot te responderá automáticamente</li>
                <li>Revisa los logs para ver el proceso completo</li>
            </ol>
            
            <h3>💬 Comandos disponibles:</h3>
            <ul>
                <li>"hola" → Saludo personalizado</li>
                <li>"hora" → Hora actual</li>
                <li>"ayuda" → Muestra comandos</li>
                <li>Cualquier otro texto → Eco del mensaje</li>
            </ul>
            
            <p><em>✅ Bot activo y respondiendo desde: Render + Meta WhatsApp API</em></p>
        </div>
    </body>
    </html>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Endpoint principal para webhooks de WhatsApp"""
    
    # ========== GET: VERIFICACIÓN DE META ==========
    if request.method == "GET":
        log("=" * 60)
        log("🔍 SOLICITUD GET DE META (Verificación)")
        log("=" * 60)
        
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log(f"   Parámetros recibidos:")
        log(f"   • hub.mode: {mode}")
        log(f"   • hub.verify_token: {token}")
        log(f"   • hub.challenge: {challenge}")
        log(f"   • Token esperado: {VERIFY_TOKEN}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            log("   ✅ VERIFICACIÓN EXITOSA - Devolviendo challenge")
            log("=" * 60)
            return challenge, 200
        else:
            log("   ❌ FALLA DE VERIFICACIÓN")
            log("=" * 60)
            return "Falla de verificación", 403
    
    # ========== POST: MENSAJE DE WHATSAPP ==========
    elif request.method == "POST":
        log("=" * 60)
        log("📨 ¡MENSAJE RECIBIDO DE WHATSAPP!")
        log("=" * 60)
        
        try:
            # 1. Obtener JSON del mensaje
            data = request.get_json()
            log("📊 JSON COMPLETO RECIBIDO:")
            log(json.dumps(data, indent=2))
            log("-" * 40)
            
            # 2. Verificar estructura básica
            if data.get("object") != "whatsapp_business_account":
                log("⚠️  Estructura JSON inesperada")
                return jsonify({"status": "error", "message": "Estructura inválida"}), 400
            
            # 3. Extraer información importante
            entries = data.get("entry", [])
            if not entries:
                log("⚠️  No hay 'entry' en el JSON")
                return jsonify({"status": "ok"}), 200
            
            # Variable para almacenar respuesta
            response_sent = False
            
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    field = change.get("field", "")
                    
                    log(f"   Campo: {field}")
                    
                    # 4. Procesar mensajes y RESPONDER
                    if "messages" in value:
                        messages = value["messages"]
                        for message in messages:
                            from_number = message.get("from", "")
                            msg_type = message.get("type", "")
                            
                            if msg_type == "text":
                                text_body = message.get("text", {}).get("body", "").lower()
                                log(f"   💬 MENSAJE TEXTO DE {from_number}: '{text_body}'")
                                
                                # 5. ¡GENERAR Y ENVIAR RESPUESTA AUTOMÁTICA!
                                response_text = generate_response(text_body, from_number)
                                
                                # Enviar respuesta a WhatsApp
                                send_whatsapp_message(from_number, response_text)
                                response_sent = True
                                log(f"   ✅ RESPUESTA ENVIADA: '{response_text}'")
                    
                    # 6. Mostrar metadata
                    metadata = value.get("metadata", {})
                    if metadata:
                        log(f"   📱 Metadata:")
                        log(f"      • Número: {metadata.get('display_phone_number')}")
                        log(f"      • Phone ID: {metadata.get('phone_number_id')}")
            
            log("=" * 60)
            log("✅ Respondiendo OK a Meta")
            log("=" * 60)
            
            return jsonify({
                "status": "ok",
                "message": "Webhook procesado correctamente",
                "response_sent": response_sent,
                "timestamp": os.times().elapsed
            }), 200
            
        except Exception as e:
            log("=" * 60)
            log(f"❌ ERROR PROCESANDO WEBHOOK: {e}")
            log("=" * 60)
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": os.times().elapsed
            }), 500
    
    # ========== MÉTODO NO PERMITIDO ==========
    else:
        return "Método no permitido", 405

def generate_response(user_message, from_number):
    """Genera una respuesta automática basada en el mensaje recibido"""
    user_message = user_message.lower().strip()
    
    # Respuestas inteligentes
    if user_message in ["hola", "hi", "hello", "buenas"]:
        return f"¡Hola! 👋 Soy tu bot de WhatsApp. Me escribiste: '{user_message}'"
    
    elif user_message in ["hora", "time", "fecha"]:
        from datetime import datetime
        now = datetime.now()
        return f"🕐 Son las {now.strftime('%H:%M:%S')} del {now.strftime('%d/%m/%Y')}"
    
    elif user_message in ["ayuda", "help", "comandos"]:
        return "ℹ️ Comandos disponibles:\n• hola - Saludo\n• hora - Hora actual\n• ayuda - Esta ayuda\n• Cualquier texto - Eco"
    
    elif "gracias" in user_message:
        return "¡De nada! 😊 ¿En qué más puedo ayudarte?"
    
    else:
        # Respuesta por defecto: eco del mensaje
        return f"✅ Recibí tu mensaje: '{user_message}'\n\nEscribe 'ayuda' para ver comandos disponibles."

# ========== INICIAR SERVIDOR ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    log("=" * 60)
    log("🚀 INICIANDO WHATSAPP BOT CON RESPUESTAS AUTOMÁTICAS")
    log("=" * 60)
    log(f"   Puerto: {port}")
    log(f"   Token: {VERIFY_TOKEN}")
    log(f"   Webhook: /webhook")
    log(f"   URL: https://meta-chat-npbx.onrender.com")
    log(f"   Phone Number ID: {PHONE_NUMBER_ID}")
    log("=" * 60)
    log("   🤖 Bot listo para recibir y RESPONDER mensajes")
    log("   Envía un WhatsApp a +1 555 149 2382 para probar")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)