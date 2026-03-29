"""
FOCO IA Lab — Agente WhatsApp con Voiceflow
Webhook para Twilio WhatsApp API → Voiceflow Dialog Manager API
"""

import os
import requests
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VF_API_KEY = os.getenv("VF_API_KEY", "")
VF_PROJECT_ID = os.getenv("VF_PROJECT_ID", "")
VF_BASE_URL = "https://general-runtime.voiceflow.com"


def voiceflow_interact(user_id: str, message: str) -> str:
    """Envía mensaje a Voiceflow y retorna la respuesta en texto."""
    url = f"{VF_BASE_URL}/state/user/{user_id}/interact"
    headers = {
        "Authorization": VF_API_KEY,
        "Content-Type": "application/json",
        "versionID": "production",
    }
    payload = {
        "action": {"type": "text", "payload": message},
        "config": {"tts": False, "stripSSML": True},
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        traces = response.json()

        texts = []
        for trace in traces:
            if trace.get("type") == "text":
                msg = trace.get("payload", {}).get("message", "")
                if msg:
                    texts.append(msg)
            elif trace.get("type") == "speak":
                msg = trace.get("payload", {}).get("message", "")
                if msg:
                    texts.append(msg)

        return "\n\n".join(texts) if texts else "Un momento, ¿puedes repetirme eso?"

    except Exception as e:
        print(f"[VOICEFLOW] Error: {e}")
        return "Lo siento, tuve un problema técnico. ¿Puedes escribirme de nuevo?"


def voiceflow_reset(user_id: str):
    """Reinicia la conversación del usuario en Voiceflow."""
    url = f"{VF_BASE_URL}/state/user/{user_id}"
    headers = {"Authorization": VF_API_KEY}
    try:
        requests.delete(url, headers=headers, timeout=5)
    except Exception as e:
        print(f"[VOICEFLOW] Error al reiniciar: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "unknown")
    profile_name = request.values.get("ProfileName", "")

    if not incoming_msg:
        return _twiml_response("")

    print(f"[WEBHOOK] {sender} ({profile_name}): {incoming_msg[:80]}")

    if incoming_msg.lower() in ("/reset", "!reset"):
        voiceflow_reset(sender)
        return _twiml_response("Conversación reiniciada. ¡Hola de nuevo! 👋")

    response_text = voiceflow_interact(sender, incoming_msg)
    print(f"[WEBHOOK] Respuesta: {response_text[:80]}")
    return _twiml_response(response_text)


def _twiml_response(text: str):
    resp = MessagingResponse()
    if text:
        resp.message(text)
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "FOCO IA Lab WhatsApp Agent",
        "engine": "Voiceflow",
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"[APP] FOCO IA Lab iniciando en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
