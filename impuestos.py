"""
Resumen de Declaración de Renta (Formulario 210 DIAN) — extrae cifras clave
desde posiciones conocidas del formulario.

El formulario de la DIAN imprime las etiquetas de cada casilla (29, 30, 31,
111, 129...) como parte de una plantilla/imagen de fondo, no como texto real
— pdfplumber solo puede leer los NÚMEROS que el contribuyente diligenció, sin
sus etiquetas. Por eso la extracción es por posición (x0, top) calibrada
contra un Formulario 210 real (año gravable 2024), no por buscar el texto de
la etiqueta. Si la DIAN cambia el layout del formulario en años futuros, esto
debe recalibrarse contra un PDF real nuevo del formulario que cambie.
"""

from __future__ import annotations

import re

import pdfplumber

# (nombre, x0 esperado, top esperado, tolerancia_x, tolerancia_top)
_CASILLAS = [
    ("patrimonio_bruto", 208, 192, 20, 6),
    ("deudas", 367, 192, 20, 6),
    ("patrimonio_liquido", 550, 192, 25, 6),
    ("renta_liquida_gravable", 271, 588, 25, 6),
    ("impuesto_a_cargo", 554, 576, 20, 6),
    ("retenciones", 554, 612, 20, 6),
    ("saldo_a_pagar", 415, 648, 20, 6),
    ("saldo_a_favor", 586, 648, 20, 6),
]


def _es_formulario_210(texto: str) -> bool:
    # El título "Declaración de renta..." es parte de la plantilla/imagen de
    # fondo del PDF de la DIAN, no texto real — solo "PRIVADA" sí lo es.
    return "PRIVADA" in texto


def _buscar_valor(palabras, x0_esp, top_esp, tol_x, tol_top) -> float | None:
    candidatos = [
        w for w in palabras
        if abs(w["x0"] - x0_esp) <= tol_x and abs(w["top"] - top_esp) <= tol_top
        and re.fullmatch(r"-?[\d,]+", w["text"])
    ]
    if not candidatos:
        return None
    texto = candidatos[0]["text"].replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None


def _extraer_anio(palabras) -> int | None:
    # Casilla "1. Año": se imprime como 4 dígitos sueltos (ej. "2" "0" "2" "4")
    # muy arriba de la página, no como un solo token "2024".
    digitos = sorted(
        (w for w in palabras if w["top"] < 70 and re.fullmatch(r"\d", w["text"])),
        key=lambda w: w["x0"],
    )
    if len(digitos) < 4:
        return None
    anio_str = "".join(w["text"] for w in digitos[:4])
    return int(anio_str) if anio_str.isdigit() else None


def parsear_declaracion_renta(file) -> dict | None:
    with pdfplumber.open(file) as pdf:
        page = pdf.pages[0]
        texto = page.extract_text() or ""
        if not _es_formulario_210(texto):
            return None

        palabras = page.extract_words()
        resultado = {"anio": _extraer_anio(palabras)}
        for nombre, x0, top, tol_x, tol_top in _CASILLAS:
            resultado[nombre] = _buscar_valor(palabras, x0, top, tol_x, tol_top)

        # Algunos documentos relacionados (ej. el recibo de pago) también
        # contienen "PRIVADA" y pasan la detección inicial, pero no tienen el
        # layout del formulario completo — si las cifras clave no se pudieron
        # ubicar, no es el Formulario 210 real.
        campos_clave = ("patrimonio_liquido", "impuesto_a_cargo", "renta_liquida_gravable")
        if resultado["anio"] is None or any(resultado[c] is None for c in campos_clave):
            return None
        return resultado


def parsear_declaraciones(archivos) -> list[dict]:
    """Parsea varios PDFs y devuelve solo los que sí son Formulario 210, uno por año."""
    resultados = []
    for f in archivos:
        try:
            r = parsear_declaracion_renta(f)
        except Exception:
            r = None
        if r and r.get("anio"):
            resultados.append(r)
    resultados.sort(key=lambda r: r["anio"])
    return resultados
