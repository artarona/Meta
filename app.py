from flask import Flask, request, jsonify
import json
import requests
import os

app = Flask(__name__)

# CONFIGURACIÓN SANDBOX
VERIFY_TOKEN = "mi_token_secreto_123"
ACCESS_TOKEN = "EAAJYsGl5pHgBQnTe6gLSHzfgLZCfOjXKzOOaPgB5fNjTLWa4ZAyRhzAfmLtrrLwUgbw2TJmvb4CNNgW0iwZAivM5wMPIXFaJpkD8syGR1tRIESJZClY9jy8yoNkszbXZAuqmIZCt90mb6ZBmDU5tnj7tNmq4ZBHGKQX3kZBy6PBFJqVuKNMb6phwBEJernQ8EKPQau9c5MXnmZAY6xKRETNTL1CNgwSIgt1yEzYVuZCzEpqbSv1iJcRPcumRGp1huGAVkzXEK09E0YZBOJBCmLPgN6w3Khzzy2XEF9fyIyUZD"  # ← REEMPLAZAR
PHONE_NUMBER_ID = "1000705633118215"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación de Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        print(f"🔍 GET recibido - mode: {mode}, token: {token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado exitosamente!")
            return challenge, 200
        else:
            print("❌ Verificación fallida")
            return "Verificación fallida", 403
    
    if request.method == "POST":
        data = request.get_json()
        print("📨 POST recibido:", json.dumps(data, indent=2))
        
        try:
            # Procesar mensaje entrante
            entry = data["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            
            if "messages" in value:
                message = value["messages"][0]
                from_number = message["from"]
                message_id = message["id"]
                
                if message["type"] == "text":
                    text = message["text"]["body"]
                    print(f"💬 Mensaje de {from_number}: {text}")
                    
                    # Responder automáticamente
                    response_text = f"Recibí tu mensaje: '{text}'"
                    send_whatsapp_message(from_number, response_text)
                
        except Exception as e:
            print(f"⚠️ Error procesando mensaje: {e}")
        
        # Siempre responder OK a Meta
        return jsonify({"status": "ok"}), 200

def send_whatsapp_message(to_number, text):
    """Envía mensaje por WhatsApp API"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
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
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Mensaje enviado a {to_number}: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return None

@app.route("/", methods=["GET"])
def index():
    return """
    <h1>✅ WhatsApp Webhook Funcionando</h1>
    <p>Servidor listo para recibir mensajes de WhatsApp.</p>
    <p>Webhook: <code>/webhook</code></p>
    <p>Verifica en Meta con token: <strong>mi_token_secreto_123</strong></p>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor iniciado en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=True)