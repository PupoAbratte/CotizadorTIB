import json
from typing import Dict, Any, Tuple

# ------------------------
# Carga de catálogo
# ------------------------
def load_catalog(path: str = "catalog.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------------------
# Base: suma de módulos por pesos (ya normalizados por el parser)
# ------------------------
def base_price_usd(catalog: Dict[str, Any], mod_weights: Dict[str, float]) -> float:
    P = catalog.get("precios", {})
    total = 0.0
    for m, w in (mod_weights or {}).items():
        if m == "A":
            total += P.get("A", 0) * float(w)
        elif m == "B":
            # w: 1.0 (full) o 0.65 (lite) viene precalculado en el parser
            base = P.get("B", 0)
            total += base * float(w)
        elif m == "C":
            # w: 1.0(C_full) | 0.8(C_rebranding) | 0.5(C_refresh)
            if abs(float(w) - 1.0) < 1e-9:
                total += P.get("C_full", 0)
            elif abs(float(w) - 0.8) < 1e-9:
                total += P.get("C_rebranding", 0)
            elif abs(float(w) - 0.5) < 1e-9:
                total += P.get("C_refresh", 0)
            else:
                total += P.get("C_full", 0) * float(w)
        elif m == "D":
            # w: 1.0 (full) | 0.6 (lite)
            if abs(float(w) - 1.0) < 1e-9:
                total += P.get("D_full", 0)
            elif abs(float(w) - 0.6) < 1e-9:
                total += P.get("D_lite", 0)
            else:
                total += P.get("D_full", 0) * float(w)
        elif m == "E":
            # w: 1.0 (full) | 0.6 (lite) | 1.5 (plus)
            if abs(float(w) - 1.0) < 1e-9:
                total += P.get("E_full", 0)
            elif abs(float(w) - 0.6) < 1e-9:
                total += P.get("E_lite", 0)
            elif abs(float(w) - 1.5) < 1e-9:
                total += P.get("E_plus", 0)
            else:
                total += P.get("E_full", 0) * float(w)
        # ignorar claves desconocidas
    return round(total, 2)

# ------------------------
# Bundles (hoy neutros)
# ------------------------
def apply_bundles(catalog: Dict[str, Any], mod_weights: Dict[str, float], total_base: float) -> float:
    b = catalog.get("bundles", {"dos_mods": 1.0, "tres_o_mas": 1.0})
    n_mods_activos = len([m for m, w in (mod_weights or {}).items() if float(w) > 0])
    factor = 1.0
    if n_mods_activos >= 3:
        factor = float(b.get("tres_o_mas", 1.0))
    elif n_mods_activos == 2:
        factor = float(b.get("dos_mods", 1.0))
    return round(total_base * factor, 2)

# ------------------------
# Overhead (costos fijos) imputado por horas estimadas
# ------------------------
def _overhead_level_key(mod: str, w: float) -> str:
    """
    Mapea módulo + peso a una clave de 'module_hours' en catalog.json.
    Sigue tus reglas actuales de pesos:
    - B: 1.0 full | 0.65 lite
    - C: 1.0 full | 0.8 rebranding | 0.5 refresh
    - D: 1.0 full | 0.6 lite
    - E: 1.0 full | 0.6 lite | 1.5 plus
    """
    wf = float(w)
    if mod == "A":
        return "A"
    if mod == "B":
        return "B_lite" if abs(wf - 0.65) < 1e-9 else "B_full"
    if mod == "C":
        if abs(wf - 1.0) < 1e-9:
            return "C_full"
        if abs(wf - 0.8) < 1e-9:
            return "C_rebranding"
        if abs(wf - 0.5) < 1e-9:
            return "C_refresh"
        # fallback razonable si viniera un peso raro
        return "C_full"
    if mod == "D":
        return "D_lite" if abs(wf - 0.6) < 1e-9 else "D_full"
    if mod == "E":
        if abs(wf - 1.5) < 1e-9:
            return "E_plus"
        if abs(wf - 0.6) < 1e-9:
            return "E_lite"
        return "E_full"
    return mod  # fallback


def estimate_hours_by_module(catalog: Dict[str, Any], mod_weights: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """
    Devuelve (horas_totales_estimadas, breakdown_por_clave).
    Si falta configuración de overhead, devuelve (0.0, {}).
    """
    oh = (catalog or {}).get("overhead") or {}
    hmap = (oh.get("module_hours") or {})
    if not hmap:
        return 0.0, {}

    breakdown: Dict[str, float] = {}
    total_h = 0.0

    for m, w in (mod_weights or {}).items():
        try:
            wf = float(w)
        except Exception:
            continue
        if wf <= 0:
            continue

        key = _overhead_level_key(m, wf)
        h = float(hmap.get(key, 0.0))
        if h <= 0:
            continue

        breakdown[key] = round(breakdown.get(key, 0.0) + h, 2)
        total_h += h

    return round(total_h, 2), breakdown


def overhead_rate_usd_per_hour(catalog: Dict[str, Any]) -> float:
    """
    Overhead/h = (sum monthly_usd) / billable_hours_per_month
    """
    oh = (catalog or {}).get("overhead") or {}
    monthly = (oh.get("monthly_usd") or {})
    billable = float(oh.get("billable_hours_per_month", 0) or 0)
    monthly_total = sum(float(v) for v in monthly.values()) if monthly else 0.0

    if monthly_total <= 0 or billable <= 0:
        return 0.0
    return round(monthly_total / billable, 4)


def overhead_for_quote_usd(catalog: Dict[str, Any], hours_est: float) -> float:
    rate = overhead_rate_usd_per_hour(catalog)
    if rate <= 0 or hours_est <= 0:
        return 0.0
    return round(rate * float(hours_est), 2)

# ------------------------
# Coeficientes
# ------------------------
def coef_stakeholders(label: str) -> float:
    return {
        "uno": 1.00,
        "dos": 1.04,
        "tres_o_mas": 1.08
    }.get(label, 1.00)

def coef_idiomas(base: float, n_idiomas: int, extra_per: float) -> float:
    if n_idiomas <= 1:
        return base
    return round(base + (n_idiomas - 1) * extra_per, 3)

def apply_coefs(catalog: Dict[str, Any], base_usd: float,
                cliente: str, urgencia: str, complejidad: str,
                n_idiomas: int, stakeholders: str, relacion: str) -> Tuple[float, Dict[str, float]]:
    C = catalog["coeficientes"]
    c_cliente = float(C["cliente"].get(cliente, 1.0))
    c_urg = float(C["urgencia"].get(urgencia, 1.0))
    c_comp = float(C["complejidad"].get(complejidad, 1.0))
    c_idiomas = coef_idiomas(float(C["idiomas"]["base"]), n_idiomas, float(C["idiomas"]["extra"]))
    c_st = coef_stakeholders(stakeholders)
    c_rel = float(C["relacion"].get(relacion, 1.0))

    total_coef = c_cliente * c_urg * c_comp * c_idiomas * c_st * c_rel
    total_coef = min(total_coef, float(C["tope_total_coef"]))

    adjusted = round(base_usd * total_coef, 2)
    return adjusted, {
        "cliente": c_cliente,
        "urgencia": c_urg,
        "complejidad": c_comp,
        "idiomas": c_idiomas,
        "stakeholders": c_st,
        "relacion": c_rel,
        "total_coef": round(total_coef, 3)
    }

# ------------------------
# Escenarios y COP
# ------------------------
def to_scenarios(catalog: Dict[str, Any], adjusted_usd: float) -> Dict[str, float]:
    S = catalog["escenarios"]
    return {
        "minimo": round(adjusted_usd * float(S["minimo"]), 2),
        "logico": round(adjusted_usd * float(S["logico"]), 2),
        "maximo": round(adjusted_usd * float(S["maximo"]), 2)
    }

def to_cop(catalog: Dict[str, Any], usd: float) -> int:
    rate = int(catalog["moneda"]["usd_to_cop"])
    return int(round(usd * rate, 0))

# ------------------------
# Explicación legible
# ------------------------
def explain(mod_levels: Dict[str, float], razones: Any, coefs: Dict[str, float]) -> str:
    parts = []
    ml = mod_levels or {}
    if ml.get("A"): parts.append("A: Research.")
    if ml.get("B"):
        parts.append(f"B: Brand DNA ({'lite' if abs(ml['B']-0.65)<1e-9 else 'full'}).")
    if ml.get("C"):
        c_txt = "full" if abs(ml["C"]-1.0)<1e-9 else ("rebranding" if abs(ml["C"]-0.8)<1e-9 else "refresh")
        parts.append(f"C: Creación ({c_txt}).")
    if ml.get("D"):
        parts.append(f"D: Brandbook ({'lite' if abs(ml['D']-0.6)<1e-9 else 'full'}).")
    if ml.get("E"):
        e_txt = "lite" if abs(ml["E"]-0.6)<1e-9 else ("plus" if abs(ml["E"]-1.5)<1e-9 else "full")
        parts.append(f"E: Implementación ({e_txt}).")
    rs = " ".join(razones or [])
    co = " ".join([f"{k}:{v}" for k,v in (coefs or {}).items()])
    return " • ".join(parts) + (f"\nRazones: {rs}\nCoeficientes: {co}" if rs or co else "")

# ------------------------
# Orquestador único (usado por app.py)
# ------------------------
def compute_quote(catalog: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    base = base_price_usd(catalog, features.get("modulos_pesos", {}))
    base = apply_bundles(catalog, features.get("modulos_pesos", {}), base)
    adjusted, coefs = apply_coefs(
        catalog, base,
        features.get("cliente_tipo", "pyme"),
        features.get("urgencia", "normal"),
        features.get("complejidad", "media"),
        int(features.get("idiomas", 1)),
        features.get("stakeholders", "uno"),
        features.get("relacion", "nuevo")
    )

    # -------- Overhead: estimación por horas --------
    adjusted_usd_sin_overhead = adjusted
    hours_est, hours_breakdown = estimate_hours_by_module(
        catalog,
        features.get("modulos_pesos", {})
    )
    overhead_rate_usd_h = overhead_rate_usd_per_hour(catalog)
    overhead_usd = overhead_for_quote_usd(catalog, hours_est)

    adjusted = round(adjusted_usd_sin_overhead + overhead_usd, 2)
    # -----------------------------------------------

    return {
        "base_usd": base,
        "adjusted_usd": adjusted,  # ahora incluye overhead
        "adjusted_usd_sin_overhead": adjusted_usd_sin_overhead,
        "hours_est": hours_est,
        "hours_breakdown": hours_breakdown,
        "overhead_rate_usd_h": overhead_rate_usd_h,
        "overhead_usd": overhead_usd,
        "coefs": coefs,
        "scenarios": to_scenarios(catalog, adjusted),
        "rate": float(catalog["moneda"]["usd_to_cop"])
    }