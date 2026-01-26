from flask import Flask, request, jsonify
import json
import os
import sys

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"

def log(message):
    """Función para logging con flush automático"""
    print(message, flush=True)

# ========== RUTAS ==========
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>✅ WhatsApp Webhook Funcionando</title>
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
            .url-box {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #007bff;
                margin: 20px 0;
                font-family: monospace;
                word-break: break-all;
            }
            .status {
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
            .status.active {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">✅ WhatsApp Webhook Funcionando</h1>

            <div class="status active">
                <strong>Estado:</strong> Servidor activo y recibiendo webhooks
            </div>

            <h3>🔗 Configuración en Meta:</h3>
            <div class="url-box">
                <strong>URL de Webhook:</strong><br>
                https://meta-chat-npbx.onrender.com/webhook
            </div>

            <div class="url-box">
                <strong>Token de Verificación:</strong><br>
                mi_token_secreto_123
            </div>

            <h3>📊 Para probar:</h3>
            <ol>
                <li>Envía un mensaje de WhatsApp al número: <strong>+1 555 149 2382</strong></li>
                <li>Revisa los logs en Render para ver el JSON completo</li>
                <li>El servidor responderá automáticamente "✅ OK" a Meta</li>
            </ol>

            <p><em>Última actualización: Servidor listo para producción</em></p>
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
            # 1. Obtener y mostrar JSON completo
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
            
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    field = change.get("field", "")
                    
                    log(f"   Campo: {field}")
                    
                    # 4. Procesar mensajes
                    if "messages" in value:
                        messages = value["messages"]
                        for message in messages:
                            process_message(message, value.get("metadata", {}))
                    
                    # 5. Mostrar metadata
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

def process_message(message, metadata):
    """Procesa un mensaje individual de WhatsApp"""
    msg_type = message.get("type", "desconocido")
    from_number = message.get("from", "desconocido")
    msg_id = message.get("id", "sin-id")
    timestamp = message.get("timestamp", "sin-timestamp")
    
    log(f"   💬 MENSAJE {msg_type.upper()}:")
    log(f"      • De: {from_number}")
    log(f"      • ID: {msg_id}")
    log(f"      • Hora: {timestamp}")
    
    # Procesar según tipo de mensaje
    if msg_type == "text":
        text_body = message.get("text", {}).get("body", "")
        log(f"      • Texto: '{text_body}'")
        
    elif msg_type == "image":
        image = message.get("image", {})
        log(f"      • Imagen ID: {image.get('id')}")
        log(f"      • Caption: {image.get('caption', 'sin caption')}")
        
    elif msg_type == "audio":
        audio = message.get("audio", {})
        log(f"      • Audio ID: {audio.get('id')}")
        
    elif msg_type == "document":
        document = message.get("document", {})
        log(f"      • Documento: {document.get('filename')}")
        log(f"      • Tipo: {document.get('mime_type')}")
        
    elif msg_type == "location":
        location = message.get("location", {})
        log(f"      • Latitud: {location.get('latitude')}")
        log(f"      • Longitud: {location.get('longitude')}")
        
    else:
        log(f"      • Datos: {json.dumps(message, indent=6)[:200]}...")
    
    log(f"      • Metadata: {json.dumps(metadata, indent=6)}")

# ========== INICIAR SERVIDOR ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    log("=" * 60)
    log("🚀 INICIANDO WHATSAPP WEBHOOK SERVER")
    log("=" * 60)
    log(f"   Puerto: {port}")
    log(f"   Token: {VERIFY_TOKEN}")
    log(f"   Webhook: /webhook")
    log(f"   URL: https://meta-chat-npbx.onrender.com")
    log("=" * 60)
    log("   Esperando webhooks de WhatsApp...")
    log("   Envía un mensaje a +1 555 149 2382 para probar")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)