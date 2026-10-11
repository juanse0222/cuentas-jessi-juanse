"""
Asesor financiero con IA — envía un resumen del presupuesto/gastos del mes
actual a Claude y devuelve observaciones y sugerencias en texto plano.

No es asesoría de inversión con licencia — solo observaciones de presupuesto
y gasto, explícitamente enmarcadas así en el prompt del sistema.
"""

from __future__ import annotations

import anthropic

MODELO = "claude-opus-5"

SYSTEM_PROMPT = """Eres un asistente de presupuesto familiar para una pareja colombiana \
(Jessi y Juanse) que usan una app de control financiero. Te paso un resumen de su \
presupuesto y gasto real del mes.

Da observaciones concretas y accionables en español, en un tono directo y cercano, no \
corporativo. Señala específicamente:
- Categorías que se están pasando del presupuesto o están cerca del límite
- Si el saldo del mes es positivo o negativo y qué tan urgente es
- Patrones que valga la pena vigilar (gastos grandes puntuales, categorías crecientes)
- 2-3 sugerencias concretas y realistas, no genéricas

No eres un asesor financiero con licencia — no dés recomendaciones de inversión, \
impuestos, ni asesoría legal. Si algo requiere eso, dilo explícitamente y sugiere \
consultar a un profesional. Responde en texto plano, sin markdown pesado, máximo \
unos 300-400 palabras."""


def analizar_mes(resumen: dict, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    mensaje = client.messages.create(
        model=MODELO,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _resumen_a_texto(resumen)}],
    )
    bloques_texto = [b.text for b in mensaje.content if b.type == "text"]
    return "\n".join(bloques_texto).strip()


def _resumen_a_texto(r: dict) -> str:
    lineas = [
        f"Mes: {r['mes_nombre']} {r['anio']}",
        f"Ingresos previstos: ${r['ingresos_previstos']:,.0f}",
        f"Total gastado: ${r['gastos_totales']:,.0f}",
        f"Saldo disponible: ${r['saldo']:,.0f}",
        "",
        "Gasto por categoría (presupuestado vs real):",
    ]
    for c in r["categorias"]:
        lineas.append(
            f"- {c['categoria']}: ${c['gastado']:,.0f} de ${c['presupuestado']:,.0f} "
            f"({c['pct']:.0f}%)"
        )

    if r.get("top_gastos"):
        lineas.append("")
        lineas.append("Gastos individuales más grandes del mes:")
        for g in r["top_gastos"]:
            lineas.append(f"- {g['fecha']}: {g['concepto']} ({g['categoria']}) — ${g['monto']:,.0f}")

    return "\n".join(lineas)
