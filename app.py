"""
FOCO IA Lab — Agente de Atención al Cliente WhatsApp
Webhook para Twilio WhatsApp API

Configuración necesaria:
1. Cuenta Twilio con WhatsApp habilitado (sandbox o número business)
2. Configurar webhook URL en Twilio: https://tu-dominio.com/webhook
3. Variables de entorno en .env (ver .env.example)

Despliegue local para pruebas:
  ngrok http 5000
  → Usar la URL de ngrok como webhook en Twilio

Despliegue en producción:
  - Railway, Render, Heroku, o VPS propio
"""

import os
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import OrchestratorAgent
from store.conversations import reset_conversation

app = Flask(__name__)
orchestrator = OrchestratorAgent()

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
VALIDATE_TWILIO = os.getenv("VALIDATE_TWILIO_SIGNATURE", "false").lower() == "true"


def validate_twilio_request(f):
    """Decorador para validar que la petición viene de Twilio (producción)."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not VALIDATE_TWILIO:
            return f(*args, **kwargs)

        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        url = request.url
        post_vars = request.form.to_dict()
        signature = request.headers.get("X-Twilio-Signature", "")

        if not validator.validate(url, post_vars, signature):
            return jsonify({"error": "Invalid signature"}), 403
        return f(*args, **kwargs)

    return decorated


@app.route("/webhook", methods=["POST"])
@validate_twilio_request
def webhook():
    """
    Endpoint principal del webhook de Twilio.
    Recibe mensajes de WhatsApp y retorna respuesta en formato TwiML.
    """
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "unknown")
    profile_name = request.values.get("ProfileName", "")

    if not incoming_msg:
        return _twiml_response("")

    print(f"[WEBHOOK] Mensaje de {sender} ({profile_name}): {incoming_msg[:80]}")

    # Comando de reset para testing
    if incoming_msg.lower() in ("/reset", "!reset"):
        reset_conversation(sender)
        return _twiml_response("Conversación reiniciada. ¡Hola de nuevo! 👋")

    try:
        response_text = orchestrator.process_message(sender, incoming_msg)
        print(f"[WEBHOOK] Respuesta generada ({len(response_text)} chars)")
        return _twiml_response(response_text)
    except Exception as e:
        print(f"[WEBHOOK] Error procesando mensaje: {e}")
        return _twiml_response(
            "Lo siento, tuve un problema técnico momentáneo. ¿Puedes escribirme de nuevo?"
        )


def _twiml_response(text: str):
    resp = MessagingResponse()
    if text:
        resp.message(text)
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/health", methods=["GET"])
def health():
    """Endpoint de salud para monitoreo."""
    return jsonify({
        "status": "ok",
        "service": "FOCO IA Lab WhatsApp Agent",
        "website": "www.focoialab.com"
    })


@app.route("/test", methods=["GET"])
def test_conversation():
    """
    Endpoint de prueba (solo para desarrollo).
    Uso: GET /test?sender=test_user&message=Hola
    """
    if os.getenv("FLASK_ENV") == "production":
        return jsonify({"error": "Not available in production"}), 403

    sender = request.args.get("sender", "whatsapp:+1234567890")
    message = request.args.get("message", "Hola")

    response = orchestrator.process_message(sender, message)
    return jsonify({
        "sender": sender,
        "message": message,
        "response": response
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"[APP] FOCO IA Lab WhatsApp Agent iniciando en puerto {port}")
    print(f"[APP] Webhook URL: http://localhost:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=debug)
