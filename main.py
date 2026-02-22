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
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
# IMPORTANTE: Usar variable de entorno para el token
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "EAAJYsGl5pHgBQ2z1zTX7wPi3TGnWuTuRmkTzml1bVVAjdvZCIFZAddB0FeT8RoPSWlC4U0s6yrfooZCxcwWDxatRkdksmr8LNrUJHxiDZAFJbMqrQscuE6sXjsnRm5VPoPRzRz3E4Yy6JIN2IyTeYoSUx3ADjop0rJTl5YFJJAKSDZCnNACh1W9Fuc98tDhDyLyXH31OyVeHUtnpYYTjvvRVrRz1z9wT5nooYxWVk0ONBXwaJ0Ry0CYeQWZCLqRjoTrRTqhTZBo1AZC2iUm7uN9vqqjKZBagc3gTdbQZDZD")
PHONE_NUMBER_ID = "1000705633118215"

# ========== CACHE MEJORADO PARA DEDUPLICACIÓN ==========
processed_messages = {}
CACHE_MAX_SIZE = 1000
CACHE_TTL = 300

def log(message, force_flush=True):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} ℹ️ {message}", flush=force_flush)

def generate_message_hash(webhook_data):
    try:
        if "messages" in webhook_data and webhook_data["messages"]:
            message = webhook_data["messages"][0]
            message_id = message.get("id", "unknown")
            timestamp = message.get("timestamp", "0")
            from_number = message.get("from", "unknown")
            hash_string = f"msg_{message_id}_{timestamp}_{from_number}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        else:
            return hashlib.md5(str(time.time()).encode()).hexdigest()
    except:
        return hashlib.md5(str(time.time()).encode()).hexdigest()

def is_duplicate_webhook(webhook_data):
    message_hash = generate_message_hash(webhook_data)
    if message_hash in processed_messages:
        if time.time() - processed_messages[message_hash] < CACHE_TTL:
            log(f"🔄 Webhook DUPLICADO detectado")
            return True, message_hash
        else:
            del processed_messages[message_hash]
    return False, message_hash

def mark_webhook_processed(message_hash):
    processed_messages[message_hash] = time.time()

def send_whatsapp_reply(to_number, text):
    """Envía un mensaje de respuesta por WhatsApp usando plantilla"""
    try:
        # TRANSFORMACIÓN DE NÚMERO PARA SANDBOX
        numero_transformado = to_number
        if to_number == "5491151511579":
            numero_transformado = "54111551511579"
            log(f"🔄 Número transformado: {to_number} -> {numero_transformado}")
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Determinar tipo de mensaje
        texto_minuscula = text.lower().strip()
        hora_actual = datetime.now()
        
        if any(p in texto_minuscula for p in ["hola", "hi", "hello", "buenas"]):
            param1 = "Usuario"
            param2 = "SALUDO"
            param3 = "¡Hola! 👋 Gracias por escribir"
        elif any(p in texto_minuscula for p in ["hora", "time", "fecha"]):
            param1 = "Consulta"
            param2 = "HORA"
            param3 = hora_actual.strftime("%d/%m/%Y %H:%M:%S")
        elif any(p in texto_minuscula for p in ["ayuda", "help", "comandos"]):
            param1 = "Asistencia"
            param2 = "AYUDA"
            param3 = "Comandos: Hola, Hora, Ayuda"
        elif "que dia es hoy" in texto_minuscula or "qué día es hoy" in texto_minuscula:
            dias_es = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
                "Sunday": "Domingo"
            }
            nombre_dia_en = hora_actual.strftime("%A")
            nombre_dia_es = dias_es.get(nombre_dia_en, nombre_dia_en)
            param1 = "Consulta"
            param2 = "DIA"
            param3 = f"📅 Hoy es {nombre_dia_es} {hora_actual.strftime('%d/%m/%Y')}"
        else:
            param1 = f"Usuario"
            param2 = "RESPUESTA"
            param3 = text[:30] + ("..." if len(text) > 30 else "")
        
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
        
        log(f"📤 Enviando a {numero_transformado}: '{text}'")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        if response.status_code == 200:
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Mensaje enviado: {message_id}")
            return {"status": "success", "message_id": message_id}
        else:
            error = result.get('error', {})
            log(f"❌ Error {error.get('code')}: {error.get('message')}")
            return {"status": "error", "error": error.get('message')}
            
    except Exception as e:
        log(f"🔥 Error: {e}")
        return {"status": "error", "error": str(e)}

# ========== RUTAS ==========
@app.route("/")
def home():
    token_status = "✅ Configurado" if ACCESS_TOKEN else "❌ No configurado"
    return f"""
    <h1>🤖 WHATSAPP BOT - VERSIÓN CORREGIDA</h1>
    <p><strong>Token:</strong> {token_status}</p>
    <p><strong>Número:</strong> +1 555 149 2382</p>
    <p><a href="/token-status">Verificar token</a></p>
    <p><a href="/debug-token-env">Debug variables</a></p>
    <p><a href="/check-code">Verificar código</a></p>
    """

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación del webhook
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if verify_token == VERIFY_TOKEN:
            return challenge, 200
        return "Token de verificación incorrecto", 403
    
    # POST - Recibir mensajes
    try:
        data = request.get_json()
        log("📨 Webhook recibido")
        
        # Verificar duplicados
        is_dup, msg_hash = is_duplicate_webhook(data)
        if is_dup:
            return jsonify({"status": "duplicate"}), 200
        
        mark_webhook_processed(msg_hash)
        
        # Procesar mensaje
        if "entry" in data and data["entry"]:
            entry = data["entry"][0]
            if "changes" in entry and entry["changes"]:
                value = entry["changes"][0].get("value", {})
                
                if "messages" in value and value["messages"]:
                    message = value["messages"][0]
                    from_number = message.get("from")
                    text = message.get("text", {}).get("body", "")
                    
                    log(f"👤 Usuario: {from_number}, Texto: {text}")
                    
                    # Enviar respuesta
                    result = send_whatsapp_reply(from_number, text)
                    log(f"📊 Resultado: {result.get('status')}")
                    
                    return jsonify({
                        "status": "processed",
                        "user": from_number,
                        "result": result
                    }), 200
        
        return jsonify({"status": "no_message"}), 200
        
    except Exception as e:
        log(f"❌ Error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/token-status")
def token_status():
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

@app.route("/debug-token-env")
def debug_token_env():
    token_from_env = os.environ.get("WHATSAPP_TOKEN", "NO_ENV_VAR")
    return jsonify({
        "env_var_exists": "WHATSAPP_TOKEN" in os.environ,
        "token_from_env_preview": token_from_env[:20] + "..." if len(token_from_env) > 20 else token_from_env,
        "token_from_code_preview": ACCESS_TOKEN[:20] + "...",
        "tokens_match": token_from_env == ACCESS_TOKEN if token_from_env != "NO_ENV_VAR" else False
    })

@app.route("/check-code")
def check_code():
    return "✅ CÓDIGO CORRECTO - Versión actualizada feb 22"

@app.route("/test-send")
def test_send():
    result = send_whatsapp_reply("5491151511579", "test desde browser")
    return jsonify(result)

if __name__ == "__main__":
    log("🚀 INICIANDO BOT - VERSIÓN CORREGIDA")
    log(f"📱 Phone ID: {PHONE_NUMBER_ID}")
    log(f"🔑 Token desde env: {'✅ Configurado' if 'WHATSAPP_TOKEN' in os.environ else '❌ Usando default'}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)