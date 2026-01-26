from flask import Flask, request, jsonify
import os

app = Flask(__name__)

VERIFY_TOKEN = "mi_token_secreto_123"

@app.route("/")
def home():
    return """
    <h1>✅ WhatsApp Webhook (VERSIÓN ESTABLE)</h1>
    <p><strong>Webhook URL:</strong> https://meta-chat-npbx.onrender.com/webhook</p>
    <p><strong>Token:</strong> mi_token_secreto_123</p>
    <p><strong>Estado:</strong> Servidor estable - Esperando webhooks</p>
    <p><strong>Última verificación:</strong> {}</p>
    """.format("Ninguna aún"), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("=" * 50)
    print(f"🔔 WEBHOOK ACCEDIDO - Método: {request.method}")
    print(f"   URL: {request.url}")
    print(f"   Headers: {dict(request.headers)}")
    print("=" * 50)
    
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        print(f"   Parámetros GET:")
        print(f"     hub.mode: {mode}")
        print(f"     hub.verify_token: {token}")
        print(f"     hub.challenge: {challenge}")
        print(f"     Token esperado: {VERIFY_TOKEN}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("   ✅ VERIFICACIÓN EXITOSA - Devolviendo challenge")
            return challenge, 200
        else:
            print("   ❌ FALLA DE VERIFICACIÓN")
            return "Falla de verificación", 403
    
    elif request.method == "POST":
        print("📨 POST RECIBIDO")
        
        try:
            data = request.get_json()
            print(f"   JSON recibido: {json.dumps(data, indent=2)[:500]}...")
        except Exception as e:
            print(f"   Error leyendo JSON: {e}")
            data = {}
        
        print("   ✅ Respondiendo OK a Meta")
        return jsonify({"status": "ok", "message": "Webhook recibido"}), 200
    
    else:
        print(f"   ❌ Método no permitido: {request.method}")
        return "Método no permitido", 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("=" * 50)
    print(f"🚀 INICIANDO SERVIDOR FLASK ESTABLE")
    print(f"   Puerto: {port}")
    print(f"   Token: {VERIFY_TOKEN}")
    print(f"   Webhook: /webhook")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)