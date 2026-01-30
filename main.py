from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQqTgjqYpHKvrNNJ5OMWF7oXTS55aexccXSIUJnzfmY7VHxnNe9ZBTyJgp23GcU3EjgjNIgNO3kvGLIMyBNFuQ1neG32ZACeWP2EjBprsxZCEPED3GZBvM8VlQLu7vbPNg4SPFfhkJ31ZAUgOkMijxh2TlRUKYk7kie33eS2K4EXUCcap0x1Hr4bwzBxpPDI9bD8ZBidFpjHsRt0ZCmxI5qC1sYcdy5t3BjwABiBPnmvNolDb3X6EJZCPGmpZASwPhyiWkMyQHMjiZA1hXKZADtsIGL7ZCRNT"
PHONE_NUMBER_ID = "1000705633118215"

def log(message):
    """Función para logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} {message}", flush=True)

# ========== BOT SIMPLE ==========
def get_bot_response(text):
    """Responde con un mensaje simple"""
    text_lower = text.lower().strip()
    
    if text_lower in ["hola", "hi", "hello", "hola bot", "inicio", "menu"]:
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
    
    elif text_lower == "3":
        return "Búsqueda por zona disponible pronto."
    
    elif text_lower == "4":
        return "Búsqueda libre disponible pronto."
    
    elif text_lower == "5":
        return "Ver todas las propiedades disponible pronto."
    
    elif text_lower == "6":
        return "Información del sistema disponible pronto."
    
    else:
        return f"Gracias por tu mensaje: '{text}'. Envía 'Hola' para comenzar."

# ========== SEND WHATSAPP MESSAGE ==========


def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de WhatsApp usando texto directo"""
    try:
        # ========== TRANSFORMAR NÚMERO PARA SANDBOX ==========
        # Meta Sandbox requiere un formato específico para números de prueba
        def transform_number(number):
            # Si es el número argentino, usar el formato que Meta espera
            if number == "5491151511579":
                return "54111551511579"  # Formato que Meta usa en sandbox
            return number
        
        transformed_number = transform_number(to_number)
        
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
            "to": transformed_number,  # Usar el número transformado
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        log(f"📤 ENVIANDO MENSAJE DIRECTO")
        log(f"   Número original: {to_number}")
        log(f"   Número transformado: {transformed_number}")
        log(f"💬 MENSAJE: {message_text[:100]}...")
        
        # Enviar la solicitud
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        log(f"📊 STATUS HTTP: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ ✅ ✅ MENSAJE ENVIADO EXITOSAMENTE")
            log(f"📱 ID del mensaje: {message_id}")
            return {
                "status": "success",
                "message_id": message_id,
                "details": "Mensaje de texto directo enviado",
                "numero_original": to_number,
                "numero_usado": transformed_number
            }
        else:
            log(f"❌ ERROR HTTP: {response.status_code}")
            error_text = response.text[:300] if response.text else "Sin respuesta"
            log(f"❌ RESPUESTA: {error_text}")
            
            # Intentar con plantilla hello_world como fallback
            log("🔄 Intentando con plantilla hello_world como fallback...")
            return send_hello_world_template(transformed_number)
            
    except Exception as e:
        log(f"🔥 ERROR INESPERADO: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }




# ========== RUTAS PRINCIPALES ==========

@app.route("/test-numbers", methods=["GET"])
def test_numbers():
    """Prueba diferentes formatos de números"""
    test_numbers_list = [
        "5491151511579",      # Original
        "54111551511579",     # Transformado
        "+5491151511579",     # Con +
        "+54111551511579",    # Transformado con +
    ]
    
    test_message = "🔧 Prueba de formato de número"
    
    results = []
    for number in test_numbers_list:
        log(f"🧪 Probando número: {number}")
        result = send_whatsapp_message(number, test_message)
        results.append({
            "number": number,
            "result": result
        })
    
    return jsonify({
        "test": "numbers_test",
        "results": results
    })




@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 WhatsApp Bot - NUEVA VERSIÓN</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .test-btn { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .test-btn:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <h1>🤖 WhatsApp Bot - NUEVA VERSIÓN</h1>
        
        <div class="status success">
            <strong>✅ ESTADO:</strong> Bot activo y funcionando
        </div>
        
        <p><strong>📞 Número Sandbox:</strong> +1 555 149 2382</p>
        <p><strong>🎯 Modo:</strong> Mensajes directos (sin plantillas complejas)</p>
        <p><strong>🚀 Instrucciones:</strong> Envía "Hola" al número de WhatsApp para comenzar</p>
        
        <h2>🔧 Pruebas</h2>
        <button class="test-btn" onclick="testSend()">Probar envío manual</button>
        <div id="testResult" style="margin-top: 10px;"></div>
        
        <button class="test-btn" onclick="testNumbers()">Probar diferentes formatos de número</button>
        <div id="numbersResult" style="margin-top: 10px;"></div>
        
        <h2>📊 Estado del sistema</h2>
        <div id="tokenStatus" class="status">Verificando token...</div>
        
        <script>
            // Verificar token al cargar
            fetch('/token-status')
                .then(r => r.json())
                .then(data => {
                    const tokenDiv = document.getElementById('tokenStatus');
                    if (data.valid) {
                        tokenDiv.className = 'status success';
                        tokenDiv.innerHTML = '<strong>✅ TOKEN VÁLIDO:</strong> Conectado a Meta API';
                    } else {
                        tokenDiv.className = 'status error';
                        tokenDiv.innerHTML = '<strong>❌ TOKEN INVÁLIDO:</strong> ' + (data.error || 'Error desconocido');
                    }
                });
            
            // Función para probar envío manual
            function testSend() {
                const btn = document.querySelector('.test-btn');
                const resultDiv = document.getElementById('testResult');
                
                btn.disabled = true;
                btn.textContent = 'Enviando...';
                resultDiv.innerHTML = '<div class="status">Enviando prueba...</div>';
                
                fetch('/test')
                    .then(r => r.json())
                    .then(data => {
                        if (data.result.status === 'success') {
                            resultDiv.innerHTML = '<div class="status success">✅ Prueba enviada exitosamente</div>';
                        } else {
                            resultDiv.innerHTML = '<div class="status error">❌ Error en prueba: ' + (data.result.error || 'Error desconocido') + '</div>';
                        }
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="status error">❌ Error de conexión: ' + error + '</div>';
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                    });
            }
        </script>
    </body>
    </html>
    """, 200

function testNumbers() {
    const resultDiv = document.getElementById('numbersResult');
    resultDiv.innerHTML = '<div class="status">Probando formatos de número...</div>';
    
    fetch('/test-numbers')
        .then(r => r.json())
        .then(data => {
            let html = '<h3>Resultados de prueba de números:</h3>';
            data.results.forEach(item => {
                const status = item.result.status === 'success' ? '✅' : '❌';
                html += `<div class="status ${item.result.status}">
                    ${status} Número: ${item.number}<br>
                    Estado: ${item.result.status}<br>
                    ${item.result.details || ''}
                </div>`;
            });
            resultDiv.innerHTML = html;
        })
        .catch(error => {
            resultDiv.innerHTML = '<div class="status error">❌ Error: ' + error + '</div>';
        });
}


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook para recibir mensajes de WhatsApp"""
    if request.method == "GET":
        # Verificación del webhook (Meta requiere esto)
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log("=" * 60)
        log("🔍 SOLICITUD GET AL WEBHOOK (VERIFICACIÓN)")
        log(f"   Mode: {mode}")
        log(f"   Token: {token}")
        log(f"   Challenge: {challenge}")
        
        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                log("✅ ✅ ✅ WEBHOOK VERIFICADO EXITOSAMENTE")
                return challenge, 200
            else:
                log("❌ VERIFICACIÓN FALLIDA - Token incorrecto")
                return "Verification failed", 403
        
        log("ℹ️  Solicitud GET sin parámetros de verificación")
        return "Webhook endpoint", 200
    
    elif request.method == "POST":
        log("=" * 60)
        log("📨 📨 📨 NUEVO WEBHOOK POST RECIBIDO")
        log("=" * 60)
        
        try:
            data = request.get_json()
            
            if not data:
                log("❌ Datos JSON vacíos o inválidos")
                return jsonify({"status": "no_data"}), 200
            
            # Log básico de la estructura
            log(f"📦 Estructura recibida:")
            log(f"   Object: {data.get('object', 'N/A')}")
            
            if "entry" in data and data["entry"]:
                log(f"   Entries: {len(data['entry'])}")
            
            # Verificar que sea un webhook de WhatsApp Business
            if data.get("object") != "whatsapp_business_account":
                log("❌ No es un webhook de WhatsApp Business")
                return jsonify({"status": "not_whatsapp"}), 200
            
            # Procesar las entradas
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Verificar si hay mensajes
                    if "messages" in value:
                        messages = value["messages"]
                        log(f"   📨 Mensajes en webhook: {len(messages)}")
                        
                        for message in messages:
                            # Solo procesar mensajes de texto
                            if message.get("type") == "text":
                                from_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                
                                if from_number and message_text:
                                    log("=" * 40)
                                    log(f"👤 USUARIO: {from_number}")
                                    log(f"💬 TEXTO: {message_text}")
                                    log("=" * 40)
                                    
                                    # Obtener respuesta del bot
                                    response_text = get_bot_response(message_text)
                                    log(f"🤖 RESPUESTA GENERADA ({len(response_text)} caracteres)")
                                    
                                    # Enviar respuesta
                                    result = send_whatsapp_message(from_number, response_text)
                                    
                                    log("=" * 40)
                                    log(f"📊 RESULTADO FINAL: {result.get('status')}")
                                    if result.get('status') == 'success':
                                        log("✅ ✅ ✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
                                    else:
                                        log("❌ PROCESAMIENTO CON ERRORES")
                                    log("=" * 60)
                                    
                                    return jsonify({
                                        "status": "processed",
                                        "user": from_number,
                                        "result": result
                                    }), 200
            
            log("ℹ️  Webhook recibido pero sin mensajes de texto para procesar")
            return jsonify({"status": "no_text_messages"}), 200
            
        except Exception as e:
            log(f"❌ ERROR PROCESANDO WEBHOOK: {str(e)}")
            import traceback
            log(f"🔍 TRAZABILIDAD: {traceback.format_exc()[:500]}")
            return jsonify({"status": "error", "error": str(e)}), 500


def send_hello_world_template(to_number):
    """Envía la plantilla hello_world como fallback"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Transformar número también para plantilla
        def transform_number(number):
            if number == "5491151511579":
                return "54111551511579"
            return number
        
        transformed_number = transform_number(to_number)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"}
            }
        }
        
        log("🔄 ENVIANDO PLANTILLA HELLO_WORLD...")
        log(f"   Número transformado: {transformed_number}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            log("✅ PLANTILLA HELLO_WORLD ENVIADA EXITOSAMENTE")
            return {
                "status": "success",
                "template_used": "hello_world",
                "details": "Plantilla hello_world enviada",
                "numero_usado": transformed_number
            }
        else:
            log(f"❌ ERROR CON PLANTILLA: {response.status_code}")
            error_text = response.text[:300] if response.text else "Sin respuesta"
            log(f"❌ DETALLES: {error_text}")
            return {
                "status": "error",
                "details": response.text,
                "numero_usado": transformed_number
            }
            
    except Exception as e:
        log(f"🔥 ERROR CON PLANTILLA: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }



@app.route("/test", methods=["GET"])
def test_send():
    """Endpoint de prueba manual"""
    log("=" * 60)
    log("🧪 INICIANDO PRUEBA MANUAL")
    log("=" * 60)
    
    test_number = "5491151511579"
    test_message = "✅ ¡Hola! Este es un mensaje de prueba desde la NUEVA versión del bot. El bot ahora funciona con mensajes de texto directos. ¡Prueba enviando 'Hola'!"
    
    result = send_whatsapp_message(test_number, test_message)
    
    log("=" * 60)
    log(f"🧪 RESULTADO DE PRUEBA: {result.get('status')}")
    log("=" * 60)
    
    return jsonify({
        "test": "completed",
        "timestamp": datetime.now().isoformat(),
        "number": test_number,
        "message": test_message,
        "result": result
    })

@app.route("/token-status", methods=["GET"])
def token_status():
    """Verifica si el token es válido"""
    try:
        log("🔍 Verificando token de acceso...")
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Token válido - Nombre: {data.get('verified_name', 'N/A')}")
            return jsonify({
                "valid": True,
                "status": response.status_code,
                "name": data.get('verified_name'),
                "number": data.get('display_phone_number')
            })
        else:
            log(f"❌ Token inválido - Status: {response.status_code}")
            return jsonify({
                "valid": False,
                "status": response.status_code,
                "error": response.text[:200] if response.text else "No response"
            })
    except Exception as e:
        log(f"🔥 Error verificando token: {str(e)}")
        return jsonify({"valid": False, "error": str(e)})

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    return jsonify({
        "status": "healthy",
        "service": "whatsapp-bot",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "mode": "direct_messages"
    })

if __name__ == "__main__":
    # Mostrar información inicial
    print("\n" + "=" * 60)
    print("🚀 🚀 🚀 WHATSAPP BOT - NUEVA VERSIÓN 2.0")
    print("=" * 60)
    print(f"📞 Número Sandbox: +1 555 149 2382")
    print(f"🔑 Verify Token: {VERIFY_TOKEN}")
    print(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    print(f"⚡ Modo: Mensajes de texto directos")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)