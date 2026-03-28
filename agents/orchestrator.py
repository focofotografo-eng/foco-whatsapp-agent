"""
Agente Orquestador — FOCO IA Lab WhatsApp
Coordina subagentes especializados para gestionar la conversación de atención al cliente.

Arquitectura de Orquestación:
  Orchestrator (claude-opus-4-6)
    ├── Conversation Agent     → Genera respuestas al usuario
    ├── Data Extractor Agent   → Extrae datos de contacto (claude-haiku-4-5)
    └── Email Sender Agent     → Envía resumen al cierre de conversación
"""

import json
import os
import anthropic

from config.knowledge_base import FOCO_SERVICE_KNOWLEDGE, AGENT_PERSONA
from store.conversations import (
    load_conversation,
    save_conversation,
    append_message,
    update_stage,
    update_contact_data,
    is_data_complete,
    mark_email_sent,
)
from agents.data_extractor import extract_contact_data, determine_conversation_stage
from agents.email_sender import send_contact_email

client = anthropic.Anthropic()

ORCHESTRATOR_SYSTEM = f"""
{AGENT_PERSONA}

{FOCO_SERVICE_KNOWLEDGE}

# INSTRUCCIONES DE CONVERSACIÓN

Eres el agente de atención al cliente de FOCO IA Lab en WhatsApp. Tu objetivo es:
1. Entender la necesidad del visitante
2. Explicar cómo FOCO IA Lab puede ayudarles específicamente
3. Recopilar sus datos de forma natural y conversacional
4. Llevarles sutilmente a agendar una llamada de diagnóstico gratuita con Cristian

# FLUJO DE CONVERSACIÓN

## ETAPA: greeting
- Saluda calurosamente
- Presenta FOCO IA Lab brevemente
- Pregunta en qué puedes ayudar
- Ejemplo: "¡Hola! 👋 Soy el asistente de FOCO IA Lab, la agencia que ayuda a negocios a comunicarse y operar mejor con IA. ¿En qué puedo ayudarte hoy?"

## ETAPA: diagnosis
- Escucha activamente su necesidad
- Haz 1-2 preguntas para entender mejor su negocio
- Identifica: tipo de negocio, tamaño, problemas principales

## ETAPA: education
- Conecta sus necesidades específicas con los servicios de FOCO IA Lab
- Usa ejemplos concretos y beneficios tangibles
- Genera interés y confianza
- NO abrumes con información, sé selectivo y relevante

## ETAPA: data_collection
- Pide los datos de forma NATURAL, no como formulario
- Explica para qué los necesitas: "Para preparar algo personalizado para ti..."
- Pide en este orden sugerido: nombre → nombre del negocio → descripción → email → WhatsApp
- Confirma cada dato con naturalidad

## ETAPA: closing
- Resume lo entendido sobre su negocio
- Propone la llamada de diagnóstico gratuita con Cristian
- Explica el valor: "En 30 minutos, Cristian puede mostrarte exactamente cómo la IA puede transformar tu negocio"
- Facilita el siguiente paso
- Al final pregunta: "¿Tienes alguna otra duda antes de que lo dejemos aquí?"

## ETAPA: farewell
- Responde cualquier duda final con claridad y sin prisa
- Si no tiene más dudas, cierra con calidez
- Haz que se sienta resuelto: que salió con más claridad de la que entró
- Recuérdale que puede escribir a Cristian directamente: +34 674 05 76 93
- Despedida genuina, cercana, sin presión
- Ejemplo de tono: "Ha sido un placer hablar contigo. Ya tienes el camino claro — cuando quieras dar el siguiente paso, Cristian estará listo. ¡Mucho éxito con tu negocio! 🙌"

# REGLAS IMPORTANTES
- Mensajes CORTOS para WhatsApp (máx 3-4 líneas por mensaje)
- Un solo tema o pregunta por mensaje
- Sé empático y genuinamente interesado en ayudar
- Si el usuario se pone hostil o no quiere continuar, agradece su tiempo y despídete
- NUNCA inventes precios o resultados garantizados

# ETAPA ACTUAL: {{stage}}

# DATOS YA RECOPILADOS: {{contact_data}}
"""


class OrchestratorAgent:
    """
    Orquestador principal del sistema multi-agente de WhatsApp.
    Coordina el flujo de conversación y delega tareas a subagentes especializados.
    """

    def process_message(self, sender_id: str, user_message: str) -> str:
        """
        Procesa un mensaje entrante de WhatsApp y retorna la respuesta del agente.

        Pipeline:
        1. Cargar estado de conversación
        2. Guardar mensaje del usuario
        3. [Subagente] Extractor: actualizar datos de contacto detectados
        4. [Subagente] Extractor: determinar/actualizar etapa de conversación
        5. [Agente principal] Generar respuesta contextual
        6. Guardar respuesta
        7. Si conversación completa → [Subagente] Email
        """
        # 1. Cargar estado
        conv = load_conversation(sender_id)
        stage = conv["stage"]
        contact_data = conv["contact_data"]

        # 2. Guardar mensaje entrante
        append_message(sender_id, "user", user_message)
        conv = load_conversation(sender_id)

        # 3. Extraer datos de contacto (subagente)
        if stage not in ("complete",):
            extracted = extract_contact_data(conv["messages"])
            for field, value in extracted.items():
                if value and not contact_data.get(field):
                    update_contact_data(sender_id, field, value)
                    contact_data[field] = value

        # 4. Determinar etapa (subagente) — solo avanza hacia adelante
        if stage not in ("complete",):
            new_stage = determine_conversation_stage(conv["messages"], stage)
            if new_stage != stage:
                update_stage(sender_id, new_stage)
                stage = new_stage

        # 5. Generar respuesta principal
        response_text = self._generate_response(
            messages=conv["messages"],
            stage=stage,
            contact_data=contact_data,
            sender_id=sender_id,
        )

        # 6. Guardar respuesta
        append_message(sender_id, "assistant", response_text)

        # 7. Enviar email cuando llegamos a farewell o complete (datos completos + cierre iniciado)
        conv = load_conversation(sender_id)
        if not conv["email_sent"] and is_data_complete(sender_id) and stage in ("farewell", "complete"):
            try:
                sent = send_contact_email(
                    sender_id=sender_id,
                    contact_data=conv["contact_data"],
                    conversation_history=conv["messages"],
                )
                if sent:
                    mark_email_sent(sender_id)
                    update_stage(sender_id, "complete")
            except Exception as e:
                print(f"[ORCHESTRATOR] Error enviando email: {e}")

        return response_text

    def _generate_response(
        self,
        messages: list[dict],
        stage: str,
        contact_data: dict,
        sender_id: str,
    ) -> str:
        """
        Agente de conversación: genera la respuesta apropiada para el usuario.
        Usa claude-opus-4-6 con el contexto completo del negocio.
        """
        # Formatear datos de contacto para el system prompt
        contact_summary = []
        for field, value in contact_data.items():
            if value:
                labels = {
                    "nombre": "Nombre",
                    "email": "Email",
                    "whatsapp": "WhatsApp",
                    "nombre_negocio": "Negocio",
                    "descripcion_negocio": "Descripción negocio",
                }
                contact_summary.append(f"- {labels.get(field, field)}: {value}")

        contact_str = "\n".join(contact_summary) if contact_summary else "Ninguno aún"

        system = ORCHESTRATOR_SYSTEM.replace("{{stage}}", stage).replace(
            "{{contact_data}}", contact_str
        )

        # Convertir historial al formato de la API (excluir timestamps)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        # Asegurar que el último mensaje es del usuario
        if not api_messages or api_messages[-1]["role"] != "user":
            return "Lo siento, no pude procesar tu mensaje. ¿Puedes intentarlo de nuevo?"

        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=512,
                system=system,
                messages=api_messages,
            )
            return response.content[0].text.strip()
        except anthropic.RateLimitError:
            return "En este momento tengo mucha actividad. ¿Puedes escribirme en unos minutos? 🙏"
        except anthropic.APIError as e:
            print(f"[ORCHESTRATOR] Error API: {e}")
            return "Tuve un problema técnico. ¿Puedes repetir tu mensaje?"
