# brief_parser.py — versión unificada y optimizada para producción
# Mantiene compatibilidad con detect_module_weights(...) y debug_parse(...)

import re
import unicodedata
from typing import Dict, Any, List, Optional

# Biblioteca consolidada de entregables por módulo (A–E) y nivel
# A: Research | B: Brand DNA | C: Creación | D: Brandbook | E: Implementación

DELIVERABLES = {
    "A": {  # Research
        # Si preferís, podemos usar lite/full directamente; tu helper actual ya soporta ambos.
        "lite": [
            "Benchmark de hasta cinco marcas del sector",
            "Mapa rápido de tendencias visuales y comunicacionales",
            "Síntesis de hallazgos clave del análisis",
        ],
        "full": [
            "Benchmark gráfico, comunicacional y de posicionamiento de la categoría",
            "Análisis de audiencias, hábitos e insights",
            "Matriz de posición competitiva y perfil detallado de audiencias",
        ],
        # "plus": []  # Eliminado según decisión
    },

    "B": {  # Brand DNA (acumulativo)
        "lite": [
            "Atributos esenciales y personalidad base de la marca",
            "Promesa de valor central",
        ],
        "full": [
            "Propósito, valores y principios que guían la marca",
            "Territorios y posicionamiento estratégico",
            "Concepto y síntesis accionable de la marca",
        ],
        "plus": [
            "Narrativa y concepto rector de la marca",
            "Tono de voz, arquetipo y manifiesto de marca",
        ],
    },

    "C": {  # Creación (acumulativo; quitamos naming de Lite como pediste)
        "lite": [
            "Definición preliminar del enfoque creativo",
            "Bocetos o primeras aproximaciones al sistema visual",
        ],
        "full": [
            "Desarrollo y diseño del isologotipo",
            "Variantes de logotipo y arquitectura del sistema visual",
            "Consolidación del concepto creativo de la marca",
        ],
        "plus": [
            "Validación avanzada de nombre y sistema visual",
            "Sistema de naming extendido (familia de productos o servicios)",
            "Concepto creativo integral aplicado a la marca",
        ],
    },

    "D": {  # Brandbook (NO acumulativo por decisión; ajustamos lógica en el siguiente paso)
        "lite": [
            "Guía de uso y buenas prácticas de marca",
            "Sistema visual básico con isologotipo, paleta de colores y tipografías",
            "Manual breve con lineamientos esenciales de identidad",
        ],
        "full": [
            "Manual de marca completo con estructura visual detallada: paleta, tipografías, versiones del isologotipo y estilo fotográfico",
            "Desarrollo de recursos gráficos y visuales complementarios",
            "Lineamientos para coherencia visual en todas las aplicaciones",
        ],
        "plus": [
            "Manual avanzado con templates y aplicaciones extendidas",
            "Sistema visual complementario (íconos, tramas, recursos gráficos)",
            "Lineamientos para animación, uso digital y motion branding",
        ],
    },

    "E": {  # Implementación (acumulativo; Full incluye Lite, Plus incluye Full)
        "lite": [
            "Hasta cinco aplicaciones digitales de marca: template PPT (hasta 5 slides), template DOC, piezas para redes sociales, avatares y/o perfiles, firma de correo",
            "Ajuste técnico de logotipo y paleta para uso digital",
        ],
        "full": [
            # Extras sobre Lite (la acumulación la hace el helper)
            "Aplicaciones gráficas impresas: banners, papelería y/o señalética",
            "Diseño y diagramación de brochure de marca (hasta 10 slides; no incluye redacción de contenido)",
            "Supervisión creativa de producción y adaptación de piezas",
        ],
        "plus": [
            # Extras sobre Full
            "Campaña de lanzamiento con hasta 15 piezas digitales",
            "Kit de marca para implementación interna y externa",
            "Acompañamiento en la ejecución de piezas y medios",
        ],
    },
}

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

# A: Research (1.0)
PATTERNS_A = [
    r"\b(research|investigacion|auditoria)\b",
    r"\b(benchmark|competencia|competidores?)\b",
    r"\b(analisis\s+de\s+(audiencia|mercado)|insights?)\b",
    r"\b(estudio\s+de\s+marca|desk\s+research|tendencias)\b",
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
    r"\b(proposito\s+y\s+valores|dna\s+estrategico)\b",
]
KW_B_LITE_HINTS = [
    "adn lite", "estrategia basica", "adn basico",
    "proposito y personalidad", "manifiesto simple",
    "resumen accionable", "sintesis", "enfoque sintesis",
    "estrategia rapida", "adn de marca basico", "brand dna basico",
    "propósito básico", "adn de marca simple", "brand dna simple",
]

# C: Creación — refresh (0.5) / rebranding (0.8) / full (1.0)
PATTERNS_C_REFRESH = [
    r"\b(refresh|actualizacion|modernizacion)\b",
    r"\b(ajuste(s)?\s+(menor(es)?|de\s+marca|de\s+identidad))\b",
    r"\b(puesta\s+a\s+punto|refresco)\b",
]
PATTERNS_C_REBRAND = [
    r"\b(rebranding|re-branding|rebrand)\b",
    r"\b(rediseno\s+total|cambio\s+de\s+identidad)\b",
    r"\b(transformacion\s+de\s+marca|nueva\s+marca)\b",
    r"\b(modernizacion\s+(completa|del\s+logo|de\s+marca))\b",
]
PATTERNS_C_FULL = [
    r"\b(identidad\s+(completa|full|integral))\b",
    r"\b(logo\s+([ye+]|y)\s+(naming|identidad))\b",
    r"\b(naming\s+([ye+]|y)\s+logo)\b",
    r"\b(sistema\s+visual\s+completo)\b",
]
PATTERNS_C_NAMING  = [r"\b(naming|nombre\s+de\s+marca|claim|tagline|slogan)\b"]
PATTERNS_C_LOGO    = [r"\b(logo|logotipo|isologo|imagotipo|iso|simbolo)\b"]
PATTERNS_C_CONCEPTO= [r"\b(concepto\s+creativo|territorio\s+creativo)\b"]

# D: Brandbook — lite (0.6) / full (1.0)
PATTERNS_D_FULL = [
    r"\b(manual\s+(completo|full|detallado|extenso|avanzado|integral))\b",
    r"\b(brandbook\s+(completo|full|integral))\b",
    r"\b(guia\s+(completa|avanzada|integral|de\s+marca\s+completa))\b",
    r"\b(manual\s+de\s+identidad\s+(completo|full|integral))\b",
    r"\b(sistema\s+visual\s+(completo|extenso|integral))\b",
    r"\b(arquitectura\s+de\s+marca)\b",
]
PATTERNS_D_LITE = [
    r"\b(manual\s+(lite|basico|simple|reducido|abreviado|rapido))\b",
    r"\b(brandbook\s+(lite|basico|esencial|simple))\b",
    r"\b(guia\s+(rapida|basica|simple|essencial))\b",
    r"\b(mini\s+manual|version\s+simplificada)\b",
    r"\b(guia\s+de\s+marca\s+(basica|simple|lite))\b",
    r"\b(manual\s+de\s+marca\s+(lite|basico|simple|reducido))\b",
]
KW_D_GENERIC = ["brandbook", "manual de marca", "manual", "guia de marca", "manual de identidad", "sistema visual"]

# E: Implementación — lite (0.6) / full (1.0) / plus (1.5)
KW_E_GENERIC = [
    "implementacion", "aplicaciones", "piezas", "pack",
    "lanzamiento", "template", "plantilla", "presentacion",
    "brochure", "banner", "papeleria", "posts", "redes",
    "sitio", "web", "packaging", "evento", "adaptaciones",
    "rrss", "banners",
]
PATTERNS_E_LITE = [
    r"\b(piezas?\s+basicas?|aplicaciones?\s+minimas?)\b",
    r"\b(pack\s+(pequeno|basico|inicial))\b",
    r"\b(adaptaciones?\s+esenciales?)\b",
]
PATTERNS_E_FULL = [
    r"\b(pack\s+(estandar|medio|completo))\b",
    r"\b(lanzamiento\s+estandar)\b",
    r"\b(aplicaciones?\s+principales?)\b",
]
PATTERNS_E_PLUS = [
    r"\b(pack\s+(grande|premium|extendido))\b",
    r"\b(campana|lanzamiento\s+(integral|masivo|completo))\b",
    r"\b(implementacion\s+(completa|extensa))\b",
    r"\b(evento\s+de\s+lanzamiento)\b",
]
RANGO_E_LITE_MAX = 10
RANGO_E_FULL_MAX = 15

# ============================================================================
# DETECCIÓN E (Implementación) CON PARSER NUMÉRICO
# ============================================================================

def _parse_number_expr(text: str) -> Optional[int]:
    t = _normalize(text)
    m = re.search(r'\bentre\s+(\d+)\s+y\s+(\d+)\b', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (a + b) // 2
    m = re.search(r'\bhasta\s+(\d+)\b', t)
    if m: return int(m.group(1))
    m = re.search(r'\bmas\s+de\s+(\d+)\b', t)
    if m: return int(m.group(1)) + 1
    m = re.search(r'(>=|>|<=|<)\s*(\d+)', t)
    if m:
        op, num = m.group(1), int(m.group(2))
        return num + 1 if op == '>' else num if op in ('>=','<=') else max(0, num - 1)
    m = re.search(r'\b(\d+)\s*(adaptaciones?|piezas?|posts?|banners?|aplicaciones?)\b', t)
    if m: return int(m.group(1))
    m = re.search(r'\b(adaptaciones?|piezas?|posts?|banners?|aplicaciones?)\s*(de|x)?\s*(\d+)\b', t)
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
            _add_reason(reasons, f"E full: {qty} piezas ({RANGO_E_LITE_MAX+1}-{RANGO_E_FULL_MAX})")
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
    score = _count_pattern_matches(t, PATTERNS_A)
    if score > 0:
        _add_reason(reasons, f"A: Research ({score} señales)")
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
    sf  = _count_pattern_matches(t, PATTERNS_C_FULL)
    srb = _count_pattern_matches(t, PATTERNS_C_REBRAND)
    srf = _count_pattern_matches(t, PATTERNS_C_REFRESH)
    has_naming   = _count_pattern_matches(t, PATTERNS_C_NAMING)   > 0
    has_logo     = _count_pattern_matches(t, PATTERNS_C_LOGO)     > 0
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
    4) Genérico sin adjetivo → **1.0 (full)**
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
    weights: Dict[str, float] = {"A":0.0,"B":0.0,"C":0.0,"D":0.0,"E":0.0}

    a = _detect_module_a(brief, reasons)
    if a > 0: weights["A"] = a

    b = _detect_module_b(brief, reasons)
    if b > 0: weights["B"] = b

    c = _detect_module_c(brief, reasons)
    if c > 0: weights["C"] = c

    d = _detect_module_d(brief, reasons)
    if d > 0: weights["D"] = d

    e = _detect_impl_weight(brief, reasons)
    if e > 0: weights["E"] = e

    weights = {k:v for k,v in weights.items() if v > 0}
    return {
        "modulos_pesos": weights,
        "razones": reasons,
        "scores": {k:v for k,v in weights.items()},
    }

# ============================================================================
# DEBUG COMPATIBLE CON TU UI
# ============================================================================

def debug_parse(brief_text: str) -> Dict[str, Any]:
    t = _normalize(brief_text)
    strong = []
    for kw in ["naming","logo","logotipo","rebranding","refresh","manual","identidad","pack","piezas","lanzamiento","brandbook"]:
        if _has_keyword(t, kw):
            strong.append(kw)
    parsed = detect_module_weights(brief_text)
    wants_rebrand = _count_pattern_matches(t, PATTERNS_C_REBRAND) > 0
    wants_refresh = _count_pattern_matches(t, PATTERNS_C_REFRESH) > 0
    has_naming    = _count_pattern_matches(t, PATTERNS_C_NAMING)  > 0
    has_logo      = _count_pattern_matches(t, PATTERNS_C_LOGO)    > 0
    return {
        "mode": "auto",
        "has_naming": has_naming,
        "has_logo": has_logo,
        "wants_rebrand": wants_rebrand,
        "wants_refresh": wants_refresh,
        "strong": strong,
        "modulos_pesos": parsed["modulos_pesos"],
        "razones": parsed["razones"],
        "scores": parsed.get("scores", {}),
    }

# ============================================================================
# ALIAS LEGACY
# ============================================================================

def _norm(s: Any) -> str: return _normalize(s)
def _has(text: str, kw: str) -> bool: return _has_keyword(text, kw)
def _any(text: str, kws: List[str]) -> bool: return _any_keyword(text, kws)