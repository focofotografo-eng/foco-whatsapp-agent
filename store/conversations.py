"""
Gestión de estado de conversaciones WhatsApp
Persiste conversaciones por número de teléfono en archivos JSON
"""

import json
import os
from datetime import datetime
from typing import Optional


STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "conversations")


def _ensure_store():
    os.makedirs(STORE_DIR, exist_ok=True)


def _conv_path(sender_id: str) -> str:
    safe_id = sender_id.replace("+", "").replace(":", "_").replace(" ", "_")
    return os.path.join(STORE_DIR, f"{safe_id}.json")


def load_conversation(sender_id: str) -> dict:
    """Carga el estado de conversación de un contacto."""
    _ensure_store()
    path = _conv_path(sender_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _new_conversation(sender_id)


def save_conversation(sender_id: str, data: dict):
    """Guarda el estado de conversación."""
    _ensure_store()
    data["updated_at"] = datetime.now().isoformat()
    path = _conv_path(sender_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _new_conversation(sender_id: str) -> dict:
    return {
        "sender_id": sender_id,
        "stage": "greeting",
        "messages": [],
        "contact_data": {
            "nombre": None,
            "email": None,
            "whatsapp": None,
            "nombre_negocio": None,
            "descripcion_negocio": None,
        },
        "email_sent": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def append_message(sender_id: str, role: str, content: str):
    """Agrega un mensaje al historial de la conversación."""
    conv = load_conversation(sender_id)
    conv["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    save_conversation(sender_id, conv)


def update_stage(sender_id: str, stage: str):
    """Actualiza la etapa de la conversación."""
    conv = load_conversation(sender_id)
    conv["stage"] = stage
    save_conversation(sender_id, conv)


def update_contact_data(sender_id: str, field: str, value: str):
    """Actualiza un campo de datos del contacto."""
    conv = load_conversation(sender_id)
    conv["contact_data"][field] = value
    save_conversation(sender_id, conv)


def is_data_complete(sender_id: str) -> bool:
    """Verifica si se recopilaron todos los datos necesarios."""
    conv = load_conversation(sender_id)
    data = conv["contact_data"]
    return all(data.get(f) for f in [
        "nombre", "email", "nombre_negocio", "descripcion_negocio"
    ])


def mark_email_sent(sender_id: str):
    """Marca que el email de resumen fue enviado."""
    conv = load_conversation(sender_id)
    conv["email_sent"] = True
    save_conversation(sender_id, conv)


def reset_conversation(sender_id: str):
    """Reinicia la conversación (para testing)."""
    _ensure_store()
    path = _conv_path(sender_id)
    if os.path.exists(path):
        os.remove(path)
