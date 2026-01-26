from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "mi_token_secreto_123"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Token de verificación incorrecto", 403

    if request.method == "POST":
        data = request.get_json()
        print("Mensaje entrante:", data)
        return "EVENT_RECEIVED", 200

    return "Método no permitido", 405