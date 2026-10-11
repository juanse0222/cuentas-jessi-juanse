"""
Parseo de extractos BBVA (PDF de cuenta y Excel de movimientos) hacia
un formato normalizado listo para revisar e importar como transacciones.
"""

from __future__ import annotations

import html
import imaplib
import email
import io
import re
from datetime import datetime, timedelta

import pandas as pd
import pdfplumber

# ─── Reglas de categorización por palabra clave ──────────────────────────────
# Se evalúan en orden; la primera coincidencia (substring, case-insensitive) gana.
# Cualquier descripción que no calce queda sin sugerencia y debe revisarse a mano.
REGLAS_CATEGORIA = [
    # Entretenimiento / suscripciones
    ("NETFLIX", "🎬 Entretenimiento", "Netflix"),
    ("SPOTIFY", "🎬 Entretenimiento", "Plataformas (Disney/Apple)"),
    ("GOOGLE", "🎬 Entretenimiento", "Google One"),
    ("GRAMMARLY", "🎬 Entretenimiento", "Grammarly"),
    ("ANTHROPIC", "🎬 Entretenimiento", "Claude AI"),
    ("APPLE.COM", "🎬 Entretenimiento", "iCloud Juanse"),
    ("CINE COLOMBIA", "🎬 Entretenimiento", "Salidas / Ocio"),
    ("CINEPO", "🎬 Entretenimiento", "Salidas / Ocio"),
    ("MULTIPLEX", "🎬 Entretenimiento", "Salidas / Ocio"),

    # Comida — domicilios primero (más específico que "restaurantes")
    ("RAPPI", "🍽️ Comida", "Domicilios"),
    # Supermercados
    ("CARULLA", "🍽️ Comida", "Mercado mensual"),
    ("EXITO", "🍽️ Comida", "Mercado mensual"),
    ("JUMBO", "🍽️ Comida", "Mercado mensual"),
    ("TIENDA D1", "🍽️ Comida", "Mercado adicional"),
    ("TIENDAS ARA", "🍽️ Comida", "Mercado adicional"),
    ("NOVAVENTA", "🍽️ Comida", "Mercado mensual"),
    ("PRICESMART", "🍽️ Comida", "Mercado mensual"),
    ("MERCAMIO", "🍽️ Comida", "Mercado adicional"),
    ("JERONIMO MARTINS", "🍽️ Comida", "Mercado adicional"),
    # Restaurantes / cafés / comida rápida (orden importa: antes de otras reglas genéricas)
    ("FRISBY", "🍽️ Comida", "Restaurantes"),
    ("KFC", "🍽️ Comida", "Restaurantes"),
    ("MC DONALD", "🍽️ Comida", "Restaurantes"),
    ("SUBWAY", "🍽️ Comida", "Restaurantes"),
    ("TAQUERIA", "🍽️ Comida", "Restaurantes"),
    ("DUNKIN DONUTS", "🍽️ Comida", "Restaurantes"),
    ("SR WOK", "🍽️ Comida", "Restaurantes"),
    ("FUSION WOK", "🍽️ Comida", "Restaurantes"),
    ("CAPPRIATO", "🍽️ Comida", "Restaurantes"),
    ("JUAN VALDEZ", "🍽️ Comida", "Restaurantes"),
    ("GOYURT", "🍽️ Comida", "Restaurantes"),
    ("HELADERIA", "🍽️ Comida", "Restaurantes"),
    ("PANADERIA", "🍽️ Comida", "Restaurantes"),
    ("CAFE", "🍽️ Comida", "Restaurantes"),
    ("CAFFE", "🍽️ Comida", "Restaurantes"),
    ("DOLCE BOCATTO", "🍽️ Comida", "Restaurantes"),
    ("HASHTAG FOOD", "🍽️ Comida", "Restaurantes"),
    ("PECANA", "🍽️ Comida", "Restaurantes"),
    ("STORIA D AMORE", "🍽️ Comida", "Restaurantes"),
    ("BOLD*", "🍽️ Comida", "Restaurantes"),
    ("BOLD SA*", "🍽️ Comida", "Restaurantes"),
    ("SOBREMESA", "🍽️ Comida", "Restaurantes"),
    ("CREPES Y WAFFLES", "🍽️ Comida", "Restaurantes"),
    ("TUGO", "🍽️ Comida", "Restaurantes"),

    # Transporte
    ("UBER", "🚗 Transporte", "Otro"),
    ("DIDI", "🚗 Transporte", "Otro"),
    ("EDS ", "🚗 Transporte", "Combustible"),
    ("PWS*EDS", "🚗 Transporte", "Combustible"),
    ("PETROB", "🚗 Transporte", "Combustible"),

    # Cuidado personal / salud
    ("FARMATODO", "💆 Cuidado Personal", "Médicos / Salud"),
    ("DROGUERIA", "💆 Cuidado Personal", "Médicos / Salud"),
    ("DROGUER", "💆 Cuidado Personal", "Médicos / Salud"),
    ("DROG ", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CRUZ VERDE", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CENTRO MEDICO", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CLINICA", "💆 Cuidado Personal", "Médicos / Salud"),
    ("IPS SALUD", "💆 Cuidado Personal", "Médicos / Salud"),
    ("IMBANACO", "💆 Cuidado Personal", "Médicos / Salud"),
    ("KRIKA BEAUTY", "💆 Cuidado Personal", "Pelo y uñas Jessi"),

    # Préstamos / tarjetas de crédito
    # Ojo: debe exigir "PSE A" para distinguir el PAGO de la tarjeta de una
    # COMPRA hecha en la tienda física (ej. "COMPRA EN ALKOSTO CALI" no es
    # un pago de tarjeta, es un gasto real que no debe caer en este bucket).
    ("PSE A BANCOOMEVA", "💳 Préstamos", "Tarjeta Bancoomeva"),
    ("PSE A ALKOSTO", "💳 Préstamos", "Tarjeta Alkosto"),
    ("PSE A FALABELLA", "💳 Préstamos", "Tarjeta Falabella"),

    # Casa — servicios
    ("GASES DE OCCIDE", "🏠 Casa — Básico", "Gas (Gases de Occidente)"),
    ("EMCAL", "🏠 Casa — Básico", "Energía (Emcali)"),
    ("COLOMBIA TELECO", "🏠 Casa — Básico", "Internet (Claro)"),
    ("SAUCEDO Y SAUCE", "🏠 Casa — Básico", "Arriendo Sayab"),

    # Seguros
    ("SEGUROS DE VIDA", "🛡️ Seguro", "Otro"),
    ("ZONA P SURA", "🛡️ Seguro", "Sura Póliza Salud"),

    # Ahorros / inversión
    ("FAP MUNDIAL", "💰 Ahorros e Inversiones", "Cuenta de inversión"),
    ("FONDO DE INVERS", "💰 Ahorros e Inversiones", "Cuenta de inversión"),
    ("PATRIMONIOS AUT", "💰 Ahorros e Inversiones", "Cuenta de jubilación"),

    # Impuestos
    ("IMPUESTO 4X1", "📄 Impuestos", "Otro"),

    # Ingresos (abonos de nómina conocidos)
    ("800024390 EMPRESAS CALI", "Ingreso — Juanse", "DIME"),
    ("CORPORACION CENTRO INTE", "Ingreso — Juanse", "CIDEIM"),
    ("JUAN SEBA UNIVERSIDAD DE", "Ingreso — Juanse", "UNISABANA"),
]


def sugerir_categoria(descripcion: str, tipo: str) -> tuple[str | None, str | None]:
    desc_up = descripcion.upper()
    for clave, categoria, subcategoria in REGLAS_CATEGORIA:
        if clave in desc_up:
            return categoria, subcategoria
    return None, None


def _parsear_monto_es(texto: str) -> float:
    """Convierte '$ -1.642.336,00' (formato es-CO) a float."""
    limpio = texto.replace("$", "").strip()
    negativo = limpio.startswith("-")
    limpio = limpio.replace("-", "").replace(".", "").replace(",", ".")
    valor = float(limpio)
    return -valor if negativo else valor


def parsear_excel(file) -> pd.DataFrame:
    """Parsea el export 'Movements_*.xlsx' de banca en línea BBVA."""
    df = pd.read_excel(file, header=2)
    mask_fecha = df["Fecha"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}T")
    df = df[mask_fecha].copy()

    filas = []
    for _, row in df.iterrows():
        fecha = datetime.fromisoformat(str(row["Fecha"])[:19]).date()
        monto_signed = _parsear_monto_es(str(row["Monto"]))
        tipo = "ingreso" if monto_signed > 0 else "gasto"
        descripcion = str(row["Descripción"]).strip()
        categoria, subcategoria = sugerir_categoria(descripcion, tipo)
        filas.append({
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": abs(monto_signed),
            "tipo": tipo,
            "categoria_sugerida": categoria,
            "subcategoria_sugerida": subcategoria,
            "origen": "Excel",
        })
    return pd.DataFrame(filas)


_LINEA_PDF = re.compile(
    r"^\d+\s+(\d{2}-\d{2}-\d{4})\s+\d{2}-\d{2}-\d{4}\s+(.+?)\s+([\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})$"
)
_SALDO_ANTERIOR = re.compile(r"SALDO CIERRE MES ANTERIOR\s+([\d,]+\.\d{2})")


def parsear_pdf(file) -> pd.DataFrame:
    """Parsea un 'Extracto Cuenta-N.pdf' de banca BBVA (cuenta de ahorros/corriente)."""
    filas = []
    saldo_anterior = None

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            for linea in texto.split("\n"):
                m_saldo = _SALDO_ANTERIOR.search(linea)
                if m_saldo and saldo_anterior is None:
                    saldo_anterior = float(m_saldo.group(1).replace(",", ""))
                    continue

                m = _LINEA_PDF.match(linea)
                if not m:
                    continue

                fecha_str, descripcion, monto_str, saldo_str = m.groups()
                fecha = datetime.strptime(fecha_str, "%d-%m-%Y").date()
                monto = float(monto_str.replace(",", ""))
                saldo_nuevo = float(saldo_str.replace(",", ""))

                if saldo_anterior is None:
                    # No se encontró el encabezado de saldo inicial; se infiere
                    # por el texto de la descripción (abonos suben el saldo).
                    tipo = "ingreso" if descripcion.upper().startswith(("ABONO", "TRANSFERENCIA RECIBIDA", "NC ABONO")) else "gasto"
                else:
                    tipo = "ingreso" if saldo_nuevo > saldo_anterior else "gasto"

                saldo_anterior = saldo_nuevo
                descripcion = descripcion.strip()
                categoria, subcategoria = sugerir_categoria(descripcion, tipo)
                filas.append({
                    "fecha": fecha,
                    "descripcion": descripcion,
                    "monto": monto,
                    "tipo": tipo,
                    "categoria_sugerida": categoria,
                    "subcategoria_sugerida": subcategoria,
                    "origen": "PDF",
                })

    return pd.DataFrame(filas)


_EMAIL_FECHA = re.compile(r"Fecha de la operaci[oó]n:\s*(\d{4}-\d{2}-\d{2})")
_EMAIL_ESTAB = re.compile(r"Establecimiento:\s*(.+)")
_EMAIL_VALOR = re.compile(r"Valor:\s*\$?\s*([\d,]+\.\d{2})")
_EMAIL_TARJETA = re.compile(r"Tarjeta terminada en:\s*(\*?\d+)")
_EMAIL_REF = re.compile(r"Ref:\s*(\d+)")


def parsear_email_texto(texto: str) -> pd.DataFrame:
    """Parsea el texto de una notificación BBVA de 'Compra Exitosa' (correo o PDF impreso del correo)."""
    filas = []
    # Permite varios correos concatenados en un mismo texto/archivo.
    # Se parte por "Ref:" (antes de los demás campos en el cuerpo del correo)
    # para que Tarjeta/Ref queden en el mismo bloque que su Fecha/Establecimiento/Valor.
    bloques = re.split(r"(?=Ref:\d)", texto)
    for bloque in bloques:
        m_fecha = _EMAIL_FECHA.search(bloque)
        m_estab = _EMAIL_ESTAB.search(bloque)
        m_valor = _EMAIL_VALOR.search(bloque)
        if not (m_fecha and m_estab and m_valor):
            continue

        fecha = datetime.strptime(m_fecha.group(1), "%Y-%m-%d").date()
        establecimiento = m_estab.group(1).strip()
        monto = float(m_valor.group(1).replace(",", ""))
        m_tarjeta = _EMAIL_TARJETA.search(bloque)
        m_ref = _EMAIL_REF.search(bloque)

        descripcion = f"COMPRA EN {establecimiento}"
        categoria, subcategoria = sugerir_categoria(descripcion, "gasto")
        filas.append({
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": monto,
            "tipo": "gasto",
            "categoria_sugerida": categoria,
            "subcategoria_sugerida": subcategoria,
            "origen": "Email",
            "tarjeta": m_tarjeta.group(1) if m_tarjeta else None,
            "ref": m_ref.group(1) if m_ref else None,
        })
    return pd.DataFrame(filas)


def _es_email_bbva(texto: str) -> bool:
    return "Establecimiento:" in texto and "Fecha de la operaci" in texto


# ─── Extracto Tarjeta de Crédito CMR (Banco Falabella) ───────────────────────
# El PDF simula negrita duplicando cada carácter (ej. "NNúúmmeerroo" en vez de
# "Número"). Se normaliza antes de aplicar las expresiones regulares.

_DOBLE_CARACTER = re.compile(r"(?:(.)\1){2,}")


def _normalizar_doble(texto: str) -> str:
    return _DOBLE_CARACTER.sub(lambda m: m.group(0)[0::2], texto)


def _es_falabella(texto: str) -> bool:
    return "Tarjeta de Crédito CMR" in texto or "Banco Falabella" in texto


_LINEA_FALABELLA = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+[TA]{1,2}\s+(-?\$[\d.,]+)", re.MULTILINE
)

# Movimientos que son pagos/abonos a la propia tarjeta (no gasto nuevo —
# ya se ve reflejado como salida de dinero en la cuenta desde la que se pagó).
_FALABELLA_IGNORAR_PREFIJOS = ("PAGO TARJETA CMR",)


def parsear_falabella(file) -> pd.DataFrame:
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)
    texto_norm = _normalizar_doble(texto_completo)

    filas = []
    for m in _LINEA_FALABELLA.finditer(texto_norm):
        fecha_str, descripcion, monto_str = m.groups()
        descripcion = descripcion.strip()
        if descripcion.upper().startswith(_FALABELLA_IGNORAR_PREFIJOS):
            continue

        fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        monto = abs(_parsear_monto_es(monto_str))

        categoria, subcategoria = sugerir_categoria(descripcion, "gasto")
        if categoria is None:
            desc_up = descripcion.upper()
            if "SEGURO VIDA" in desc_up:
                categoria, subcategoria = "🛡️ Seguro", "Otro"
            elif "CUOTA MANEJO" in desc_up:
                categoria, subcategoria = "💳 Préstamos", "Tarjeta Falabella"

        filas.append({
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": monto,
            "tipo": "gasto",
            "categoria_sugerida": categoria,
            "subcategoria_sugerida": subcategoria,
            "origen": "Falabella PDF",
        })
    return pd.DataFrame(filas)


# ─── Extracto Tarjeta de Crédito Alkosto (Tuya) ──────────────────────────────

def _es_alkosto(texto: str) -> bool:
    return "Tuya" in texto and "Tarjeta de Crédito" in texto


_LINEA_ALKOSTO = re.compile(
    r"^(\d{4}/\d{2}/\d{2})\s+([+-])(.+?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+"
    r"[\d.,]+%\s+[\d.,]+%\s+\d+/(\d+)\s*$",
    re.MULTILINE,
)


def parsear_alkosto(file) -> pd.DataFrame:
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    filas = []
    for m in _LINEA_ALKOSTO.finditer(texto_completo):
        fecha_str, signo, descripcion, valor_transaccion, _saldo, cuota_mes, total_cuotas = m.groups()
        if signo == "-":
            continue  # pago o reverso, no es gasto nuevo

        fecha = datetime.strptime(fecha_str, "%Y/%m/%d").date()
        descripcion = descripcion.strip()
        if "|" in descripcion:
            descripcion = descripcion.split("|", 1)[1].strip()

        # Compras a cuotas: lo que corresponde pagar este período.
        # Cargos de una sola vez (cuota de manejo, seguro, 0/0): el valor total.
        monto = _parsear_monto_es(cuota_mes) if int(total_cuotas) > 0 else _parsear_monto_es(valor_transaccion)
        monto = abs(monto)

        categoria, subcategoria = sugerir_categoria(descripcion, "gasto")
        if categoria is None:
            desc_up = descripcion.upper()
            if "SEG DEUD" in desc_up:
                categoria, subcategoria = "🛡️ Seguro", "Otro"
            elif "CUOTA DE MANEJO" in desc_up:
                categoria, subcategoria = "💳 Préstamos", "Tarjeta Alkosto"

        filas.append({
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": monto,
            "tipo": "gasto",
            "categoria_sugerida": categoria,
            "subcategoria_sugerida": subcategoria,
            "origen": "Alkosto PDF",
        })
    return pd.DataFrame(filas)


# ─── Extracto Cuenta de Ahorros Banco de Bogotá (PDF con contraseña) ────────
# El PDF viene protegido con contraseña (normalmente la cédula del titular).
# Cada movimiento empieza con "DD/MM CODIGO ..." y puede continuar en una
# segunda línea sin fecha (el texto se corta a mitad de palabra al envolver).

_BOGOTA_INICIO_BLOQUE = re.compile(r"^(\d{2}/\d{2})\s+[A-Z0-9]{3,6}\s+", re.MULTILINE)
_BOGOTA_MONTO = re.compile(r"-?[\d,]+\.\d{2}")
_BOGOTA_RUIDO = re.compile(
    r"\b(Tarj\s*#.*|efectuad[oa]\s+el\s+\d{8}.*|efectuad[oa]\s+el\s+\d{2}/\d{2}/\d{4}\.?.*)",
    re.IGNORECASE | re.DOTALL,
)


def _es_banco_bogota(texto: str) -> bool:
    return "Extracto Cuenta Ahorros" in texto or "Extracto Cuenta Corriente" in texto


def parsear_banco_bogota(file, password: str) -> pd.DataFrame:
    with pdfplumber.open(file, password=password) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # pdfplumber a veces funde la línea "Tarj # xxxxxx******xxxx" del final de
    # un movimiento con el inicio del siguiente ("DD/MM CODIGO ...") en una
    # sola línea de texto sin salto — eso hace que el siguiente movimiento
    # quede invisible para el regex de inicio de bloque (ancla ^). Se separa
    # a la fuerza antes de partir en bloques.
    for patron_cierre in (
        r"(\d{6}\*{6}\d{4})",            # línea "Tarj # xxxxxx******xxxx"
        r"(efectuad[oa]\s+el\s+\d{8})",  # cierre sin tarjeta (ej. Pago PSE)
        r"([\d,]+\.\d{2})",              # cierre que termina directo en el saldo (ej. Intereses ganados)
    ):
        texto_completo = re.sub(
            patron_cierre + r"\s+(\d{2}/\d{2}\s+[A-Z0-9]{3,6}\s)",
            r"\1\n\2",
            texto_completo,
        )

    m_anio = re.search(r"FECHA EXTRACTO.*?(\d{4})", texto_completo)
    anio = int(m_anio.group(1)) if m_anio else datetime.now().year

    posiciones = [m.start() for m in _BOGOTA_INICIO_BLOQUE.finditer(texto_completo)]
    fechas_raw = [m.group(1) for m in _BOGOTA_INICIO_BLOQUE.finditer(texto_completo)]

    filas = []
    for i, pos in enumerate(posiciones):
        fin = posiciones[i + 1] if i + 1 < len(posiciones) else len(texto_completo)
        bloque = texto_completo[pos:fin]

        montos = _BOGOTA_MONTO.findall(bloque)
        if len(montos) < 2:
            continue
        # Este PDF usa formato en-US ("-1,234.00"), a diferencia de los demás
        # extractos que usan es-CO — se parsea directo, sin _parsear_monto_es.
        monto = float(montos[0].replace(",", ""))

        dia, mes = fechas_raw[i].split("/")
        fecha = datetime(anio, int(mes), int(dia)).date()

        descripcion = _BOGOTA_INICIO_BLOQUE.sub("", bloque, count=1)
        descripcion = _BOGOTA_RUIDO.sub("", descripcion)
        for m_str in montos[:2]:
            descripcion = descripcion.replace(m_str, "")
        descripcion = re.sub(r"\s+", " ", descripcion).strip(" .\n")

        tipo = "ingreso" if monto > 0 else "gasto"
        categoria, subcategoria = sugerir_categoria(descripcion, tipo)
        if categoria is None:
            desc_up = descripcion.upper()
            if "BANCO FALABELLA" in desc_up:
                categoria, subcategoria = "💳 Préstamos", "Tarjeta Falabella"
            elif "FINANCIAMIENTO TUYA" in desc_up:
                categoria, subcategoria = "💳 Préstamos", "Tarjeta Alkosto"
            elif "BANCOOMEVA" in desc_up:
                categoria, subcategoria = "💳 Préstamos", "Tarjeta Bancoomeva"

        filas.append({
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": abs(monto),
            "tipo": tipo,
            "categoria_sugerida": categoria,
            "subcategoria_sugerida": subcategoria,
            "origen": "Banco de Bogotá PDF",
        })
    return pd.DataFrame(filas)


class PDFProtegidoError(Exception):
    """El PDF está protegido con contraseña y no se pudo abrir (falta o es incorrecta)."""


def parsear_archivo(file, password: str | None = None) -> pd.DataFrame:
    nombre = file.name.lower()
    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
        return parsear_excel(file)
    if nombre.endswith(".pdf"):
        try:
            with pdfplumber.open(file) as pdf:
                texto_p1 = pdf.pages[0].extract_text() or ""
        except Exception:
            if not password:
                raise PDFProtegidoError(
                    f"'{file.name}' está protegido con contraseña. Ingrésala arriba e inténtalo de nuevo."
                )
            file.seek(0)
            try:
                with pdfplumber.open(file, password=password) as pdf:
                    texto_p1 = pdf.pages[0].extract_text() or ""
            except Exception:
                raise PDFProtegidoError(f"La contraseña no abrió '{file.name}'.")
            if _es_banco_bogota(texto_p1):
                file.seek(0)
                return parsear_banco_bogota(file, password)
            raise ValueError(f"PDF protegido pero no reconocido: {file.name}")

        if _es_email_bbva(texto_p1):
            file.seek(0)
            with pdfplumber.open(file) as pdf:
                texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)
            return parsear_email_texto(texto_completo)
        if _es_falabella(texto_p1):
            file.seek(0)
            return parsear_falabella(file)
        if _es_alkosto(texto_p1):
            file.seek(0)
            return parsear_alkosto(file)
        file.seek(0)
        return parsear_pdf(file)
    raise ValueError(f"Formato no soportado: {file.name}")


# ─── Conexión IMAP (lectura de notificaciones BBVA directo del correo) ───────

REMITENTE_BBVA = "BBVA@bbvanet.com.co"

# Asuntos de correo BBVA que sabemos parsear hoy. BBVA envía muchos otros
# tipos (alertas de inicio de sesión, confirmaciones de ingreso digital, etc.)
# que no son transacciones — filtrarlos aquí evita descargar esos cuerpos.
ASUNTOS_SOPORTADOS = ["Compra Exitosa"]


def _criterio_asuntos(asuntos: list[str]) -> str:
    terminos = [f'SUBJECT "{a}"' for a in asuntos]
    criterio = terminos[-1]
    for t in reversed(terminos[:-1]):
        criterio = f"OR {t} {criterio}"
    return criterio


def _cuerpo_texto(msg: email.message.Message) -> str:
    """Extrae la parte text/plain de un correo; si no existe, limpia el HTML a mano."""
    if msg.is_multipart():
        texto_html = None
        for parte in msg.walk():
            tipo = parte.get_content_type()
            if parte.get_content_disposition() == "attachment":
                continue
            if tipo == "text/plain":
                charset = parte.get_content_charset() or "utf-8"
                return html.unescape(parte.get_payload(decode=True).decode(charset, errors="replace"))
            if tipo == "text/html" and texto_html is None:
                charset = parte.get_content_charset() or "utf-8"
                texto_html = parte.get_payload(decode=True).decode(charset, errors="replace")
        if texto_html:
            return html.unescape(re.sub(r"<[^>]+>", " ", texto_html))
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    return html.unescape(payload.decode(charset, errors="replace")) if payload else ""


def _buscar_correos_imap(
    usuario: str, app_password: str, dias: int, remitente: str,
    criterio_extra: str, extraer_fila,
) -> pd.DataFrame:
    """
    Conecta por IMAP a Gmail, busca correos de `remitente` (+ `criterio_extra`
    opcional, ej. SUBJECT) de los últimos `dias` días, y para cada uno llama
    extraer_fila(msg) -> DataFrame de 0+ filas, o None si el correo no se
    pudo reconocer/parsear (se cuenta como 'no_reconocido').
    """
    desde = (datetime.now() - timedelta(days=dias)).strftime("%d-%b-%Y")

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        imap.login(usuario, app_password)
        imap.select("INBOX", readonly=True)
        query = f'(FROM "{remitente}" SINCE "{desde}"' + (f" {criterio_extra}" if criterio_extra else "") + ")"
        _, datos = imap.search(None, query)
        ids = datos[0].split()

        partes = []
        no_reconocidos = 0
        for msg_id in ids:
            _, msg_datos = imap.fetch(msg_id, "(RFC822)")
            raw = msg_datos[0][1]
            msg = email.message_from_bytes(raw)
            fila = extraer_fila(msg)
            if fila is not None and not fila.empty:
                partes.append(fila)
            else:
                no_reconocidos += 1

        df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
        df.attrs["no_reconocidos"] = no_reconocidos
        df.attrs["total_mensajes"] = len(ids)
        return df
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def buscar_correos_bbva(usuario: str, app_password: str, dias: int = 30) -> pd.DataFrame:
    """
    Busca notificaciones BBVA de 'Compra Exitosa' y las parsea al mismo
    formato normalizado que parsear_archivo().
    """
    def extraer(msg):
        texto = _cuerpo_texto(msg)
        return parsear_email_texto(texto) if _es_email_bbva(texto) else None

    criterio_asunto = _criterio_asuntos(ASUNTOS_SOPORTADOS)
    return _buscar_correos_imap(usuario, app_password, dias, REMITENTE_BBVA, criterio_asunto, extraer)


def _extraer_adjunto_pdf(msg: email.message.Message) -> bytes | None:
    for part in msg.walk():
        nombre = (part.get_filename() or "").lower()
        if part.get_content_disposition() == "attachment" and nombre.endswith(".pdf"):
            return part.get_payload(decode=True)
    return None


# ─── Recibo de pago — citas presenciales Fundación Valle del Lili ───────────

REMITENTE_FVL = "pagosonline@fvl.org.co"
ASUNTO_FVL = "Recibo de pago cita presencial"
_FVL_FECHA = re.compile(r"\d{2}/\d{2}/\d{4}")
_FVL_VALOR = re.compile(r"Pago PSE\s+([\d.,]+)\s+COP")


def parsear_recibo_fvl(pdf_bytes: bytes) -> pd.DataFrame | None:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = pdf.pages[0].extract_text() or ""
    m_fecha = _FVL_FECHA.search(texto)
    m_valor = _FVL_VALOR.search(texto)
    if not (m_fecha and m_valor):
        return None
    fecha = datetime.strptime(m_fecha.group(0), "%d/%m/%Y").date()
    monto = _parsear_monto_es("$" + m_valor.group(1))
    return pd.DataFrame([{
        "fecha": fecha,
        "descripcion": "Fundación Valle del Lili - cita presencial",
        "monto": monto,
        "tipo": "gasto",
        "categoria_sugerida": "💆 Cuidado Personal",
        "subcategoria_sugerida": "Médicos / Salud",
        "origen": "FVL Email PDF",
    }])


def buscar_correos_fvl(usuario: str, app_password: str, dias: int = 365) -> pd.DataFrame:
    def extraer(msg):
        pdf_bytes = _extraer_adjunto_pdf(msg)
        return parsear_recibo_fvl(pdf_bytes) if pdf_bytes else None

    return _buscar_correos_imap(usuario, app_password, dias, REMITENTE_FVL, f'SUBJECT "{ASUNTO_FVL}"', extraer)


# ─── Recibo de cobro — Póliza de Salud SURA ──────────────────────────────────

REMITENTE_SURA = "suracomunicaciones@sura.com.co"
ASUNTO_SURA = "Recibo de cobro"
_SURA_PERIODO = re.compile(r"Hasta:\s*(\d{4}-\d{2}-\d{2})")
_SURA_TOTAL = re.compile(r"Total a pagar\s*\$?\s*([\d.,]+)")


def parsear_recibo_sura(pdf_bytes: bytes) -> pd.DataFrame | None:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = pdf.pages[0].extract_text() or ""
    m_periodo = _SURA_PERIODO.search(texto)
    m_total = _SURA_TOTAL.search(texto)
    if not (m_periodo and m_total):
        return None
    fecha = datetime.strptime(m_periodo.group(1), "%Y-%m-%d").date()
    monto = _parsear_monto_es("$" + m_total.group(1))
    return pd.DataFrame([{
        "fecha": fecha,
        "descripcion": "SURA - Póliza Salud (Plan Salud Evoluciona Familiar)",
        "monto": monto,
        "tipo": "gasto",
        "categoria_sugerida": "🛡️ Seguro",
        "subcategoria_sugerida": "Sura Póliza Salud",
        "origen": "SURA Email PDF",
    }])


def buscar_correos_sura(usuario: str, app_password: str, dias: int = 365) -> pd.DataFrame:
    def extraer(msg):
        pdf_bytes = _extraer_adjunto_pdf(msg)
        return parsear_recibo_sura(pdf_bytes) if pdf_bytes else None

    return _buscar_correos_imap(usuario, app_password, dias, REMITENTE_SURA, f'SUBJECT "{ASUNTO_SURA}"', extraer)
