from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

VERIFY_TOKEN = "mi_token_secreto_123"

@app.route("/")
def home():
    return """
    <h1>✅ WhatsApp Webhook Funcionando</h1>
    <p><strong>Webhook URL:</strong> https://meta-chat-npbx.onrender.com/webhook</p>
    <p><strong>Verify Token:</strong> <code>mi_token_secreto_123</code></p>
    <p><em>Nota: Solo recibe mensajes por ahora. Para enviar respuestas, añade 'requests' a requirements.txt</em></p>
    """, 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("🔔 Webhook accedido")
    
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        print(f"   Mode: {mode}, Token: {token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ VERIFICACIÓN EXITOSA")
            return challenge, 200
        return "Falla de verificación", 403
    
    elif request.method == "POST":
        data = request.get_json()
        print("📨 Mensaje POST recibido de WhatsApp")
        # Aquí puedes procesar el mensaje
        return jsonify({"status": "ok"}), 200
    
    return "Método no permitido", 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Iniciando en puerto {port}")
    app.run(host="0.0.0.0", port=port)