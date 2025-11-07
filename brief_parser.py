import re
import unicodedata
from typing import Dict, Any, List, Tuple, Optional

# ============================================================================
# NORMALIZACIÓN Y UTILIDADES BASE
# ============================================================================

def _normalize(txt: str) -> str:
    """
    Normaliza texto para matching robusto:
    - Maneja None y tipos no-string
    - Elimina tildes (ó→o, á→a) mediante NFD decomposition
    - Lowercase completo
    - Colapsa espacios múltiples
    
    Examples:
        "Diseño básico" → "diseno basico"
        "MODERNIZACIÓN   del logo" → "modernizacion del logo"
    """
    if not isinstance(txt, str):
        txt = str(txt or "")
    
    # Descomponer caracteres Unicode (NFD) y eliminar marcas diacríticas
    nfd = unicodedata.normalize("NFD", txt)
    without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    
    # Lowercase y colapsar espacios
    normalized = without_accents.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized


def _negated_present(text: str, kw: str, window: int = 4) -> bool:
    """
    Detecta si una keyword está negada dentro de una ventana de palabras.
    
    Negadores soportados:
    - sin, no, sin necesidad de, excluir, excepto, omitir
    
    Args:
        text: Texto normalizado a analizar
        kw: Keyword a buscar (puede ser multi-palabra)
        window: Ventana de palabras antes del keyword
    
    Examples:
        "sin manual" → True
        "no incluye logo" → True
        "sin necesidad de naming" → True
        "el manual es necesario" → False
    """
    # Extraer última palabra del keyword para matching robusto
    parts = kw.split()
    head = re.escape(parts[-1])
    
    # Pattern con negadores expandidos
    pattern = rf'\b(sin|no|sin\s+necesidad\s+de|excluir|excepto|omitir)\s+(?:\w+\s+){{0,{window}}}{head}\b'
    
    return re.search(pattern, text, re.IGNORECASE) is not None


def _has_keyword(text: str, kw: str) -> bool:
    """
    Verifica presencia de keyword considerando negación.
    Solo retorna True si está presente Y no negada.
    """
    if kw not in text:
        return False
    return not _negated_present(text, kw)


def _any_keyword(text: str, keywords: List[str]) -> bool:
    """Verifica si alguna keyword de la lista está presente (sin negación)"""
    return any(_has_keyword(text, kw) for kw in keywords)


def _add_reason(reasons: List[str], msg: str) -> None:
    """Agrega razón solo si no existe (previene duplicados)"""
    if msg not in reasons:
        reasons.append(msg)


def _count_pattern_matches(text: str, patterns: List[str]) -> int:
    """
    Cuenta cuántos patterns regex matchean en el texto.
    Útil para scoring de señales.
    """
    count = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            count += 1
    return count


# ============================================================================
# KEYWORDS Y PATRONES POR MÓDULO
# ============================================================================

# ────────────────────────────────────────────────────────────────────────────
# Módulo A: Research (nivel único = 1.0)
# ────────────────────────────────────────────────────────────────────────────
KW_A = [
    "research", "investigacion", "benchmark", "auditoria",
    "analisis de audiencia", "analisis de mercado",
    "competencia", "competidores", "estudio de marca",
    "desk research", "tendencias", "insights"
]

# ────────────────────────────────────────────────────────────────────────────
# Módulo B: Brand DNA
# ────────────────────────────────────────────────────────────────────────────
# Patrones para FULL (1.0) - Señales de profundidad estratégica
PATTERNS_B_FULL = [
    r'\b(brand\s+dna|adn\s+de\s+marca)\b',
    r'\b(territorios\s+de\s+marca|arquetipo)\b',
    r'\b(storytelling|narrativa\s+(de\s+marca|profunda))\b',
    r'\b(estrategia\s+(completa|profunda|integral))\b',
    r'\b(manifiesto\s+(completo|detallado))\b',
    r'\b(valores\s+y\s+principios|personalidad\s+de\s+marca)\b',
    r'\b(insight\s+del\s+consumidor|concepto\s+de\s+marca)\b'
]

# Keywords para LITE (0.65) - Señales de versión básica/simplificada
KW_B_LITE_HINTS = [
    "adn lite", "estrategia basica", "adn basico",
    "proposito y personalidad", "manifiesto simple",
    "resumen accionable", "sintesis", "enfoque sintesis",
    "estrategia rapida", "proposito basico", "brand dna simple",
    "adn de marca simple", "adn de marca sencillo",
    "brand dna sencillo", "adn de marca sencillo", "brand dna basico"
]

# Umbrales de decisión
UMBRAL_B_FULL = 2  # Necesita 2+ señales para ser full
UMBRAL_B_LITE = 1  # 1 señal lite es suficiente

# ────────────────────────────────────────────────────────────────────────────
# Módulo C: Creación de Identidad
# ────────────────────────────────────────────────────────────────────────────
# Patrones REFRESH (0.5) - Ajustes menores
PATTERNS_C_REFRESH = [
    r'\b(refresh|actualizacion|modernizacion)\b',
    r'\b(ajuste(s)?\s+(menor(es)?|de\s+marca|de\s+identidad))\b',
    r'\b(puesta\s+a\s+punto|refresco)\b'
]

# Patrones REBRANDING (0.8) - Rediseño significativo
PATTERNS_C_REBRAND = [
    r'\b(rebranding|re-branding|rebrand)\b',
    r'\b(rediseno\s+total|cambio\s+de\s+identidad)\b',
    r'\b(transformacion\s+de\s+marca|nueva\s+marca)\b',
    r'\b(modernizacion\s+(completa|del\s+logo|de\s+marca))\b'
]

# Patrones FULL (1.0) - Sistema completo
PATTERNS_C_FULL = [
    r'\b(identidad\s+(completa|full|integral))\b',
    r'\b(logo\s+([ye+]|y)\s+(naming|identidad))\b',
    r'\b(naming\s+([ye+]|y)\s+logo)\b',
    r'\b(sistema\s+visual\s+completo)\b'
]

# Componentes individuales (para detección combinada)
PATTERNS_C_NAMING = [r'\b(naming|nombre\s+de\s+marca|claim|tagline|slogan)\b']
PATTERNS_C_LOGO = [r'\b(logo|logotipo|isologo|imagotipo|iso|simbolo)\b']
PATTERNS_C_CONCEPTO = [r'\b(concepto\s+creativo|territorio\s+creativo)\b']

# Umbrales
UMBRAL_C_FULL = 2
UMBRAL_C_REBRAND = 1
UMBRAL_C_REFRESH = 1

# ────────────────────────────────────────────────────────────────────────────
# Módulo D: Brandbook/Manual
# ────────────────────────────────────────────────────────────────────────────
# Patrones FULL (1.0)
PATTERNS_D_FULL = [
    r'\b(manual\s+(completo|full|detallado|extenso|avanzado))\b',
    r'\b(brandbook\s+(completo|full))\b',
    r'\b(guia\s+(completa|avanzada|de\s+marca\s+completa))\b',
    r'\b(arquitectura\s+de\s+marca)\b',
    r'\b(sistema\s+visual\s+(completo|extenso))\b',
    r'\b(manual\s+de\s+identidad\s+full)\b'
]

# Patrones LITE (0.6)
PATTERNS_D_LITE = [
    r'\b(manual\s+(lite|basico|simple|reducido))\b',
    r'\b(brandbook\s+(lite|basico|esencial))\b',
    r'\b(guia\s+(rapida|basica|simple))\b',
    r'\b(mini\s+manual|version\s+simplificada)\b',
    r'\b(guia\s+de\s+marca\s+(basica|simple))\b'
]

# Keywords genéricos (sin calificador)
KW_D_GENERIC = [
    "brandbook", "manual de marca", "manual",
    "guia de marca", "sistema visual"
]

# Umbrales
UMBRAL_D_FULL = 2
UMBRAL_D_LITE = 1

# ────────────────────────────────────────────────────────────────────────────
# Módulo E: Implementación
# ────────────────────────────────────────────────────────────────────────────
KW_E_GENERIC = [
    "implementacion", "aplicaciones", "piezas", "pack",
    "lanzamiento", "template", "plantilla", "presentacion",
    "brochure", "banner", "papeleria", "posts", "redes",
    "sitio", "web", "packaging", "evento", "adaptaciones",
    "rrss", "banners"
]

PATTERNS_E_LITE = [
    r'\b(piezas?\s+basicas?|aplicaciones?\s+minimas?)\b',
    r'\b(pack\s+(pequeno|basico|inicial))\b',
    r'\b(adaptaciones?\s+esenciales?)\b'
]

PATTERNS_E_FULL = [
    r'\b(pack\s+(estandar|medio|completo))\b',
    r'\b(lanzamiento\s+estandar)\b',
    r'\b(aplicaciones?\s+principales?)\b'
]

PATTERNS_E_PLUS = [
    r'\b(pack\s+(grande|premium|extendido))\b',
    r'\b(campana|lanzamiento\s+(integral|masivo|completo))\b',
    r'\b(implementacion\s+(completa|extensa))\b',
    r'\b(evento\s+de\s+lanzamiento)\b'
]

# Rangos numéricos para clasificación
RANGO_E_LITE_MAX = 10   # ≤10 piezas → lite
RANGO_E_FULL_MAX = 15   # 11-15 piezas → full
                        # >15 piezas → plus


# ============================================================================
# DETECCIÓN DE MÓDULO E CON PARSER NUMÉRICO AVANZADO
# ============================================================================

def _parse_number_expr(text: str) -> Optional[int]:
    """
    Extrae número representativo de expresiones de cantidad en implementación.
    
    Soporta:
    - "entre 8 y 12 piezas" → 10 (promedio)
    - "hasta 5 adaptaciones" → 5
    - "más de 15 posts" → 16
    - ">= 20 banners" → 20
    - "10 piezas", "12 adaptaciones" → valor directo
    
    Returns:
        Número representativo o None si no se encuentra
    """
    # Patrón 1: "entre X y Y"
    match = re.search(r'\bentre\s+(\d+)\s+y\s+(\d+)\b', text)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        return (a + b) // 2  # Promedio
    
    # Patrón 2: "hasta X"
    match = re.search(r'\bhasta\s+(\d+)\b', text)
    if match:
        return int(match.group(1))
    
    # Patrón 3: "más de X"
    match = re.search(r'\bmas\s+de\s+(\d+)\b', text)
    if match:
        return int(match.group(1)) + 1  # Ligeramente por encima
    
    # Patrón 4: Operadores de comparación (>=, >, <=, <)
    match = re.search(r'(>=|>|<=|<)\s*(\d+)', text)
    if match:
        operator, num = match.group(1), int(match.group(2))
        if operator == '>':
            return num + 1
        elif operator == '>=':
            return num
        elif operator == '<':
            return max(0, num - 1)
        elif operator == '<=':
            return num
    
    # Patrón 5: "N piezas/posts/adaptaciones/banners"
    match = re.search(r'\b(\d+)\s*(adaptaciones?|piezas?|posts?|banners?|aplicaciones?)\b', text)
    if match:
        return int(match.group(1))
    
    # Patrón 6: "piezas/posts de N"
    match = re.search(r'\b(adaptaciones?|piezas?|posts?|banners?)\s*(de|x)?\s*(\d+)\b', text)
    if match and match.lastindex and match.group(match.lastindex).isdigit():
        return int(match.group(match.lastindex))
    
    return None


def _detect_impl_weight(text: str, reasons: List[str]) -> float:
    """
    Detecta peso de Implementación (E) basado en:
    1. Cantidades numéricas explícitas
    2. Rangos y expresiones ("más de", "hasta")
    3. Señales cualitativas (pack grande, campaña)
    
    Returns:
        0.0 (no detectado), 0.6 (lite), 1.0 (full), o 1.5 (plus)
    """
    t = _normalize(text)
    
    # Si no menciona nada de implementación, retornar 0
    if not _any_keyword(t, KW_E_GENERIC):
        return 0.0
    
    # Intentar parsear cantidad numérica
    qty = _parse_number_expr(t)
    
    if isinstance(qty, int):
        # Clasificar por rangos
        if qty <= RANGO_E_LITE_MAX:
            _add_reason(reasons, f"E lite: {qty} piezas detectadas (≤{RANGO_E_LITE_MAX})")
            return 0.6
        elif qty <= RANGO_E_FULL_MAX:
            _add_reason(reasons, f"E full: {qty} piezas detectadas ({RANGO_E_LITE_MAX+1}-{RANGO_E_FULL_MAX})")
            return 1.0
        else:
            _add_reason(reasons, f"E plus: {qty} piezas detectadas (>{RANGO_E_FULL_MAX})")
            return 1.5
    
    # Sin número explícito: usar señales cualitativas
    score_plus = _count_pattern_matches(t, PATTERNS_E_PLUS)
    score_full = _count_pattern_matches(t, PATTERNS_E_FULL)
    score_lite = _count_pattern_matches(t, PATTERNS_E_LITE)
    
    if score_plus > 0:
        _add_reason(reasons, f"E plus: {score_plus} señales de campaña/lanzamiento integral")
        return 1.5
    elif score_full > 0:
        _add_reason(reasons, f"E full: {score_full} señales de pack estándar")
        return 1.0
    elif score_lite > 0:
        _add_reason(reasons, f"E lite: {score_lite} señales de piezas básicas")
        return 0.6
    
    # Menciones genéricas sin detalles → default conservador (lite)
    _add_reason(reasons, "E lite: implementación mencionada sin detalles (default conservador)")
    return 0.6


# ============================================================================
# DETECCIÓN POR MÓDULOS (A-D)
# ============================================================================

def _detect_module_a(text: str, reasons: List[str]) -> float:
    """
    Módulo A: Research
    Nivel único = 1.0 (no tiene variantes)
    """
    t = _normalize(text)
    
    if _any_keyword(t, KW_A):
        _add_reason(reasons, "A: Research detectado (benchmark/análisis/auditoría)")
        return 1.0
    
    return 0.0


def _detect_module_b(text: str, reasons: List[str]) -> float:
    """
    Módulo B: Brand DNA
    Niveles: 0.65 (lite) o 1.0 (full)
    
    Estrategia conservadora:
    - 2+ señales full → full
    - 1+ señales lite → lite
    - 1 señal full aislada → lite (conservador)
    """
    t = _normalize(text)
    
    score_full = _count_pattern_matches(t, PATTERNS_B_FULL)
    score_lite = sum(1 for kw in KW_B_LITE_HINTS if _has_keyword(t, kw))
    
    # Decisión por prioridad
    if score_full >= UMBRAL_B_FULL:
        _add_reason(reasons, f"B full: Brand DNA completo ({score_full} señales de profundidad)")
        return 1.0
    
    if score_lite >= UMBRAL_B_LITE:
        _add_reason(reasons, f"B lite: Estrategia básica ({score_lite} señales)")
        return 0.65
    
    # Edge case: 1 señal full sin señales lite → conservador a lite
    if score_full == 1 and score_lite == 0:
        _add_reason(reasons, "B lite: 1 señal aislada sin contexto (conservador)")
        return 0.65
    
    return 0.0


def _detect_module_c(text: str, reasons: List[str]) -> float:
    """
    Módulo C: Creación de Identidad
    Niveles: 0.5 (refresh), 0.8 (rebranding), 1.0 (full)
    
    Estrategia:
    - Detectar señales específicas por nivel
    - Detectar componentes individuales (logo+naming = full)
    - En empates, elegir el nivel inferior (conservador)
    """
    t = _normalize(text)
    
    # Verificar negación global de identidad
    if _negated_present(t, "logo") and _negated_present(t, "identidad"):
        _add_reason(reasons, "C descartado: negación explícita de logo e identidad")
        return 0.0
    
    # Scoring por nivel
    score_full = _count_pattern_matches(t, PATTERNS_C_FULL)
    score_rebrand = _count_pattern_matches(t, PATTERNS_C_REBRAND)
    score_refresh = _count_pattern_matches(t, PATTERNS_C_REFRESH)
    
    # Detectar componentes individuales
    has_naming = _count_pattern_matches(t, PATTERNS_C_NAMING) > 0
    has_logo = _count_pattern_matches(t, PATTERNS_C_LOGO) > 0
    has_concepto = _count_pattern_matches(t, PATTERNS_C_CONCEPTO) > 0
    
    components_count = sum([has_naming, has_logo, has_concepto])
    
    # Decisión por prioridad descendente
    
    # 1) FULL: Señales explícitas o múltiples componentes
    if score_full >= UMBRAL_C_FULL or components_count >= 2:
        _add_reason(reasons, f"C full: Identidad completa (full={score_full}, componentes={components_count})")
        return 1.0
    
    # 2) REBRANDING: Pero cuidado con empates con refresh
    if score_rebrand >= UMBRAL_C_REBRAND:
        # Si hay empate con refresh, elegir refresh (más conservador)
        if score_refresh >= UMBRAL_C_REFRESH and score_refresh >= score_rebrand:
            _add_reason(reasons, "C refresh: Empate rebranding/refresh (conservador)")
            return 0.5
        _add_reason(reasons, f"C rebranding: Rediseño significativo ({score_rebrand} señales)")
        return 0.8
    
    # 3) REFRESH: Ajustes menores
    if score_refresh >= UMBRAL_C_REFRESH:
        _add_reason(reasons, f"C refresh: Ajuste/modernización ({score_refresh} señales)")
        return 0.5
    
    # 4) Componentes individuales sin calificador
    if has_logo or has_naming:
        # Si menciona "ajuste" → refresh, sino → full
        if re.search(r'\b(ajuste(s)?|puesta\s+a\s+punto)\b', t):
            _add_reason(reasons, "C refresh: Componentes con mención de ajuste")
            return 0.5
        _add_reason(reasons, "C full: Logo/naming sin calificador (default realista)")
        return 1.0
    
    return 0.0


def _detect_module_d(text: str, reasons: List[str]) -> float:
    """
    Módulo D: Brandbook/Manual
    Niveles: 0.6 (lite) o 1.0 (full)
    
    Estrategia conservadora:
    - Negación explícita → 0
    - Señales full claras → full
    - Señales lite o ambiguas → lite
    - Genéricos sin calificador → lite (conservador)
    """
    t = _normalize(text)
    
    # Verificar negación explícita
    if _negated_present(t, "manual") or _negated_present(t, "brandbook"):
        _add_reason(reasons, "D descartado: negación explícita 'sin manual/brandbook'")
        return 0.0
    
    score_full = _count_pattern_matches(t, PATTERNS_D_FULL)
    score_lite = _count_pattern_matches(t, PATTERNS_D_LITE)
    
    # Detectar keywords genéricos (sin calificador)
    has_generic = any(kw in t for kw in KW_D_GENERIC)
    
    if has_generic:
        # Contar como señal ambigua para ambos lados
        score_full += 1
        score_lite += 1
    
    # Decisión conservadora
    if score_full >= UMBRAL_D_FULL and score_full > score_lite:
        _add_reason(reasons, f"D full: Manual completo ({score_full} señales)")
        return 1.0
    
    if score_lite >= UMBRAL_D_LITE:
        _add_reason(reasons, f"D lite: Manual básico ({score_lite} señales)")
        return 0.6
    
    # Empate o genérico solo → conservador a lite
    if score_full == score_lite and has_generic:
        _add_reason(reasons, "D lite: Mención genérica sin calificador (conservador)")
        return 0.6
    
    return 0.0


# ============================================================================
# API PRINCIPAL
# ============================================================================

def detect_module_weights(brief: str) -> Dict[str, Any]:
    """
    Detecta módulos de branding y sus pesos a partir del brief textual.
    
    Args:
        brief: Texto del brief en español (formato libre)
    
    Returns:
        {
            "modulos_pesos": {"A": 1.0, "B": 0.65, "C": 1.0, ...},
            "razones": ["A: Research detectado...", "B lite: ..."],
            "scores": {}  # Reservado para debugging futuro
        }
    
    Módulos detectados:
        A: Research (1.0)
        B: Brand DNA (lite=0.65, full=1.0)
        C: Creación (refresh=0.5, rebranding=0.8, full=1.0)
        D: Brandbook (lite=0.6, full=1.0)
        E: Implementación (lite=0.6, full=1.0, plus=1.5)
    """
    reasons: List[str] = []
    weights: Dict[str, float] = {}
    
    # Detectar cada módulo en orden
    peso_a = _detect_module_a(brief, reasons)
    if peso_a > 0:
        weights["A"] = peso_a
    
    peso_b = _detect_module_b(brief, reasons)
    if peso_b > 0:
        weights["B"] = peso_b
    
    peso_c = _detect_module_c(brief, reasons)
    if peso_c > 0:
        weights["C"] = peso_c
    
    peso_d = _detect_module_d(brief, reasons)
    if peso_d > 0:
        weights["D"] = peso_d
    
    peso_e = _detect_impl_weight(brief, reasons)
    if peso_e > 0:
        weights["E"] = peso_e
    
    return {
        "modulos_pesos": weights,
        "razones": reasons,
        "scores": {}  # Reservado para compatibilidad futura
    }


# ============================================================================
# FUNCIÓN DE DEBUG (COMPATIBILIDAD CON UI)
# ============================================================================

def debug_parse(brief_text: str) -> Dict[str, Any]:
    """
    Versión extendida para debugging en interfaz de usuario.
    Mantiene 100% de compatibilidad con versión anterior.
    
    Returns:
        {
            "mode": "auto",
            "has_naming": bool,
            "has_logo": bool,
            "wants_rebrand": bool,
            "wants_refresh": bool,
            "strong": [keywords detectadas],
            "modulos_pesos": {...},
            "razones": [...]
        }
    """
    t = _normalize(brief_text)
    
    # Detección de keywords "fuertes" para UI legacy
    strong_keywords = []
    legacy_keywords = [
        "naming", "logo", "logotipo", "rebranding", "refresh",
        "manual", "identidad", "pack", "piezas", "lanzamiento"
    ]
    
    for kw in legacy_keywords:
        if _has_keyword(t, kw):
            strong_keywords.append(kw)
    
    # Detecciones booleanas específicas (para compatibilidad UI)
    has_naming = any(kw in t for kw in ["naming", "nombre de marca", "claim", "tagline", "slogan"])
    has_logo = any(kw in t for kw in ["logo", "logotipo", "isologo", "imagotipo", "iso"])
    wants_rebrand = re.search(r'\b(rebranding|re-branding|rebrand)\b', t) is not None
    wants_refresh = re.search(r'\b(refresh|puesta\s+a\s+punto|ajustes?\s+menor(es)?)\b', t) is not None
    
    # Parseo completo
    parsed = detect_module_weights(brief_text)
    
    return {
        "mode": "auto",
        "has_naming": has_naming,
        "has_logo": has_logo,
        "wants_rebrand": wants_rebrand,
        "wants_refresh": wants_refresh,
        "strong": strong_keywords,
        "modulos_pesos": parsed["modulos_pesos"],
        "razones": parsed["razones"]
    }


# ============================================================================
# FUNCIONES LEGACY (COMPATIBILIDAD CON CÓDIGO EXISTENTE)
# ============================================================================

def _norm(s: str) -> str:
    """Alias de _normalize() para compatibilidad con código legacy"""
    return _normalize(s)


def _has(text: str, kw: str) -> bool:
    """Alias de _has_keyword() para compatibilidad con código legacy"""
    return _has_keyword(text, kw)


def _any(text: str, kws: List[str]) -> bool:
    """Alias de _any_keyword() para compatibilidad con código legacy"""
    return _any_keyword(text, kws)