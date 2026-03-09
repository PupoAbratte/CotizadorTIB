# llm_parser.py — Parser inteligente de briefs usando Google Gemini
# Complementa brief_parser.py (keywords). Se usa cuando hay API key configurada.

import json
from typing import Dict, Any, Optional

import requests

GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """Sos un experto en branding y comunicación que trabaja para un estudio llamado This is Bravo.
Tu tarea es analizar un brief de cliente y determinar qué módulos de servicio aplican y en qué nivel.

Los módulos disponibles son:

**A — Research (investigación)**
- Benchmark (peso 1.0): análisis competitivo, comparativas, referentes del sector.
- Auditoría (peso 1.5): diagnóstico del estado actual de la marca, consistencia, touchpoints, brechas.
- Insights (peso 2.143): research de categoría, tendencias, audiencias, segmentación, entrevistas, social listening.

**B — Brand DNA (estrategia de marca)**
- Lite (peso 0.65): estrategia básica, propósito y personalidad mínima, síntesis accionable.
- Full (peso 1.0): propósito, valores, territorios, posicionamiento, concepto de marca, arquetipo, storytelling.

**C — Creación (identidad visual)**
- Refresh (peso 0.5): ajuste menor del logo, modernizar colores/tipografía, retocar.
- Rebranding (peso 0.8): rediseño significativo de logo/identidad sin cambiar nombre, restyling, modernización.
- Full (peso 1.0): creación nueva de logo + sistema visual completo.
- Nota sobre naming: si el brief pide crear un nombre, indicar has_naming=true (es un addon sobre C).

**D — Brandbook (manual de marca)**
- Lite (peso 0.6): manual básico, paleta + tipografías + usos correctos/incorrectos.
- Full (peso 1.0): manual completo, aplicaciones de marca, recursos gráficos, lineamientos digitales e impresos.

**E — Implementación/Producción**
- Lite / Kit básico (peso 0.6): hasta 3 piezas/adaptaciones digitales.
- Full / Kit full (peso 1.0): hasta 5 piezas digitales/impresas + brochure o presentación.
- Plus / Campaña lanzamiento (peso 1.5): concepto de campaña + hasta 15 piezas + coordinación de rollout.

REGLAS:
1. Solo activá un módulo si el brief lo menciona o lo implica claramente.
2. Si el brief niega explícitamente algo ("sin research", "no hacer naming", "no cambiar el logo"), NO actives ese módulo.
3. Si hay ambigüedad en el nivel, elegí el más conservador.
4. Siempre justificá cada decisión brevemente.

Respondé ÚNICAMENTE con un JSON válido (sin markdown, sin backticks, sin texto adicional) con esta estructura exacta:

{
  "modulos_pesos": {
    "A": 0.0,
    "B": 0.0,
    "C": 0.0,
    "D": 0.0,
    "E": 0.0
  },
  "has_naming": false,
  "reasons": ["razón para cada módulo activado o descartado"]
}

Solo incluí en modulos_pesos los módulos con peso > 0.
"""


def parse_brief_with_llm(
    brief: str,
    api_key: str,
    *,
    model: str = GEMINI_MODEL,
    timeout: int = 20,
) -> Optional[Dict[str, Any]]:
    """
    Envía el brief a Gemini y devuelve el JSON parseado.
    Retorna None si falla (la app debe usar el parser por keywords como fallback).
    """
    if not brief or not brief.strip():
        return None

    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\n--- BRIEF DEL CLIENTE ---\n{brief.strip()}\n--- FIN DEL BRIEF ---"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if not resp.ok:
            return None

        data = resp.json()

        # Extraer texto de la respuesta
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text:
            return None

        # Limpiar posibles backticks de markdown
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        result = json.loads(text)

        # Validar estructura mínima
        if "modulos_pesos" not in result:
            return None

        # Filtrar módulos con peso 0
        result["modulos_pesos"] = {
            k: v for k, v in result["modulos_pesos"].items()
            if isinstance(v, (int, float)) and v > 0
        }

        # Asegurar que reasons exista
        if "reasons" not in result:
            result["reasons"] = []

        # Asegurar que has_naming exista
        if "has_naming" not in result:
            result["has_naming"] = False

        return result

    except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
        return None
