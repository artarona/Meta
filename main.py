from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
# ACCESS_TOKEN = "EAAJYsGl5pHgBQkOBQLeYlzhRZA79oJ9uh7eLzajlz5ic29kg5K0mUCV9L7CtiU6EMmaXAZAPD8ktojjtZCOxPH1RggyzpfUNAw3L6NfgQnG2u9sEY4yvVjU4VPl5PzwgyPeZCnjp0e0TZCCCr571UwDRU9wWy1FTbtBLlrnqSxO5uZAZCoMhasxxezJI3brUmuX3mweHlmoonrdOxmnfVM0nuXAkctpd7q0ztyvcZBGPBIGvnLtHwzHkWOZAB7xHd3ZAi6UyxNZALJYwnEENZA9CVzmSvO2kxSfppEcN4dkZD"
ACCESS_TOKEN = "EAAJYsGl5pHgBQtcI1S7nVzSwpspcQIk4tNGMnq7ZB2PONLbYINTQ3pfXatZAwvqXbxDnKklTelRCrbsjvwFYk1hP9uBOIBquz3wKiQHUH9JhFuCPWX1D6sY8JHrZCaa3yYnOXxXSMRE3cvGPvXh37VaussSlQBXyC5JVqDIsJkkMpeyPmEzQwCE5HR1ZBuReg5MZBk1i1LNUaJtei5HnQVd9S6yIIOgVkWnMPZCWMkedmnFUbZCGFCzpjOiavJNHeOnK6VQzajZCbEX9zgPFdyVXbqYynMWCFoMymCcZD"PHONE_NUMBER_ID = "1000705633118215"

def log(message):
    """Función para logging con flush automático"""
    print(message, flush=True)

def test_token_validity():
    """Testea si el token es válido al iniciar"""
    try:
        log("=" * 60)
        log("🔍 TESTEANDO TOKEN DE ACCESO...")
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ TOKEN VÁLIDO")
            log(f"   Phone ID: {data.get('id')}")
            log(f"   Nombre: {data.get('verified_name', 'N/A')}")
            log(f"   Número: {data.get('display_phone_number', 'N/A')}")
        else:
            error_data = response.json() if response.content else {}
            log(f"❌ ERROR CON TOKEN: Status {response.status_code}")
            log(f"   Detalle: {json.dumps(error_data, indent=2)}")
            
            # Mostrar primeros 50 chars del token para debug
            token_preview = ACCESS_TOKEN[:50] + "..." if len(ACCESS_TOKEN) > 50 else ACCESS_TOKEN
            log(f"   Token usado: {token_preview}")
        
        log("=" * 60)
        return response.status_code == 200
        
    except Exception as e:
        log(f"🔥 ERROR TESTEANDO TOKEN: {e}")
        import traceback
        traceback.print_exc()
        return False





def send_whatsapp_reply(to_number, text):
    """Envía un mensaje de respuesta por WhatsApp usando plantilla"""
    try:
        # ========== TRANSFORMACIÓN DE NÚMERO PARA SANDBOX ==========
        # Meta Sandbox transforma los números automáticamente
        # Original: 5491151511579 → Transformado: 54111551511579
        # Para que la respuesta llegue al número correcto, debemos usar el formato transformado
        
        def transform_number_for_sandbox(original_number):
            """Transforma número para formato sandbox de Meta"""
            if original_number == "5491151511579":
                return "54111551511579"  # Formato transformado que usa Meta
            return original_number
        
        numero_transformado = transform_number_for_sandbox(to_number)
        
        log("=" * 50)
        log("🔄 TRANSFORMACIÓN DE NÚMERO:")
        log(f"   Número recibido: {to_number}")
        log(f"   Número para enviar: {numero_transformado}")
        log("=" * 50)
        
        # ========== CONFIGURACIÓN DE ENVÍO ==========
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # ========== GENERAR PARÁMETROS DINÁMICOS ==========
        hora_actual = datetime.now()
        
        # Determinar tipo de mensaje para personalizar respuesta
        texto_minuscula = text.lower().strip()
        
        if any(palabra in texto_minuscula for palabra in ["hola", "hi", "hello", "buenas"]):
            param1 = "Usuario"
            param2 = "SALUDO_INICIAL"
            param3 = "¡Hola! 👋 Gracias por escribirnos."
            
        elif any(palabra in texto_minuscula for palabra in ["hora", "time", "fecha", "día"]):
            param1 = "Consulta"
            param2 = "INFO_TIEMPO"
            param3 = hora_actual.strftime("%d/%m/%Y %H:%M:%S")
            
        elif any(palabra in texto_minuscula for palabra in ["ayuda", "help", "comandos", "opciones"]):
            param1 = "Asistencia"
            param2 = "MENU_AYUDA"
            param3 = "Comandos: Hola, Hora, Ayuda, Estado"
            
        elif any(palabra in texto_minuscula for palabra in ["estado", "status", "funciona", "test"]):
            param1 = "Verificación"
            param2 = "SISTEMA_OK"
            param3 = "✅ Bot funcionando correctamente"
            
        else:
            # Respuesta genérica para otros mensajes
            param1 = f"Usuario {to_number[-4:]}"
            param2 = f"MSG{hora_actual.timestamp():.0f}[-3:]"
            param3 = text[:30] + ("..." if len(text) > 30 else "")
        
        # ========== CONSTRUIR PAYLOAD ==========
        # Usar la MISMA estructura que probamos y funciona
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero_transformado,  # ¡NÚMERO TRANSFORMADO!
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
        
        # ========== LOGS DETALLADOS ==========
        log("=" * 50)
        log("📤 ENVIANDO RESPUESTA WHATSAPP")
        log("=" * 50)
        log(f"   🔗 URL: {url}")
        log(f"   📱 Destinatario original: {to_number}")
        log(f"   🔄 Destinatario transformado: {numero_transformado}")
        log(f"   💬 Mensaje original: '{text}'")
        log(f"   🏷️  Plantilla: jaspers_market_order_confirmation_v1")
        log(f"   📊 Parámetros:")
        log(f"      1. {param1}")
        log(f"      2. {param2}")
        log(f"      3. {param3}")
        log("=" * 50)
        
        # ========== ENVIAR SOLICITUD ==========
        log("   🚀 Enviando solicitud a Meta API...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        log(f"   📊 Estado HTTP: {response.status_code}")
        
        # ========== MANEJAR RESPUESTA ==========
        if response.status_code == 200:
            # ¡ÉXITO!
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"   ✅ MENSAJE ENVIADO EXITOSAMENTE")
            log(f"   🆔 ID del mensaje: {message_id}")
            
            # Información adicional de WhatsApp
            if 'contacts' in result and result['contacts']:
                contacto = result['contacts'][0]
                waid = contacto.get('wa_id', 'N/A')
                input_waid = contacto.get('input', 'N/A')
                log(f"   👤 Contacto procesado:")
                log(f"      - WA_ID: {waid}")
                log(f"      - Input: {input_waid}")
            
            return {
                "status": "success",
                "message_id": message_id,
                "http_status": response.status_code,
                "details": "Mensaje enviado correctamente",
                "numero_original": to_number,
                "numero_enviado": numero_transformado
            }
            
        else:
            # ERROR
            error_data = result.get('error', {})
            error_code = error_data.get('code', 'N/A')
            error_message = error_data.get('message', 'Error desconocido')
            error_type = error_data.get('type', 'N/A')
            
            log(f"   ❌ ERROR AL ENVIAR MENSAJE")
            log(f"   🔴 Código de error: {error_code}")
            log(f"   🔴 Tipo: {error_type}")
            log(f"   🔴 Mensaje: {error_message}")
            
            # Manejo específico de errores comunes
            if error_code == 131030:
                log(f"   ⚠️  PROBLEMA: Número no autorizado en sandbox")
                log(f"   💡 SOLUCIÓN: Agrega {to_number} a 'Números de prueba' en Meta")
                
            elif error_code == 190 or "expired" in error_message.lower():
                log(f"   ⚠️  PROBLEMA: Token expirado")
                log(f"   💡 SOLUCIÓN: Genera nuevo token en Meta Developers")
                log(f"   🔑 Token actual (inicio): {ACCESS_TOKEN[:30]}...")
                
            elif error_code == 100:
                log(f"   ⚠️  PROBLEMA: Parámetros inválidos")
                log(f"   💡 SOLUCIÓN: Verificar formato del payload")
                
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_message,
                "http_status": response.status_code,
                "details": result
            }
            
    except requests.exceptions.Timeout:
        log("   ⏰ ERROR: Timeout al conectar con Meta API")
        return {
            "status": "error",
            "error": "Timeout",
            "details": "La solicitud tardó demasiado en responder"
        }
        
    except requests.exceptions.ConnectionError:
        log("   🔌 ERROR: Problema de conexión")
        return {
            "status": "error", 
            "error": "ConnectionError",
            "details": "No se pudo conectar con los servidores de Meta"
        }
        
    except Exception as e:
        log(f"   🔥 ERROR INESPERADO: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        log(f"   📝 Traceback: {error_trace[:500]}...")
        
        return {
            "status": "error",
            "error": str(e),
            "details": "Error inesperado en send_whatsapp_reply"
        }



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
    <p><strong>Token status:</strong> <span id="tokenStatus">Verificando...</span></p>
    <script>
        fetch('/token-status').then(r => r.json()).then(data => {
            document.getElementById('tokenStatus').textContent = 
                data.valid ? '✅ Válido' : '❌ Inválido: ' + data.error;
        });
    </script>
    """, 200

@app.route("/token-status")
def token_status():
    """Endpoint para verificar estado del token"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify({"valid": True, "status": response.status_code})
        else:
            return jsonify({
                "valid": False, 
                "status": response.status_code,
                "error": response.json() if response.content else "No response"
            })
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})

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
        log(f"📅 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            data = request.get_json()
            
            # 🔍 DEBUG DETALLADO
            log("🔍 WEBHOOK RAW DATA (primeros 1000 chars):")
            log(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            if len(json.dumps(data)) > 1000:
                log("... [data truncated]")
            
            # Log básico
            if "object" in data:
                log(f"   Object: {data['object']}")
            if "entry" in data and data["entry"]:
                log(f"   Entries: {len(data['entry'])}")
            
            # VERIFICAR ESTRUCTURA
            if "entry" not in data or not data["entry"]:
                log("ℹ️  Webhook sin 'entry' - podría ser notificación de estado")
                return jsonify({"status": "no_entry", "type": "status_notification"}), 200
                
            entry = data["entry"][0]
            
            if "changes" not in entry or not entry["changes"]:
                log("ℹ️  Webhook sin 'changes'")
                return jsonify({"status": "no_changes"}), 200
                
            value = entry["changes"][0].get("value", {})
            
            # DETECTAR TIPO DE WEBHOOK
            webhook_type = "unknown"
            
            if "messages" in value:
                webhook_type = "message"
            elif "statuses" in value:
                webhook_type = "status"
                log(f"📊 Webhook de ESTADO: {value.get('statuses', [{}])[0].get('status', 'unknown')}")
                return jsonify({"status": "message_status", "type": webhook_type}), 200
            elif "errors" in value:
                webhook_type = "error"
                log(f"❌ Webhook de ERROR: {value.get('errors')}")
                return jsonify({"status": "error", "type": webhook_type}), 200
            
            log(f"🔍 Tipo de webhook: {webhook_type}")
            
            # PROCESAR MENSAJES
            if webhook_type != "message":
                log(f"ℹ️  Webhook sin 'messages' (tipo: {webhook_type})")
                return jsonify({"status": f"no_messages_{webhook_type}"}), 200
            
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
                return jsonify({"status": "no_text"})
            
            from_number = messages[0]["from"]
            message_text = messages[0]["text"]["body"]
            message_id = messages[0].get("id", "unknown")
            
            log("=" * 60)
            log("📨 ¡MENSAJE PROCESADO!")
            log("=" * 60)
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            log(f"   🆔 ID Mensaje: {message_id}")
            
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
            send_result = send_whatsapp_reply(from_number, response_text)
            
            log("=" * 60)
            log(f"📊 RESULTADO FINAL:")
            log(f"   Status: {send_result.get('status')}")
            if send_result.get('status') == 'success':
                log(f"   ✅ Mensaje enviado exitosamente")
                log(f"   ID: {send_result.get('message_id')}")
            else:
                log(f"   ❌ Error: {send_result.get('error')}")
            log("=" * 60)
            
            return jsonify({
                "status": "success", 
                "response_sent": send_result.get('status') == 'success',
                "details": send_result
            }), 200
            
        except KeyError as e:
            log(f"❌ Error de clave en webhook: {e}")
            log(f"   Data disponible: {list(data.keys()) if 'data' in locals() else 'no data'}")
            return jsonify({"status": "key_error", "missing_key": str(e)}), 200
            
        except Exception as e:
            log(f"❌ Error general en webhook: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "error": str(e)}), 500
    
    return "Método no permitido", 405

@app.route("/test-send", methods=["GET"])
def test_send():
    """Endpoint para probar envío manual"""
    try:
        test_number = "5491151511579"
        test_message = "Mensaje de prueba desde /test-send"
        
        log("=" * 60)
        log("🧪 PRUEBA MANUAL DESDE /test-send")
        log("=" * 60)
        
        result = send_whatsapp_reply(test_number, test_message)
        
        return jsonify({
            "status": "test_completed",
            "result": result,
            "test_number": test_number,
            "test_message": test_message
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    log("=" * 60)
    log("🚀 WHATSAPP BOT - MODO SANDBOX")
    log("=" * 60)
    log(f"📞 Número Sandbox: +1 555 149 2382")
    log(f"🔑 Verify Token: {VERIFY_TOKEN}")
    log(f"🔑 Access Token (inicio): {ACCESS_TOKEN[:20]}...")
    log(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    log(f"📱 Phone Number ID: {PHONE_NUMBER_ID}")
    log("=" * 60)
    
    # Testear token al inicio
    token_valid = test_token_validity()
    
    if token_valid:
        log("✅ Bot ACTIVO - Token válido")
    else:
        log("⚠️  Bot INICIADO pero token podría tener problemas")
    
    log("   Usando SOLO plantillas")
    log("   Plantilla: jaspers_market_order_confirmation_v1")
    log("   Envía mensaje al +1 555 149 2382")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)