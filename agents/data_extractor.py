"""
Subagente especializado en extracción de datos de contacto
Usa claude-haiku-4-5 para mayor velocidad y costo reducido
"""

import json
import anthropic

client = anthropic.Anthropic()


def extract_contact_data(conversation_history: list[dict]) -> dict:
    """
    Analiza el historial de conversación y extrae cualquier dato de contacto
    que el usuario haya proporcionado.

    Retorna un dict con los campos encontrados (None si no están disponibles).
    """
    messages_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-10:]  # Últimos 10 mensajes
    ])

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system="""Eres un extractor de datos de contacto. Analiza conversaciones de WhatsApp
y extrae información de contacto mencionada por el usuario.

Responde SIEMPRE con un JSON válido con esta estructura exacta:
{
  "nombre": "nombre completo o null",
  "email": "email o null",
  "whatsapp": "número de WhatsApp/teléfono o null",
  "nombre_negocio": "nombre del negocio o null",
  "descripcion_negocio": "descripción del negocio o null"
}

Solo incluye valores que estén EXPLÍCITAMENTE mencionados en la conversación.
Para campos no mencionados, usa null.""",
        messages=[{
            "role": "user",
            "content": f"Extrae los datos de contacto de esta conversación:\n\n{messages_text}"
        }]
    )

    text = response.content[0].text.strip()
    # Limpiar posible markdown
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "nombre": None,
            "email": None,
            "whatsapp": None,
            "nombre_negocio": None,
            "descripcion_negocio": None,
        }


def determine_conversation_stage(conversation_history: list[dict], current_stage: str) -> str:
    """
    Analiza el estado actual de la conversación y determina si se debe
    avanzar a la siguiente etapa.

    Etapas: greeting → diagnosis → education → data_collection → closing → farewell → complete
    """
    STAGE_ORDER = ["greeting", "diagnosis", "education", "data_collection", "closing", "farewell", "complete"]

    if current_stage == "complete":
        return "complete"

    messages_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-6:]
    ])

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        system=f"""Analiza esta conversación de WhatsApp y determina la etapa actual.

Etapas posibles (en orden):
- greeting: Primer contacto, aún no se entendió la necesidad
- diagnosis: Se está entendiendo qué necesita el usuario
- education: Se está explicando cómo FOCO IA Lab puede ayudar
- data_collection: Se están recopilando datos de contacto
- closing: Se está invitando a agendar una llamada y se pregunta si hay más dudas
- farewell: Se están resolviendo dudas finales o el usuario ya no tiene más preguntas
- complete: Conversación finalizada

Etapa actual: {current_stage}

Responde SOLO con el nombre de la etapa (una sola palabra de las opciones).""",
        messages=[{
            "role": "user",
            "content": f"¿En qué etapa está esta conversación?\n\n{messages_text}"
        }]
    )

    suggested_stage = response.content[0].text.strip().lower()

    # Validar que sea una etapa válida y que no retroceda
    if suggested_stage in STAGE_ORDER:
        current_idx = STAGE_ORDER.index(current_stage)
        suggested_idx = STAGE_ORDER.index(suggested_stage)
        # Solo avanzar, nunca retroceder
        if suggested_idx > current_idx:
            return suggested_stage

    return current_stage
