# brief_parser.py — versión unificada y optimizada para producción
# Mantiene compatibilidad con detect_module_weights(...) y debug_parse(...)

import re
import unicodedata
from typing import Dict, Any, List, Optional

# Biblioteca consolidada de entregables por módulo (A–E) y nivel
# A: Research | B: Brand DNA | C: Creación | D: Brandbook | E: Implementación

DELIVERABLES = {
    "A": {  # Research (no acumulativo)
        "lite": [
            "Análisis de tu competencia (entre 3 y 5 marcas del sector)",
            "Matriz comparativa: propuesta de valor, mensajes clave, estilo de comunicación y códigos visuales",
            "Mapa de posicionamiento y oportunidades de diferenciación",
        ],
        "full": [
            "Diagnóstico del estado actual de tu marca",
            "Determinación de hallazgos clave",
            "Identificación de brechas marcarias y/o comunicacionales",
            "Recomendaciones accionables a corto, mediano y/o largo plazo",
            "Análisis comparativo con 2-4 marcas del sector",
        ],
        "plus": [
            "Research de categoría e industria (contexto competitivo y drivers)",
            "Análisis de tendencias relevantes y su impacto",
            "Definición de audiencias de interés",
            "Definición de territorios estratégicos y criterios para posicionamiento y mensajes",
        ],
    },

    "B": {  # Brand DNA (acumulativo)
        "lite": [
            "Definición de los aspectos esenciales de la personalidad de marca",
            "Promesa de valor central",
        ],
        "full": [
            "Propósito, valores y principios que guían la marca",
            "Territorios y posicionamiento estratégico",
            "Concepto de marca",
        ],
        "plus": [
            "Tono de voz, arquetipo y manifiesto de marca",
            "Desarrollo de los pilares narrativos de la marca",
        ],
    },

    "C": {  # Creación (acumulativo; quitamos naming de Lite como pediste)
        "lite": [
            "Definición del enfoque creativo",
            "Exploración visual inicial",
            "Desarrollo de 2 (dos) caminos conceptuales",
        ],
        "full": [
            "Diseño de isologotipo",
            "Desarrollo del sistema visual completo",
        ],
        "full + naming": [
            "Creación de naming",
            "Diseño de isologotipo",
            "Desarrollo del sistema visual completo",
        ],
        "plus": [
            "Desarrollo de arquitectura visual para subproductos o submarcas",
        ],
    },

    "D": {  # Brandbook (NO acumulativo)
        "lite": [
            "Sistema visual básico: isologotipo, paleta de color y tipografías",
            "Manual de marca breve con lineamientos esenciales",
            "Usos correctos / incorrectos (do’s & don’ts)",
        ],
        "full": [
            "Manual de marca completo",
            "Desarrollo de hasta 5 (cinco) aplicaciones de marca",
            "Desarrollo de recursos gráficos y visuales complementarios",
            "Lineamientos claros para aplicaciones digitales e impresas",
            "2 (dos) sesiones mentoría de marca para equipos internos (60 minutos cada una)",
        ],
        "plus": [
            "Manual de marca avanzado con templates editables",
            "Desarrollo de hasta 10 (diez) aplicaciones de marca",
            "Sistema visual complementario (íconos, tramas, recursos gráficos)",
            "Lineamientos de motion branding (animación de logo, transiciones, uso digital)",
            "Criterios para nuevas piezas, formatos y adaptaciones futuras",
            "4 (cuatro) sesiones de mentoría de marca para equipos internos (60 minutos cada una)",
        ],
    },

    "E": {  # Producción (no acumulativo)
        "Kit básico": [
            "Kit con hasta 3 (tres) adaptaciones digitales de marca (presentaciones, documentos, templates RRSS, firmas de correo, etc.)",
            "Ajustes técnicos de archivos para uso correcto",
        ],
        "Kit full": [
            "Kit con hasta 5 (cinco) adaptaciones digitales y/o impresas de marca",
            "Diseño y diagramación de brochure o presentación comercial (hasta 10 páginas, no incluye redacción de contenido)",
            "Supervisión creativa de producción y adaptación de piezas",
        ],
        "Campaña lanzamiento": [
            "Desarrollo de concepto de campaña",
            "Redacción y diseño de hasta 15 (quince) piezas digitales estáticas",
            "Coordinación creativa del rollout",
            "Kit de marca para facilitar la implementación por equipos internos",
        ],
    },
}

# ============================================================================
# ENTREGABLES: RESOLUCIÓN POR MÓDULO Y NIVEL (para PDF)
# ============================================================================

def _stable_unique(items: List[str]) -> List[str]:
    """Deduplicación estable por string EXACTO, preservando el primer orden."""
    seen = set()
    out: List[str] = []
    for s in items:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def get_deliverables(
    module_key: str,
    level_key: str,
    *,
    c_base_level: Optional[str] = None
) -> List[str]:
    """
    Devuelve la lista final de entregables a imprimir en el PDF.

    Reglas:
    - A: NO acumulativo ("lite"/"full"/"plus" => solo ese nivel)
    - B: acumulativo (lite+full / lite+full+plus)
    - C: acumulativo con variante "full + naming"
         - "full" => lite + full
         - "full + naming" => lite + (full + naming)  [NO suma full aparte]
         - "plus" => lite + (base full o full + naming) + plus
           base se pasa por c_base_level; si no viene, default "full"
    - D: NO acumulativo
    - E: NO acumulativo (niveles: "Kit básico"/"Kit full"/"Campaña lanzamiento")

    Dedup: stable unique por string exacto (por si se suma algo accidentalmente).
    """
    if module_key not in DELIVERABLES:
        raise KeyError(f"Módulo inválido: {module_key}")

    mod = DELIVERABLES[module_key]

    # A: no acumulativo
    if module_key == "A":
        if level_key not in mod:
            raise KeyError(f"Nivel inválido para A: {level_key}")
        return _stable_unique(list(mod[level_key]))

    # D: no acumulativo
    if module_key == "D":
        if level_key not in mod:
            raise KeyError(f"Nivel inválido para D: {level_key}")
        return _stable_unique(list(mod[level_key]))

    # E: no acumulativo (keys con nombres)
    if module_key == "E":
        if level_key not in mod:
            raise KeyError(f"Nivel inválido para E: {level_key}")
        return _stable_unique(list(mod[level_key]))

    # B: acumulativo
    if module_key == "B":
        if level_key not in ("lite", "full", "plus"):
            raise KeyError(f"Nivel inválido para B: {level_key}")
        if level_key == "lite":
            items = mod["lite"]
        elif level_key == "full":
            items = mod["lite"] + mod["full"]
        else:  # plus
            items = mod["lite"] + mod["full"] + mod["plus"]
        return _stable_unique(items)

    # C: acumulativo + naming
    if module_key == "C":
        if level_key not in ("lite", "full", "full + naming", "plus"):
            raise KeyError(f"Nivel inválido para C: {level_key}")

        if level_key == "lite":
            items = mod["lite"]

        elif level_key == "full":
            items = mod["lite"] + mod["full"]

        elif level_key == "full + naming":
            items = mod["lite"] + mod["full + naming"]

        else:  # plus
            base = c_base_level or "full"
            if base not in ("full", "full + naming"):
                raise KeyError(f"c_base_level inválido para C plus: {base}")
            base_items = mod["full"] if base == "full" else mod["full + naming"]
            items = mod["lite"] + base_items + mod["plus"]

        return _stable_unique(items)

    # Por completitud (no debería llegar)
    raise RuntimeError(f"Módulo no soportado: {module_key}")

# ============================================================================
# NORMALIZACIÓN Y UTILIDADES BASE
# ============================================================================

def _normalize(txt: Any) -> str:
    """Lower, sin tildes, espacios colapsados; tolerante a None."""
    if not isinstance(txt, str):
        txt = str(txt or "")
    nfd = unicodedata.normalize("NFD", txt)
    s = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s.lower()).strip()
    return s


def _negated_present(text: str, kw: str, window: int = 4) -> bool:
    """
    Detecta si una keyword está negada dentro de una ventana de palabras.
    Negadores: sin, no, sin necesidad de, excluir, excepto, omitir.
    """
    parts = kw.split()
    head = re.escape(parts[-1])
    pattern = rf"\b(sin|no|sin\s+necesidad\s+de|excluir|excepto|omitir)\s+(?:\w+\s+){{0,{window}}}{head}\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _has_keyword(text: str, kw: str) -> bool:
    return (kw in text) and (not _negated_present(text, kw))


def _any_keyword(text: str, kws: List[str]) -> bool:
    return any(_has_keyword(text, kw) for kw in kws)


def _add_reason(reasons: List[str], msg: str) -> None:
    if msg not in reasons:
        reasons.append(msg)


def _count_pattern_matches(text: str, patterns: List[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


# ============================================================================
# KEYWORDS / PATRONES POR MÓDULO
# ============================================================================

# A: Research — 3 niveles evolutivos
A_INSIGHTS_WEIGHT = 1500.0 / 700.0  # = 2.142857... (para mapear a A_insights en pricing.py)

PATTERNS_A_BENCHMARK = [
    r"\b(benchmark|comparativ[oa]s?|comparacion|comparación)\b",
    r"\b(competencia|competidores?|competitivo)\b",
    r"\b(matriz\s+comparativa|mapa\s+competitivo|referentes)\b",
]

PATTERNS_A_AUDIT = [
    r"\b(auditoria|auditoría|diagnostico|diagnóstico|evaluacion|evaluación)\b",
    r"\b(brand\s+audit|auditoria\s+de\s+marca|auditoría\s+de\s+marca|revision\s+de\s+marca|revisión\s+de\s+marca|estado\s+actual)\b",
    r"\b(consistencia|coherencia|arquitectura\s+de\s+marca|alineacion|alineación)\b",
    r"\b(activos\s+de\s+marca|puntos?\s+de\s+contacto|touchpoints?)\b",
]

PATTERNS_A_INSIGHTS_STRONG = [
    r"\b(audiencia|audiencias|usuarios?|segmentacion|segmentación|buyer\s+persona|personas|target|jtbd|jobs?\s+to\s+be\s+done)\b",
    r"\b(desk\s*research|market\s*research|investigacion\s+de\s+mercado|investigación\s+de\s+mercado)\b",
    r"\b(tendencias|trends?)\b",
    r"\b(social\s+listening|escucha\s+social|sentimiento|sentiment)\b",
    r"\b(insights?)\b",
    r"\b(entrevistas?|encuestas?|focus\s+group|grupos?\s+focal(es)?|panel)\b",
    r"\b(cuantitativ[oa]|cualitativ[oa])\b",
]

PATTERNS_A_INSIGHTS_WEAK = [
    r"\b(industria|categoria|categoría|mercado|market)\b"
    # 'sector' NO va: es demasiado común en benchmark.
]

PATTERNS_A_GENERIC = [
    r"\b(research|investigacion|investigación)\b",
]

# B: Brand DNA — lite (0.65) vs full (1.0)
PATTERNS_B_FULL = [
    r"\b(brand\s+dna|adn(\s+de\s+marca)?)\s*(completo|full|detallado|profundo|integral)?\b",
    r"\b(territorios?\s+de\s+marca|arquetipo)\b",
    r"\b(storytelling|narrativa\s+(de\s+marca|profunda))\b",
    r"\b(estrategia\s+(completa|profunda|integral|de\s+marca\s+completa))\b",
    r"\b(manifiesto\s+(completo|detallado|de\s+marca))\b",
    r"\b(valores\s+y\s+principios|personalidad\s+de\s+marca)\b",
    r"\b(insight\s+del\s+consumidor|concepto\s+de\s+marca)\b",
    r"\b(proposito\s+y\s+valores|propósito\s+y\s+valores|dna\s+estrategico|dna\s+estratégico)\b",
]
KW_B_LITE_HINTS = [
    "adn lite", "estrategia basica", "estrategia básica", "adn basico", "adn básico",
    "proposito y personalidad", "propósito y personalidad",
    "manifiesto simple", "resumen accionable", "resumen accionable",
    "sintesis", "síntesis", "enfoque sintesis", "enfoque síntesis",
    "estrategia rapida", "estrategia rápida", "adn de marca basico", "adn de marca básico",
    "brand dna basico", "brand dna básico",
]

# C: Creación — refresh (0.5) / rebranding (0.8) / full (1.0)
PATTERNS_C_REFRESH = [
    r"\b(refresh|refresco)\b",
    r"\b(actualizacion|actualización|puesta\s+a\s+punto)\b",
    r"\b(ajuste(s)?\s+(menor(es)?|minimo(s)?|puntual(es)?))\b",
    r"\b(retocar|pulir|optimizar|simplificar|refinar)\b",
    r"\b(ajuste(s)?\s+de\s+logo|ajuste(s)?\s+de\s+logotipo)\b",
]
PATTERNS_C_REBRAND = [
    r"\b(rebranding|re-branding|rebrand)\b",
    r"\b(restyling)\b",
    r"\b(redise[nñ]o|rediseno|redesign)\b",
    r"\b(redise[nñ]o\s+de\s+logo|rediseno\s+de\s+logo|redesign\s+de\s+logo)\b",
    r"\b(rediseno\s+total|cambio\s+de\s+identidad)\b",
    r"\b(transformacion|transformación)\s+de\s+marca\b",
    r"\b(nueva\s+marca)\b",
    r"\b(modernizacion|modernización)\b",
]
PATTERNS_C_FULL = [
    r"\b(identidad\s+(completa|full|integral))\b",
    r"\b(logo\s+([ye+]|y)\s+(naming|identidad))\b",
    r"\b(naming\s+([ye+]|y)\s+logo)\b",
    r"\b(sistema\s+visual\s+completo)\b",
]

# Naming SOLO si es explícito (sin "claim/tagline/slogan")
PATTERNS_C_NAMING = [
    r"\b(naming|brand\s+name)\b",
    r"\b(crear|creacion|creación|definir|definicion|definición|desarrollar|desarrollo)\s+(un\s+)?nombre\b",
    r"\b(nombre\s+(de\s+marca|comercial|para\s+la\s+marca))\b",
    r"\b(denominacion|denominación)\b",
    r"\b(bautizar|bautizo)\b",
    r"\b(renombrar|cambio\s+de\s+nombre|nuevo\s+nombre)\b",
    r"\b(re\s*-\s*naming|re\s*naming)\b",
]

PATTERNS_C_LOGO = [r"\b(logo|logotipo|isologo|imagotipo|isologotipo|simbolo|símbolo)\b"]
PATTERNS_C_CONCEPTO = [r"\b(concepto\s+creativo|territorio\s+creativo)\b"]

# D: Brandbook — lite (0.6) / full (1.0)
# Importante: NO usamos "sistema visual" como señal de D (se cruza con C).
PATTERNS_D_FULL = [
    r"\b(manual\s+(completo|full|detallado|extenso|avanzado|integral))\b",
    r"\b(brandbook\s+(completo|full|integral))\b",
    r"\b(guia\s+(completa|avanzada|integral)\s+de\s+marca)\b",
    r"\b(manual\s+de\s+(marca|identidad)\s+(completo|full|integral))\b",
    r"\b(arquitectura\s+de\s+marca)\b",
]
PATTERNS_D_LITE = [
    r"\b(manual\s+(lite|basico|básico|simple|reducido|abreviado|rapido|rápido))\b",
    r"\b(brandbook\s+(lite|basico|básico|esencial|simple))\b",
    r"\b(guia\s+(rapida|rápida|basica|básica|simple|esencial)\s+de\s+marca)\b",
    r"\b(mini\s+manual|version\s+simplificada|versión\s+simplificada)\b",
    r"\b(guia\s+de\s+marca\s+(basica|básica|simple|lite))\b",
    r"\b(manual\s+de\s+marca\s+(lite|basico|básico|simple|reducido))\b",
]
# Genérico (pero SOLO con términos inequívocos de Brandbook/Manual)
KW_D_GENERIC = [
    "brandbook",
    "manual de marca",
    "manual de identidad",
    "guia de marca",
    "guía de marca",
    "guia de identidad",
    "guía de identidad",
    "manual",
]

# E: Implementación — lite (0.6) / full (1.0) / plus (1.5)
KW_E_GENERIC = [
    "implementacion", "implementación", "aplicaciones", "piezas", "pack",
    "lanzamiento", "template", "plantilla", "presentacion", "presentación",
    "brochure", "banner", "papeleria", "papelería", "posts", "redes",
    "sitio", "web", "packaging", "evento", "adaptaciones",
    "rrss", "banners",
]
PATTERNS_E_LITE = [
    r"\b(piezas?\s+basicas?|piezas?\s+básicas?|aplicaciones?\s+minimas?|aplicaciones?\s+mínimas?)\b",
    r"\b(pack\s+(pequeno|pequeño|basico|básico|inicial))\b",
    r"\b(adaptaciones?\s+esenciales?)\b",
]
PATTERNS_E_FULL = [
    r"\b(pack\s+(estandar|estándar|medio|completo))\b",
    r"\b(lanzamiento\s+estandar|lanzamiento\s+estándar)\b",
    r"\b(aplicaciones?\s+principales?)\b",
]
PATTERNS_E_PLUS = [
    r"\b(pack\s+(grande|premium|extendido))\b",
    r"\b(campana|campaña|lanzamiento\s+(integral|masivo|completo))\b",
    r"\b(implementacion\s+(completa|extensa)|implementación\s+(completa|extensa))\b",
    r"\b(evento\s+de\s+lanzamiento)\b",
]
RANGO_E_LITE_MAX = 10
RANGO_E_FULL_MAX = 15

# ============================================================================
# DETECCIÓN E (Implementación) CON PARSER NUMÉRICO
# ============================================================================

def _parse_number_expr(text: str) -> Optional[int]:
    t = _normalize(text)
    m = re.search(r"\bentre\s+(\d+)\s+y\s+(\d+)\b", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (a + b) // 2
    m = re.search(r"\bhasta\s+(\d+)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\bmas\s+de\s+(\d+)\b", t)
    if m:
        return int(m.group(1)) + 1
    m = re.search(r"(>=|>|<=|<)\s*(\d+)", t)
    if m:
        op, num = m.group(1), int(m.group(2))
        return num + 1 if op == ">" else num if op in (">=", "<=") else max(0, num - 1)
    m = re.search(r"\b(\d+)\s*(adaptaciones?|piezas?|posts?|banners?|aplicaciones?)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(adaptaciones?|piezas?|posts?|banners?|aplicaciones?)\s*(de|x)?\s*(\d+)\b", t)
    if m and m.lastindex and (m.group(m.lastindex) or "").isdigit():
        return int(m.group(m.lastindex))
    return None


def _detect_impl_weight(text: str, reasons: List[str]) -> float:
    t = _normalize(text)
    qty = _parse_number_expr(t)
    if isinstance(qty, int):
        if qty <= RANGO_E_LITE_MAX:
            _add_reason(reasons, f"E lite: {qty} piezas (≤{RANGO_E_LITE_MAX})")
            return 0.6
        if qty <= RANGO_E_FULL_MAX:
            _add_reason(reasons, f"E full: {qty} piezas ({RANGO_E_LITE_MAX + 1}-{RANGO_E_FULL_MAX})")
            return 1.0
        _add_reason(reasons, f"E plus: {qty} piezas (>{RANGO_E_FULL_MAX})")
        return 1.5

    sp = _count_pattern_matches(t, PATTERNS_E_PLUS)
    sf = _count_pattern_matches(t, PATTERNS_E_FULL)
    sl = _count_pattern_matches(t, PATTERNS_E_LITE)

    if sp > 0:
        _add_reason(reasons, f"E plus: {sp} señales")
        return 1.5
    if sf > 0:
        _add_reason(reasons, f"E full: {sf} señales")
        return 1.0
    if sl > 0:
        _add_reason(reasons, f"E lite: {sl} señales")
        return 0.6
    if any(kw in t for kw in KW_E_GENERIC):
        _add_reason(reasons, "E lite: implementación genérica sin detalle")
        return 0.6
    return 0.0


# ============================================================================
# DETECCIÓN POR MÓDULOS (A–D)
# ============================================================================

def _detect_module_a(raw_text: str, reasons: List[str]) -> float:
    t = _normalize(raw_text)

    # Negación explícita
    if (
        _negated_present(t, "research") or
        _negated_present(t, "investigacion") or
        _negated_present(t, "investigación") or
        _negated_present(t, "benchmark") or
        _negated_present(t, "auditoria") or
        _negated_present(t, "auditoría")
    ):
        _add_reason(reasons, "A: Research negado explícitamente")
        return 0.0

    # Insights: separar señales fuertes vs débiles para evitar falsos positivos
    score_insights_strong = _count_pattern_matches(t, PATTERNS_A_INSIGHTS_STRONG)
    score_insights_weak = _count_pattern_matches(t, PATTERNS_A_INSIGHTS_WEAK)

    score_audit = _count_pattern_matches(t, PATTERNS_A_AUDIT)
    score_bench = _count_pattern_matches(t, PATTERNS_A_BENCHMARK)
    score_generic = _count_pattern_matches(t, PATTERNS_A_GENERIC)

    # Regla: si aparece algo de nivel superior, gana el superior.
    # Insights si hay ≥1 señal fuerte, o si hay ≥2 señales débiles.
    if score_insights_strong >= 1 or score_insights_weak >= 2:
        _add_reason(
            reasons,
            f"A: Research insights (strong={score_insights_strong}, weak={score_insights_weak})"
        )
        return A_INSIGHTS_WEIGHT

    if score_audit >= 1:
        _add_reason(reasons, f"A: Research auditoría ({score_audit} señales)")
        return 1.5

    if score_bench >= 1 or score_generic >= 1:
        s = score_bench + score_generic
        _add_reason(reasons, f"A: Research benchmark ({s} señales)")
        return 1.0

    return 0.0


def _detect_module_b(raw_text: str, reasons: List[str]) -> float:
    t = _normalize(raw_text)
    score_full = _count_pattern_matches(t, PATTERNS_B_FULL)
    score_lite = sum(1 for kw in KW_B_LITE_HINTS if _has_keyword(t, kw))

    if score_lite >= 1:
        _add_reason(reasons, f"B lite: {score_lite} pistas explícitas")
        return 0.65
    if score_full >= 1:
        _add_reason(reasons, f"B full: {score_full} señales")
        return 1.0
    return 0.0


def _detect_module_c(raw_text: str, reasons: List[str]) -> float:
    t = _normalize(raw_text)

    if _negated_present(t, "logo") and _negated_present(t, "identidad"):
        _add_reason(reasons, "C descartado: negación de logo e identidad")
        return 0.0

    sf = _count_pattern_matches(t, PATTERNS_C_FULL)
    srb = _count_pattern_matches(t, PATTERNS_C_REBRAND)
    srf = _count_pattern_matches(t, PATTERNS_C_REFRESH)

    has_naming = _count_pattern_matches(t, PATTERNS_C_NAMING) > 0
    has_logo = _count_pattern_matches(t, PATTERNS_C_LOGO) > 0
    has_concepto = _count_pattern_matches(t, PATTERNS_C_CONCEPTO) > 0

    comps = sum([has_naming, has_logo, has_concepto])

    if sf >= 2 or comps >= 2:
        _add_reason(reasons, f"C full: full={sf}, comps={comps}")
        return 1.0

    if srb >= 1:
        if srf >= 1 and srf >= srb:
            _add_reason(reasons, "C refresh: empate rebranding/refresh (conservador)")
            return 0.5
        _add_reason(reasons, f"C rebranding: {srb} señales")
        return 0.8

    if srf >= 1:
        _add_reason(reasons, f"C refresh: {srf} señales")
        return 0.5

    if has_logo or has_naming:
        # Si hay verbo de cambio (rediseño/restyling/modernizar/actualizar) lo tratamos como rebranding
        if re.search(r"\b(redise[nñ]o|rediseno|restyling|redesign|moderniz(ar|acion)|actualiz(ar|acion))\b", t):
            # Si además está “leve/ajuste menor”, lo bajamos a refresh
            if re.search(r"\b(leve|ligero|menor|minimo|mínimo|puntual|retocar|pulir|ajust(e|es))\b", t):
                _add_reason(reasons, "C refresh: logo con ajuste leve/menor")
                return 0.5
            _add_reason(reasons, "C rebranding: rediseño/restyling/modernización de logo")
            return 0.8

        # Fallback conservador si solo menciona logo sin verbo de cambio
        if re.search(r"\b(ajuste(s)?|puesta\s+a\s+punto)\b", t):
            _add_reason(reasons, "C refresh: componentes con 'ajuste'")
            return 0.5

        _add_reason(reasons, "C full: logo/naming sin calificador")
        return 1.0
    return 0.0


def _detect_module_d(text: str, reasons: List[str]) -> float:
    """
    Brandbook / Manual (D) – Reglas:
    1) Negación explícita → 0.0
    2) Lite explícito (pistas claras) → 0.6
    3) Full con ≥1 señal fuerte → 1.0
    4) Genérico sin adjetivo → 1.0 (full)
       Importante: no disparamos D por "sistema visual" (cruza con C).
    """
    t = _normalize(text)

    # 1) Negaciones
    if _negated_present(t, "manual") or _negated_present(t, "brandbook"):
        _add_reason(reasons, "D descartado: negación explícita")
        return 0.0

    # 2) Lite explícito
    score_lite = _count_pattern_matches(t, PATTERNS_D_LITE)
    if score_lite >= 1:
        _add_reason(reasons, f"D lite: {score_lite} señales explícitas")
        return 0.6

    # 3) Full explícito
    score_full = _count_pattern_matches(t, PATTERNS_D_FULL)
    if score_full >= 1:
        _add_reason(reasons, f"D full: {score_full} señales fuertes")
        return 1.0

    # 4) Genérico → full
    if any(kw in t for kw in KW_D_GENERIC):
        _add_reason(reasons, "D full: mención genérica sin calificador (regla de negocio)")
        return 1.0

    return 0.0


# ============================================================================
# API PRINCIPAL
# ============================================================================

def detect_module_weights(brief: str) -> Dict[str, Any]:
    reasons: List[str] = []
    weights: Dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0}

    a = _detect_module_a(brief, reasons)
    if a > 0:
        weights["A"] = a

    b = _detect_module_b(brief, reasons)
    if b > 0:
        weights["B"] = b

    c = _detect_module_c(brief, reasons)
    if c > 0:
        weights["C"] = c

    d = _detect_module_d(brief, reasons)
    if d > 0:
        weights["D"] = d

    e = _detect_impl_weight(brief, reasons)
    if e > 0:
        weights["E"] = e

    weights = {k: v for k, v in weights.items() if v > 0}

    # Compatibilidad: devolvemos tanto 'reasons' (app.py) como 'razones' (legacy)
    return {
        "modulos_pesos": weights,
        "reasons": reasons,
        "razones": reasons,
        "scores": {k: v for k, v in weights.items()},
    }


# ============================================================================
# DEBUG COMPATIBLE CON TU UI
# ============================================================================

def debug_parse(brief_text: str) -> Dict[str, Any]:
    t = _normalize(brief_text)

    strong = []
    for kw in [
        "naming",
        "logo",
        "logotipo",
        "rebranding",
        "refresh",
        "manual",
        "brandbook",
        "guia de marca",
        "guía de marca",
        "identidad",
        "pack",
        "piezas",
        "lanzamiento",
    ]:
        if _has_keyword(t, kw):
            strong.append(kw)

    parsed = detect_module_weights(brief_text)
    wants_rebrand = _count_pattern_matches(t, PATTERNS_C_REBRAND) > 0
    wants_refresh = _count_pattern_matches(t, PATTERNS_C_REFRESH) > 0
    has_naming = _count_pattern_matches(t, PATTERNS_C_NAMING) > 0
    has_logo = _count_pattern_matches(t, PATTERNS_C_LOGO) > 0

    return {
        "mode": "auto",
        "has_naming": has_naming,
        "has_logo": has_logo,
        "wants_rebrand": wants_rebrand,
        "wants_refresh": wants_refresh,
        "strong": strong,
        "modulos_pesos": parsed["modulos_pesos"],
        "reasons": parsed.get("reasons", []),
        "razones": parsed.get("razones", []),
        "scores": parsed.get("scores", {}),
    }


# ============================================================================
# ALIAS LEGACY
# ============================================================================

def _norm(s: Any) -> str:
    return _normalize(s)

def _has(text: str, kw: str) -> bool:
    return _has_keyword(text, kw)

def _any(text: str, kws: List[str]) -> bool:
    return _any_keyword(text, kws)