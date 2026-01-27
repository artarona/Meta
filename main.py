# ========== MAIN - CHATBOT INMOBILIARIO ==========
"""
Chatbot de WhatsApp para Inmobiliaria
Buenos Aires / CABA / San Telmo

Autor: Matrix Agent
Versión: 1.0
"""

from flask import Flask, request, jsonify
import json
import os
import requests
from datetime import datetime
import time

# Importar módulos del chatbot
from config import VERIFY_TOKEN, ACCESS_TOKEN, PHONE_NUMBER_ID, CACHE_MAX_SIZE, CACHE_TTL, INMOBILIARIA
from handlers import procesar_mensaje
from states import get_session, cleanup_expired_sessions

app = Flask(__name__)

# ========== CACHE PARA EVITAR DUPLICADOS ==========
processed_messages = {}

def is_message_processed(message_id: str) -> bool:
    """Verifica si un mensaje ya fue procesado"""
    if message_id in processed_messages:
        if time.time() - processed_messages[message_id] < CACHE_TTL:
            return True
        else:
            del processed_messages[message_id]

    if len(processed_messages) > CACHE_MAX_SIZE:
        oldest_ids = sorted(processed_messages.items(), key=lambda x: x[1])[:CACHE_MAX_SIZE//2]
        for msg_id, _ in oldest_ids:
            del processed_messages[msg_id]

    return False

def mark_message_processed(message_id: str):
    """Marca un mensaje como procesado"""
    processed_messages[message_id] = time.time()

def log(message: str):
    """Logging con flush automático"""
    print(message, flush=True)

# ========== ENVÍO DE MENSAJES WHATSAPP ==========
def send_whatsapp_message(to_number: str, text: str) -> dict:
    """
    Envía un mensaje de texto por WhatsApp.

    NOTA: En modo Sandbox solo funcionan plantillas.
    Cuando tengas cuenta Business verificada, puedes enviar texto libre.
    """
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        # ========== OPCIÓN 1: MENSAJE DE TEXTO (Cuenta Business verificada) ==========
        payload_texto = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }

        # ========== OPCIÓN 2: PLANTILLA (Sandbox / No verificado) ==========
        # Descomenta esto si necesitas usar plantilla en sandbox
        """
        payload_template = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "template",
            "template": {
                "name": "tu_plantilla_inmobiliaria",  # Crear en Meta Business
                "language": {"code": "es_AR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": text[:100]}  # Truncar si es muy largo
                        ]
                    }
                ]
            }
        }
        """

        log(f"📤 Enviando mensaje a {to_number}")
        log(f"📝 Contenido: {text[:100]}...")

        response = requests.post(url, json=payload_texto, headers=headers, timeout=30)
        result = response.json()

        if response.status_code == 200:
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Mensaje enviado - ID: {message_id}")
            return {"status": "success", "message_id": message_id}
        else:
            error = result.get('error', {})
            log(f"❌ Error: {error.get('message', 'Unknown error')}")

            # Si falla por sandbox, sugerir usar plantilla
            if error.get('code') == 131030:
                log("💡 Tip: En Sandbox, usa plantillas aprobadas")

            return {"status": "error", "error": error}

    except Exception as e:
        log(f"🔥 Excepción: {str(e)}")
        return {"status": "error", "error": str(e)}

# ========== RUTAS ==========

@app.route("/")
def home():
    """Página principal de estado"""
    return f"""
    <html>
    <head>
        <title>Chatbot Inmobiliario</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .status {{ padding: 20px; border-radius: 10px; margin: 20px 0; }}
            .ok {{ background: #d4edda; color: #155724; }}
            .info {{ background: #cce5ff; color: #004085; }}
            h1 {{ color: #333; }}
            code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>🏠 Chatbot Inmobiliario</h1>
        <div class="status ok">
            <strong>Estado:</strong> ✅ Bot activo
        </div>
        <div class="status info">
            <strong>Inmobiliaria:</strong> {INMOBILIARIA['nombre']}<br>
            <strong>Webhook:</strong> <code>/webhook</code><br>
            <strong>Hora servidor:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        <h3>Endpoints disponibles:</h3>
        <ul>
            <li><code>/webhook</code> - Webhook de WhatsApp</li>
            <li><code>/health</code> - Estado del servicio</li>
            <li><code>/sessions</code> - Ver sesiones activas</li>
            <li><code>/test-flow?phone=NUMERO</code> - Probar flujo</li>
        </ul>
    </body>
    </html>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook principal de WhatsApp"""

    # ========== VERIFICACIÓN (GET) ==========
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            log(f"✅ Webhook verificado")
            return challenge, 200
        else:
            log(f"❌ Verificación fallida - Token: {token}")
            return "Forbidden", 403

    # ========== MENSAJES ENTRANTES (POST) ==========
    if request.method == "POST":
        log("=" * 60)
        log(f"📨 WEBHOOK RECIBIDO - {datetime.now().strftime('%H:%M:%S')}")

        try:
            data = request.get_json()

            # Validar estructura
            if "entry" not in data or not data["entry"]:
                return jsonify({"status": "no_entry"}), 200

            entry = data["entry"][0]
            if "changes" not in entry or not entry["changes"]:
                return jsonify({"status": "no_changes"}), 200

            value = entry["changes"][0].get("value", {})

            # ========== FILTRAR TIPO DE WEBHOOK ==========

            # Notificación de estado (enviado, leído, etc.)
            if "statuses" in value:
                status = value["statuses"][0]
                log(f"📊 Status: {status.get('status')} - Msg: {status.get('id', 'N/A')[:20]}")
                return jsonify({"status": "status_update"}), 200

            # Error
            if "errors" in value:
                log(f"❌ Error webhook: {value['errors']}")
                return jsonify({"status": "error"}), 200

            # Sin mensajes
            if "messages" not in value or not value["messages"]:
                return jsonify({"status": "no_messages"}), 200

            # ========== PROCESAR MENSAJE ==========
            message = value["messages"][0]
            message_id = message.get("id", "unknown")

            # Deduplicación
            if is_message_processed(message_id):
                log(f"🔄 Mensaje duplicado: {message_id[:20]}")
                return jsonify({"status": "duplicate"}), 200

            mark_message_processed(message_id)

            # Extraer datos
            from_number = message.get("from", "")
            message_type = message.get("type", "")

            # Solo procesar mensajes de texto
            if message_type != "text":
                log(f"⚠️ Tipo no soportado: {message_type}")
                # Podrías responder indicando que solo aceptas texto
                send_whatsapp_message(from_number, "Por favor, enviá un mensaje de texto.")
                return jsonify({"status": "unsupported_type"}), 200

            message_text = message.get("text", {}).get("body", "")

            log(f"👤 De: {from_number}")
            log(f"💬 Mensaje: {message_text}")

            # ========== PROCESAR CON EL HANDLER ==========
            respuesta = procesar_mensaje(from_number, message_text)

            log(f"🤖 Respuesta: {respuesta[:100]}...")

            # ========== ENVIAR RESPUESTA ==========
            send_result = send_whatsapp_message(from_number, respuesta)

            log(f"📤 Resultado envío: {send_result.get('status')}")
            log("=" * 60)

            return jsonify({
                "status": "success",
                "message_processed": message_id,
                "response_sent": send_result.get("status") == "success"
            }), 200

        except Exception as e:
            log(f"🔥 Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/health")
def health():
    """Health check endpoint"""
    cleanup_expired_sessions()
    return jsonify({
        "status": "healthy",
        "service": "chatbot-inmobiliario",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(processed_messages)
    })

@app.route("/sessions")
def sessions():
    """Ver sesiones activas (para debug)"""
    from states import get_all_sessions

    all_sessions = get_all_sessions()
    resumen = []

    for phone, session in all_sessions.items():
        resumen.append({
            "phone": phone[-4:],  # Solo últimos 4 dígitos por privacidad
            "estado": session.get("estado"),
            "operacion": session.get("datos", {}).get("operacion"),
            "last_activity": datetime.fromtimestamp(session.get("last_activity", 0)).isoformat()
        })

    return jsonify({
        "total_sessions": len(all_sessions),
        "sessions": resumen
    })

@app.route("/test-flow")
def test_flow():
    """Endpoint para probar el flujo sin WhatsApp"""
    phone = request.args.get("phone", "test_user")
    mensaje = request.args.get("msg", "hola")

    respuesta = procesar_mensaje(phone, mensaje)
    session = get_session(phone)

    return jsonify({
        "input": mensaje,
        "response": respuesta,
        "estado_actual": session.get("estado"),
        "datos": session.get("datos")
    })

@app.route("/clear-cache")
def clear_cache():
    """Limpiar cache de mensajes"""
    global processed_messages
    old_size = len(processed_messages)
    processed_messages.clear()

    return jsonify({
        "status": "cleared",
        "old_size": old_size,
        "new_size": 0
    })

# ========== INICIAR SERVIDOR ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    log("=" * 60)
    log("🏠 CHATBOT INMOBILIARIO - INICIANDO")
    log("=" * 60)
    log(f"📍 Inmobiliaria: {INMOBILIARIA['nombre']}")
    log(f"🌐 Puerto: {port}")
    log(f"📱 Phone ID: {PHONE_NUMBER_ID}")
    log("=" * 60)
    log("Flujo: OPERACIÓN → TIPO → ZONA → AMBIENTES → PRESUPUESTO → URGENCIA → EXTRAS → RESUMEN")
    log("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=False)
