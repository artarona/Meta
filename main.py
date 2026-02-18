from flask import Flask, request, jsonify
import json
import os
import sys
import requests
from datetime import datetime
import time
import hashlib

app = Flask(__name__)

# ========== FORZAR MOSTRAR TODOS LOS LOGS ==========
# Configurar para que todos los logs se muestren inmediatamente
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQ2OIWthlnxb9C5ntxXYiOaq8mOhVZCbLPyJop6jB0iJFmEf0QoBm6iiaiNfZCaB0MZBs0FvwOESdPgYZAgjBRkyH1jWJgTVoMEoBHLpq1GawfpD4Lgp90ZCShDlJgjiYgPnVZB18TClpzWu134esp1SXk08TeHVZAOg9QfS7wXPsKLSEXIeTIkO9ODlAXWJ0TZB0gAYOQZBey04UPmbSEKNumg0halHQQepac5tpCPD0fBqVKMsunh6ed4wo0aHZCComBruYBEhkuhEZCM2BSQd8X7awgZDZD"
PHONE_NUMBER_ID = "1000705633118215"

# ========== CACHE MEJORADO PARA DEDUPLICACIÓN ==========
processed_messages = {}  # {message_hash: timestamp}
CACHE_MAX_SIZE = 1000
CACHE_TTL = 300  # 5 minutos en segundos

def log(message, force_flush=True):
    """Función para logging con flush automático"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} {message}", flush=force_flush)

def show_banner():
    """Muestra el banner inicial del bot"""
    log("=" * 60)
    log("🚀 WHATSAPP BOT - MODO SANDBOX CON DEDUPLICACIÓN MEJORADA")
    log("=" * 60)
    log(f"📞 Número Sandbox: +1 555 149 2382")
    log(f"🔑 Verify Token: {VERIFY_TOKEN}")
    log(f"🔑 Access Token (inicio): {ACCESS_TOKEN[:20]}...")
    log(f"🌐 URL: https://meta-chat-npbx.onrender.com")
    log(f"📱 Phone Number ID: {PHONE_NUMBER_ID}")
    log("=" * 60)

def generate_message_hash(webhook_data):
    """
    Genera un hash único para cualquier tipo de webhook
    """
    try:
        # Para webhooks de mensaje
        if "messages" in webhook_data and webhook_data["messages"]:
            message = webhook_data["messages"][0]
            message_id = message.get("id", "unknown")
            timestamp = message.get("timestamp", "0")
            from_number = message.get("from", "unknown")
            
            hash_string = f"msg_{message_id}_{timestamp}_{from_number}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        
        # Para webhooks de estado
        elif "statuses" in webhook_data and webhook_data["statuses"]:
            status = webhook_data["statuses"][0]
            status_id = status.get("id", "unknown")
            status_type = status.get("status", "unknown")
            timestamp = status.get("timestamp", "0")
            
            hash_string = f"status_{status_id}_{status_type}_{timestamp}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        
        # Para webhooks de error
        elif "errors" in webhook_data:
            hash_string = f"error_{time.time()}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        
        else:
            return hashlib.md5(str(webhook_data).encode()).hexdigest()
            
    except Exception as e:
        return hashlib.md5(str(time.time()).encode()).hexdigest()

def is_duplicate_webhook(webhook_data):
    """Verifica si un webhook ya fue procesado"""
    message_hash = generate_message_hash(webhook_data)
    
    if message_hash in processed_messages:
        if time.time() - processed_messages[message_hash] < CACHE_TTL:
            log(f"   🔄 Webhook DUPLICADO detectado (hash: {message_hash[:8]}...)")
            return True, message_hash
        else:
            del processed_messages[message_hash]
    
    # Limpiar cache si es muy grande
    if len(processed_messages) > CACHE_MAX_SIZE:
        clean_old_cache()
    
    return False, message_hash

def mark_webhook_processed(message_hash):
    """Marca un webhook como procesado"""
    processed_messages[message_hash] = time.time()

def clean_old_cache():
    """Limpia entradas antiguas del cache"""
    current_time = time.time()
    old_entries = 0
    
    keys_to_delete = []
    for msg_hash, timestamp in processed_messages.items():
        if current_time - timestamp > CACHE_TTL:
            keys_to_delete.append(msg_hash)
            old_entries += 1
    
    for key in keys_to_delete:
        del processed_messages[key]
    
    if old_entries > 0:
        log(f"   🧹 Cache limpiado: {old_entries} entradas antiguas removidas")

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
            
        
        # Pruebas introducidas    

        elif any(palabra in texto_minuscula for palabra in [
            "qué día es hoy",
            "que dia es hoy",
            "dia de hoy",
            "día de hoy",
            "dia actual",
            "día actual",
            "hoy que dia",
            "que fecha es hoy",
            "que dia es",
            "qué dia es"
        ]):
            # Obtener fecha actual
            hoy = datetime.now()

            # Día en inglés
            nombre_dia_en = hoy.strftime("%A")

            # Mapeo a español
            dias_es = {
                "Monday": "Lunes",
                "Tuesday": "Martes",
                "Wednesday": "Miércoles",
                "Thursday": "Jueves",
                "Friday": "Viernes",
                "Saturday": "Sábado",
                "Sunday": "Domingo"
            }

            nombre_dia_es = dias_es.get(nombre_dia_en, nombre_dia_en)

            # Formato final
            fecha_formateada = hoy.strftime("%d/%m/%Y")

            param1 = "Consulta"
            param2 = "DIA_HOY"
            param3 = f"📅 Hoy es {nombre_dia_es} {fecha_formateada}"
                    
                
        # end Pruebas introducidas 
        
        else:
            # Respuesta genérica para otros mensajes
            param1 = f"Usuario {to_number[-4:]}"
            param2 = f"MSG{int(hora_actual.timestamp()) % 1000:03d}"
            param3 = text[:30] + ("..." if len(text) > 30 else "")
        
        # ========== CONSTRUIR PAYLOAD ==========
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero_transformado,
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
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"   ✅ MENSAJE ENVIADO EXITOSAMENTE")
            log(f"   🆔 ID del mensaje: {message_id}")
            
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
            error_data = result.get('error', {})
            error_code = error_data.get('code', 'N/A')
            error_message = error_data.get('message', 'Error desconocido')
            error_type = error_data.get('type', 'N/A')
            
            log(f"   ❌ ERROR AL ENVIAR MENSAJE")
            log(f"   🔴 Código de error: {error_code}")
            log(f"   🔴 Tipo: {error_type}")
            log(f"   🔴 Mensaje: {error_message}")
            
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

# ========== RUTAS PRINCIPALES ==========
@app.route("/")
def home():
    return """
    <h1>🤖 WhatsApp Bot RESPONDIENDO (SANDBOX)</h1>
    <p><strong>Estado:</strong> ✅ Bot activo usando plantillas</p>
    <p><strong>Envía cualquier mensaje al +1 555 149 2382</strong></p>
    <p>El bot responderá con plantilla de confirmación</p>
    <p><strong>Modo:</strong> Sandbox (solo plantillas funcionan)</p>
    <p><strong>Plantilla:</strong> jaspers_market_order_confirmation_v1</p>
    <p><strong>Sistema de deduplicación:</strong> ACTIVADO ✅</p>
    <p><strong>Token status:</strong> <span id="tokenStatus">Verificando...</span></p>
    <p><a href="/cache-info">Ver estado de cache</a> | <a href="/clear-cache">Limpiar cache</a></p>
    <script>
        fetch('/token-status').then(r => r.json()).then(data => {
            document.getElementById('tokenStatus').textContent = 
                data.valid ? '✅ Válido' : '❌ Inválido: ' + data.error;
        });
    </script>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
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
                log("ℹ️  Webhook sin 'entry'")
                return jsonify({"status": "no_entry", "type": "status_notification"}), 200
                
            entry = data["entry"][0]
            
            if "changes" not in entry or not entry["changes"]:
                log("ℹ️  Webhook sin 'changes'")
                return jsonify({"status": "no_changes"}), 200
                
            value = entry["changes"][0].get("value", {})
            
            # 🔥 ¡DEDUPLICACIÓN ANTES DE PROCESAR! 🔥
            webhook_hash_data = {
                "entry_id": entry.get("id", "unknown"),
                "value": value
            }
            
            is_duplicate, webhook_hash = is_duplicate_webhook(webhook_hash_data)
            
            if is_duplicate:
                log("🔄 Webhook DUPLICADO - Ignorando procesamiento")
                log(f"   Hash: {webhook_hash[:16]}...")
                log(f"   Cache size: {len(processed_messages)}")
                return jsonify({
                    "status": "duplicate", 
                    "hash": webhook_hash,
                    "cache_size": len(processed_messages)
                }), 200
            
            # Marcar como procesado ANTES de continuar
            mark_webhook_processed(webhook_hash)
            log(f"   ✅ Webhook marcado como procesado (hash: {webhook_hash[:16]}...)")
            
            # DETECTAR TIPO DE WEBHOOK
            webhook_type = "unknown"
            
            if "messages" in value:
                webhook_type = "message"
            elif "statuses" in value:
                webhook_type = "status"
                status_info = value.get('statuses', [{}])[0]
                log(f"📊 Webhook de ESTADO: {status_info.get('status', 'unknown')}")
                log(f"   ID: {status_info.get('id', 'N/A')}")
                log(f"   Recipient: {status_info.get('recipient_id', 'N/A')}")
                
                return jsonify({
                    "status": "message_status", 
                    "type": webhook_type,
                    "message_status": status_info.get('status'),
                    "hash": webhook_hash
                }), 200
                
            elif "errors" in value:
                webhook_type = "error"
                error_info = value.get('errors', [{}])[0]
                log(f"❌ Webhook de ERROR: {error_info.get('message', 'unknown')}")
                return jsonify({"status": "error", "type": webhook_type}), 200
            
            log(f"🔍 Tipo de webhook: {webhook_type}")
            
            # PROCESAR SOLO MENSAJES
            if webhook_type != "message":
                log(f"ℹ️  Webhook de tipo '{webhook_type}' - ignorando")
                return jsonify({"status": f"non_message_{webhook_type}"}), 200
            
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
            message_id = messages[0].get("id", "unknown")
            
            log("=" * 60)
            log("📨 ¡MENSAJE PROCESADO! (NUEVO)")
            log("=" * 60)
            log(f"   👤 De: {from_number}")
            log(f"   💬 Texto: {message_text}")
            log(f"   🆔 ID Mensaje: {message_id}")
            log(f"   🗂️  Cache: {len(processed_messages)} mensajes procesados")
            
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
            log(f"   🔑 Webhook Hash: {webhook_hash[:16]}...")
            log("=" * 60)
            
            return jsonify({
                "status": "success", 
                "response_sent": send_result.get('status') == 'success',
                "details": send_result,
                "message_id": message_id,
                "webhook_hash": webhook_hash,
                "cache_size": len(processed_messages)
            }), 200
            
        except KeyError as e:
            log(f"❌ Error de clave en webhook: {e}")
            return jsonify({"status": "key_error", "missing_key": str(e)}), 200
            
        except Exception as e:
            log(f"❌ Error general en webhook: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "error": str(e)}), 500
    
    return "Método no permitido", 405

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

@app.route("/clear-cache", methods=["GET"])
def clear_cache():
    """Limpia la cache de mensajes procesados"""
    global processed_messages
    old_size = len(processed_messages)
    processed_messages.clear()
    
    return jsonify({
        "status": "cache_cleared",
        "old_size": old_size,
        "new_size": len(processed_messages),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/cache-info", methods=["GET"])
def cache_info():
    """Muestra información de la cache"""
    cache_size = len(processed_messages)
    now = time.time()
    
    recent_messages = 0
    oldest_timestamp = None
    newest_timestamp = None
    
    if processed_messages:
        timestamps = list(processed_messages.values())
        oldest_timestamp = min(timestamps)
        newest_timestamp = max(timestamps)
        
        for timestamp in timestamps:
            if now - timestamp < 60:
                recent_messages += 1
    
    return jsonify({
        "cache_size": cache_size,
        "max_size": CACHE_MAX_SIZE,
        "ttl_seconds": CACHE_TTL,
        "recent_messages_last_minute": recent_messages,
        "oldest_timestamp": oldest_timestamp,
        "newest_timestamp": newest_timestamp,
        "current_time": now
    })

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

@app.route("/debug-code", methods=["GET"])
def debug_code():
    """Endpoint para verificar qué código está ejecutando"""
    import inspect
    
    source = inspect.getsource(send_whatsapp_reply)
    
    verificaciones = {
        "Tiene transform_number_for_sandbox": "transform_number_for_sandbox" in source,
        "Usa numero_transformado": '"to": numero_transformado' in source,
        "Tiene logs de transformación": "TRANSFORMACIÓN DE NÚMERO" in source,
        "Token empieza correcto": ACCESS_TOKEN.startswith("EAAJYsGl5pHgBQtcI1S7nVzSw"),
        "Función completa": len(source) > 1000
    }
    
    resultado = "<h1>🔍 DEBUG CÓDIGO EN RENDER</h1>"
    resultado += "<h3>Verificaciones:</h3><ul>"
    
    for check, value in verificaciones.items():
        color = "green" if value else "red"
        icon = "✅" if value else "❌"
        resultado += f"<li style='color:{color}'>{icon} {check}: {value}</li>"
    
    resultado += "</ul>"
    resultado += "<h3>Primeros 500 chars de la función:</h3>"
    resultado += f"<pre>{source[:500]}...</pre>"
    
    resultado += f"<h3>Token (primeros 50):</h3><pre>{ACCESS_TOKEN[:50]}...</pre>"
    resultado += f"<h3>Longitud función:</h3><pre>{len(source)} caracteres</pre>"
    
    return resultado

@app.route("/check-code", methods=["GET"])
def check_code():
    """Verificar EXACTAMENTE qué código se ejecuta"""
    
    import inspect
    source = inspect.getsource(send_whatsapp_reply)
    
    checks = {
        "1. Tiene transform_number_for_sandbox": "transform_number_for_sandbox" in source,
        "2. Usa numero_transformado en 'to'": '"to": numero_transformado' in source,
        "3. Muestra 'TRANSFORMACIÓN DE NÚMERO' en logs": "TRANSFORMACIÓN DE NÚMERO" in source,
        "4. Token empieza con 'EAAJYsGl5pHgBQtcI1S7nVzSw'": ACCESS_TOKEN.startswith("EAAJYsGl5pHgBQtcI1S7nVzSw"),
        "5. Función es larga (>1500 chars)": len(source) > 1500
    }
    
    html = "<h1>🔍 CHECK CÓDIGO EN RENDER</h1>"
    html += f"<p><strong>Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
    
    html += "<h3>✅ VERIFICACIONES:</h3><ul>"
    for check_name, check_result in checks.items():
        color = "green" if check_result else "red"
        icon = "✅" if check_result else "❌"
        html += f"<li style='color:{color}'>{icon} {check_name}: {check_result}</li>"
    html += "</ul>"
    
    html += "<h4>Primeros 300 caracteres:</h4>"
    html += f"<pre>{source[:300]}</pre>"
    
    html += "<h4>¿Contiene '54111551511579'?</h4>"
    html += f"<pre>{'54111551511579' in source}</pre>"
    
    html += "<h4>¿Contiene 'numero_transformado'?</h4>"
    html += f"<pre>{'numero_transformado' in source}</pre>"
    
    html += "<h3>🎯 CONCLUSIÓN:</h3>"
    if all(checks.values()):
        html += "<p style='color:green; font-weight:bold'>✅ CÓDIGO CORRECTO - Debería funcionar</p>"
    else:
        html += "<p style='color:red; font-weight:bold'>❌ CÓDIGO INCORRECTO - Render tiene versión vieja</p>"
    
    return html

@app.route("/health", methods=["GET"])
def health_check():
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        status = "healthy" if response.status_code == 200 else "unhealthy"
        
        return jsonify({
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "http_code": response.status_code,
            "service": "whatsapp-bot"
        })
    except:
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    # Mostrar banner inmediatamente
    show_banner()
    
    port = int(os.environ.get("PORT", 10000))
    
    # Testear token al inicio
    token_valid = test_token_validity()
    
    if token_valid:
        log("✅ Bot ACTIVO - Token válido")
    else:
        log("⚠️  Bot INICIADO pero token podría tener problemas")
    
    log("   Usando SOLO plantillas")
    log("   Plantilla: jaspers_market_order_confirmation_v1")
    log("   Sistema de deduplicación: ACTIVADO")
    log("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)
