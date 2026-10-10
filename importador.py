"""
Parseo de extractos BBVA (PDF de cuenta y Excel de movimientos) hacia
un formato normalizado listo para revisar e importar como transacciones.
"""

from __future__ import annotations

import re
from datetime import datetime

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
    ("DROG ", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CRUZ VERDE", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CENTRO MEDICO", "💆 Cuidado Personal", "Médicos / Salud"),
    ("CLINICA", "💆 Cuidado Personal", "Médicos / Salud"),
    ("IPS SALUD", "💆 Cuidado Personal", "Médicos / Salud"),
    ("IMBANACO", "💆 Cuidado Personal", "Médicos / Salud"),
    ("KRIKA BEAUTY", "💆 Cuidado Personal", "Pelo y uñas Jessi"),

    # Préstamos / tarjetas de crédito
    ("BANCOOMEVA", "💳 Préstamos", "Tarjeta Bancoomeva"),
    ("ALKOSTO", "💳 Préstamos", "Tarjeta Alkosto"),
    ("FALABELLA", "💳 Préstamos", "Tarjeta Falabella"),

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


def parsear_archivo(file) -> pd.DataFrame:
    nombre = file.name.lower()
    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
        return parsear_excel(file)
    if nombre.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            texto_p1 = pdf.pages[0].extract_text() or ""
        if _es_email_bbva(texto_p1):
            file.seek(0)
            with pdfplumber.open(file) as pdf:
                texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)
            return parsear_email_texto(texto_completo)
        file.seek(0)
        return parsear_pdf(file)
    raise ValueError(f"Formato no soportado: {file.name}")
