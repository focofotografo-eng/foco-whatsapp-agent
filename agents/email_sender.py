"""
Agente de Email — FOCO IA Lab
Genera y envía el resumen estratégico del contacto al equipo de Cristian Foco
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import anthropic

client = anthropic.Anthropic()

RECIPIENT_EMAIL = "focofotografo@gmail.com"
SENDER_EMAIL = os.getenv("GMAIL_USER", "focofotografo@gmail.com")
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def generate_strategic_summary(contact_data: dict, conversation_history: list[dict]) -> str:
    """
    Usa Claude claude-opus-4-6 para generar un resumen estratégico del contacto
    con recomendaciones para la llamada de diagnóstico.
    """
    messages_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history
    ])

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        thinking={"type": "adaptive"},
        system="""Eres el analista estratégico de FOCO IA Lab. Tu trabajo es analizar conversaciones
con potenciales clientes y generar un resumen estratégico detallado para que Cristian Foco
pueda prepararse para la llamada de diagnóstico de forma óptima.

FOCO IA Lab ofrece: Estrategias de Comunicación Inteligente, Sistemas IA, Automatización de Procesos.
Público: Restaurantes y Marcas Personales hispanas.
Filosofía: "Los negocios no necesitan más contenido. Necesitan funcionar mejor."

Genera un análisis profesional y accionable en español.""",
        messages=[{
            "role": "user",
            "content": f"""Analiza esta conversación y genera un resumen estratégico completo.

DATOS DEL CONTACTO:
- Nombre: {contact_data.get('nombre', 'No proporcionado')}
- Email: {contact_data.get('email', 'No proporcionado')}
- WhatsApp: {contact_data.get('whatsapp', 'No proporcionado')}
- Negocio: {contact_data.get('nombre_negocio', 'No proporcionado')}
- Descripción: {contact_data.get('descripcion_negocio', 'No proporcionado')}

CONVERSACIÓN COMPLETA:
{messages_text}

Por favor incluye:
1. Resumen del perfil del contacto y su negocio
2. Problema/necesidad principal identificada
3. Nivel de interés y madurez comercial (1-10)
4. Servicios de FOCO IA Lab más relevantes para su caso
5. Puntos clave a tratar en la llamada de diagnóstico
6. Posibles objeciones y cómo abordarlas
7. Recomendación de estrategia de seguimiento"""
        }]
    )

    # Extraer solo el texto (no el bloque de thinking)
    for block in response.content:
        if block.type == "text":
            return block.text

    return "No se pudo generar el resumen estratégico."


def send_contact_email(sender_id: str, contact_data: dict, conversation_history: list[dict]) -> bool:
    """
    Genera y envía el email de resumen estratégico a Cristian Foco.

    Returns True si el email se envió correctamente.
    """
    strategic_summary = generate_strategic_summary(contact_data, conversation_history)

    nombre = contact_data.get("nombre", "Contacto nuevo")
    negocio = contact_data.get("nombre_negocio", "Sin nombre")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Construir el email HTML
    html_body = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; max-width: 700px; margin: 0 auto; }}
        .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 22px; }}
        .header p {{ margin: 5px 0 0; opacity: 0.8; font-size: 14px; }}
        .section {{ background: #f9f9f9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #e94560; }}
        .section h2 {{ color: #1a1a2e; margin-top: 0; font-size: 16px; }}
        .data-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .data-item {{ background: white; padding: 10px; border-radius: 6px; }}
        .data-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
        .data-value {{ font-size: 15px; font-weight: bold; color: #1a1a2e; margin-top: 4px; }}
        .summary {{ background: white; padding: 20px; border-radius: 8px; white-space: pre-wrap; line-height: 1.7; font-size: 14px; }}
        .footer {{ background: #1a1a2e; color: #888; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; text-align: center; }}
        .badge {{ display: inline-block; background: #e94560; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Nuevo Contacto — FOCO IA Lab</h1>
        <p>Recibido el {fecha} via WhatsApp</p>
    </div>

    <div class="section">
        <h2>📋 Datos del Contacto</h2>
        <div class="data-grid">
            <div class="data-item">
                <div class="data-label">Nombre</div>
                <div class="data-value">{contact_data.get('nombre') or '—'}</div>
            </div>
            <div class="data-item">
                <div class="data-label">Email</div>
                <div class="data-value">{contact_data.get('email') or '—'}</div>
            </div>
            <div class="data-item">
                <div class="data-label">WhatsApp</div>
                <div class="data-value">{contact_data.get('whatsapp') or sender_id}</div>
            </div>
            <div class="data-item">
                <div class="data-label">Negocio</div>
                <div class="data-value">{contact_data.get('nombre_negocio') or '—'}</div>
            </div>
        </div>
        <div style="margin-top:10px;">
            <div class="data-label">Descripción del negocio</div>
            <p style="background:white; padding:10px; border-radius:6px; margin:5px 0;">
                {contact_data.get('descripcion_negocio') or '—'}
            </p>
        </div>
    </div>

    <div class="section">
        <h2>🧠 Análisis Estratégico <span class="badge">IA</span></h2>
        <div class="summary">{strategic_summary}</div>
    </div>

    <div class="footer">
        FOCO IA Lab — Sistema de Atención Automática WhatsApp
        | www.focoialab.com
    </div>
</body>
</html>
"""

    plain_text = f"""
NUEVO CONTACTO - FOCO IA LAB
Fecha: {fecha}

DATOS DE CONTACTO:
- Nombre: {contact_data.get('nombre', '—')}
- Email: {contact_data.get('email', '—')}
- WhatsApp: {contact_data.get('whatsapp', sender_id)}
- Negocio: {contact_data.get('nombre_negocio', '—')}
- Descripción: {contact_data.get('descripcion_negocio', '—')}

ANÁLISIS ESTRATÉGICO:
{strategic_summary}
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Nuevo Lead WhatsApp: {nombre} ({negocio}) — FOCO IA Lab"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if not SENDER_PASSWORD:
        print(f"[EMAIL] GMAIL_APP_PASSWORD no configurado. Email no enviado.")
        print(f"[EMAIL] Destinatario: {RECIPIENT_EMAIL}")
        print(f"[EMAIL] Asunto: {msg['Subject']}")
        return False

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"[EMAIL] Email enviado exitosamente a {RECIPIENT_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] Error de autenticación Gmail. Verifica GMAIL_APP_PASSWORD.")
        return False
    except Exception as e:
        print(f"[EMAIL] Error enviando email: {e}")
        return False
