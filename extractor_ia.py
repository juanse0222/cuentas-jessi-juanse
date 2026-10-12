"""
Extractor de transacciones por IA — a diferencia de importador.py (un parser
por remitente conocido), esto usa Claude para leer CUALQUIER correo o PDF
adjunto y proponer fecha/monto/categoría, sin necesitar un parser nuevo por
cada formato. Pensado como complemento, no reemplazo: los parsers de
importador.py siguen siendo más baratos y deterministas para los remitentes
que ya conocemos bien (BBVA, Falabella, SURA, FVL...).
"""

from __future__ import annotations

import base64
import email
import imaplib
import json
from datetime import datetime, timedelta

import anthropic
import pandas as pd
import pdfplumber

from importador import _cuerpo_texto  # reutiliza el mismo extractor de cuerpo de correo

MODELO = "claude-opus-5"

# Términos amplios para encontrar candidatos a notificación financiera sin
# conocer de antemano el remitente exacto — más ruidoso que los buscadores
# de importador.py a propósito, Claude filtra lo que no aplica.
TERMINOS_BUSQUEDA_AMPLIA = [
    "nomina", "comprobante de pago", "recibo de pago", "factura",
    "consignacion", "transaccion aprobada", "pago aprobado",
    "certificado de pago", "desprendible",
]

_PROMPT_SISTEMA = """Eres un extractor de datos financieros. Te paso el texto de un correo \
(y a veces un PDF adjunto) que podría ser una notificación de pago, nómina, factura o \
recibo. Tu trabajo es decidir si es una transacción financiera real y extraer sus datos.

Reglas importantes:
- Si NO es una notificación de una transacción real (ej. un newsletter, una encuesta, \
un recordatorio sin monto), responde con es_transaccion: false y el resto de campos null.
- "tipo" es "ingreso" solo si es dinero que la persona RECIBE (salario, nómina, prima, \
reembolso). Todo lo demás (pagos, compras, facturas, servicios) es "gasto".
- "categoria_subcategoria" debe ser EXACTAMENTE uno de los valores de la lista que te doy, \
copiado tal cual (con el emoji incluido). Si ninguno encaja bien, usa null.
- "fecha" es la fecha real de la transacción (de pago, de nómina, de liquidación), no la \
fecha de envío del correo si son distintas — en formato YYYY-MM-DD.
- "monto" es el valor neto/total de la transacción, como número sin separadores de miles.
- Sé conservador: si no estás seguro de un campo, usa null en vez de adivinar."""


def _schema(opciones_categoria: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "es_transaccion": {"type": "boolean"},
            "fecha": {"type": ["string", "null"]},
            "monto": {"type": ["number", "null"]},
            "concepto": {"type": ["string", "null"]},
            "tipo": {"type": ["string", "null"], "enum": ["gasto", "ingreso", None]},
            "categoria_subcategoria": {
                "type": ["string", "null"],
                "enum": opciones_categoria + [None],
            },
            "confianza": {"type": ["string", "null"], "enum": ["alta", "media", "baja", None]},
        },
        "required": ["es_transaccion", "fecha", "monto", "concepto", "tipo",
                     "categoria_subcategoria", "confianza"],
        "additionalProperties": False,
    }


def extraer_transaccion(
    texto: str, opciones_categoria: list[str], api_key: str,
    pdf_bytes: bytes | None = None,
) -> dict | None:
    client = anthropic.Anthropic(api_key=api_key)

    contenido = []
    if pdf_bytes:
        contenido.append({
            "type": "document",
            "source": {
                "type": "base64", "media_type": "application/pdf",
                "data": base64.standard_b64encode(pdf_bytes).decode("utf-8"),
            },
        })
    contexto = (
        f"Categorías válidas (usa exactamente uno de estos valores o null):\n"
        f"{chr(10).join(opciones_categoria)}\n\n"
        f"Texto del correo:\n{texto[:6000]}"
    )
    contenido.append({"type": "text", "text": contexto})

    respuesta = client.messages.create(
        model=MODELO,
        max_tokens=1024,
        system=_PROMPT_SISTEMA,
        messages=[{"role": "user", "content": contenido}],
        output_config={"format": {"type": "json_schema", "schema": _schema(opciones_categoria)}},
    )
    texto_json = next((b.text for b in respuesta.content if b.type == "text"), None)
    if not texto_json:
        return None
    datos = json.loads(texto_json)
    return datos if datos.get("es_transaccion") else None


def _adjunto_pdf(msg: email.message.Message) -> bytes | None:
    for part in msg.walk():
        nombre = (part.get_filename() or "").lower()
        if part.get_content_disposition() == "attachment" and nombre.endswith(".pdf"):
            return part.get_payload(decode=True)
    return None


def buscar_correos_ia(
    usuario: str, app_password: str, dias: int, api_key: str,
    opciones_categoria: list[str], persona: str,
) -> pd.DataFrame:
    desde = (datetime.now() - timedelta(days=dias)).strftime("%d-%b-%Y")
    terminos = " ".join(f'OR SUBJECT "{t}"' for t in TERMINOS_BUSQUEDA_AMPLIA[1:])
    criterio = f'(SINCE "{desde}" (OR SUBJECT "{TERMINOS_BUSQUEDA_AMPLIA[0]}" {terminos}))'

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    filas = []
    total_revisados = 0
    try:
        imap.login(usuario, app_password)
        imap.select("INBOX", readonly=True)
        _, datos = imap.search(None, criterio)
        ids = datos[0].split()
        total_revisados = len(ids)

        for msg_id in ids:
            _, msg_datos = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_datos[0][1])
            texto = _cuerpo_texto(msg)
            pdf_bytes = _adjunto_pdf(msg)

            try:
                extraido = extraer_transaccion(texto, opciones_categoria, api_key, pdf_bytes)
            except Exception:
                continue
            if not extraido or not extraido.get("fecha") or not extraido.get("monto"):
                continue

            categoria, subcategoria = (None, None)
            if extraido.get("categoria_subcategoria"):
                categoria, subcategoria = extraido["categoria_subcategoria"].split(" → ", 1)

            try:
                fecha = datetime.strptime(extraido["fecha"], "%Y-%m-%d").date()
            except ValueError:
                continue

            filas.append({
                "fecha": fecha,
                "descripcion": extraido.get("concepto") or msg.get("Subject", ""),
                "monto": abs(float(extraido["monto"])),
                "tipo": extraido.get("tipo") or "gasto",
                "categoria_sugerida": categoria,
                "subcategoria_sugerida": subcategoria,
                "origen": "IA (correo)",
                "persona_sugerida": persona,
            })
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    df = pd.DataFrame(filas)
    df.attrs["total_mensajes"] = total_revisados
    df.attrs["no_reconocidos"] = total_revisados - len(filas)
    return df
