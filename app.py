from flask import Flask, request
import os

app = Flask(__name__)

VERIFY_TOKEN = "mi_token_secreto_123"

@app.route("/")
def home():
    return "✅ Servidor estable", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Error", 403
    
    if request.method == "POST":
        print("📨 POST recibido")
        return {"status": "ok"}, 200
    
    return "Método no permitido", 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Iniciando en puerto {port}")
    app.run(host="0.0.0.0", port=port)