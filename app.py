from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Configuración
VERIFY_TOKEN = "mi_token_secreto_123"

# ========== RUTA RAÍZ (CRÍTICA) ==========
@app.route("/")
def home():
    return """
    <h1>✅ WhatsApp Webhook Funcionando</h1>
    <p><strong>Webhook URL:</strong> https://meta-chat-npbx.onrender.com/webhook</p>
    <p><strong>Verify Token:</strong> <code>mi_token_secreto_123</code></p>
    <p><a href="/webhook">Test webhook</a></p>
    """, 200

# ========== WEBHOOK ==========
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("🔔 Webhook accedido")
    
    if request.method == "GET":
        # Meta envía estos parámetros para verificación
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        print(f"   Mode: {mode}, Token: {token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("   ✅ VERIFICACIÓN EXITOSA")
            return challenge, 200
        else:
            print("   ❌ Falla de verificación")
            return "Falla de verificación", 403
    
    elif request.method == "POST":
        # Mensajes entrantes de WhatsApp
        data = request.get_json()
        print("📨 Mensaje POST recibido")
        print(json.dumps(data, indent=2))
        
        # Responder OK a Meta
        return jsonify({"status": "ok"}), 200
    
    else:
        return "Método no permitido", 405

# ========== INICIAR ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host="0.0.0.0", port=port)