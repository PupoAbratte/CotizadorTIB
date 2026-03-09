# app.py — Cotizador (Streamlit)
# - UI: DM Sans + tema accesible con acento #6B4FC1 (dark/light 1-click)
# - Cotización + guardado en Google Sheets + PDF (wkhtmltopdf)
# - Código depurado: sin parser duplicado por keywords, entregables consistentes via brief_parser.get_deliverables()

import json
import os
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, List

import gspread
import pdfkit
import requests
import streamlit as st
from google.oauth2 import service_account
from jinja2 import Environment, FileSystemLoader, select_autoescape

from auth import require_login
from brief_parser import DELIVERABLES, get_deliverables, detect_module_weights
from ui import inject_font_and_base, inject_theme

# ===== Config =====
st.set_page_config(page_title="Cotizador — This is Bravo", layout="wide")

SHEET_ID = st.secrets["SHEET_ID"]
WORKSHEET_NAME = st.secrets.get("WORKSHEET_NAME", "Quotes")
DEBUG_UI = bool(st.secrets.get("DEBUG_UI", False))

HERE = Path(__file__).parent
CATALOG_PATH = HERE / "catalog.json"

# ===== Auth =====
inject_font_and_base()
require_login(session_hours=3)

if DEBUG_UI:
    st.sidebar.caption(f"DEBUG A.lite[0]: {DELIVERABLES['A']['lite'][0]}")

# ===== Importar pricing (opcional, con fallback) =====
try:
    import pricing as _pricing
except Exception as e:
    _pricing = None
    st.warning(f"No se pudo importar pricing.py (se usará cálculo básico): {e}")

# ===== Utilidades =====
def money(x: float) -> str:
    return f"{x:,.2f}"

def load_catalog_safely() -> Dict[str, Any]:
    if _pricing and hasattr(_pricing, "load_catalog") and callable(_pricing.load_catalog):
        try:
            return _pricing.load_catalog(str(CATALOG_PATH))
        except TypeError:
            return _pricing.load_catalog()
        except Exception:
            pass

    if not CATALOG_PATH.exists():
        st.error(f"No se encontró catalog.json en {CATALOG_PATH}")
        st.stop()

    with open(CATALOG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)

def scen_from(catalog: Dict[str, Any], adjusted_usd: float) -> Dict[str, float]:
    if _pricing and hasattr(_pricing, "to_scenarios") and callable(_pricing.to_scenarios):
        try:
            return _pricing.to_scenarios(catalog, adjusted_usd)
        except Exception:
            pass

    S = catalog.get("escenarios", {})
    minimo = float(S.get("minimo", 0.85))
    logico = float(S.get("logico", 1.0))
    maximo = float(S.get("maximo", 1.3))
    return {
        "minimo": round(adjusted_usd * minimo, 2),
        "logico": round(adjusted_usd * logico, 2),
        "maximo": round(adjusted_usd * maximo, 2),
    }

def to_cop_local(rate: float, usd: float) -> int:
    try:
        r = float(rate)
    except Exception:
        r = 4300.0
    return int(round(float(usd) * r, 0))

# ===== Helpers de niveles =====
def _nearly(x: float, target: float, tol: float = 0.05) -> bool:
    try:
        return abs(float(x) - float(target)) <= tol
    except Exception:
        return False

def _level_for(mod: str, weight: float) -> str:
    if mod == "A":
        # Research: 1.0=lite (benchmark), 1.5=full (auditoría), >=2.0=plus (insights)
        if _nearly(weight, 1.0): return "lite"
        if _nearly(weight, 1.5): return "full"
        if weight >= 2.0: return "plus"
        return "lite"
    if mod == "B":
        # B: 0.65 lite / 1.0 full (plus existe en librería, pero hoy no lo devolvés por parser)
        return "full" if weight >= 0.9 else "lite"
    if mod == "C":
        # C: 0.5 refresh / 0.8 rebranding / 1.0 full (naming se decide aparte)
        if _nearly(weight, 1.0): return "full"
        if _nearly(weight, 0.8): return "rebranding"
        if _nearly(weight, 0.5): return "refresh"
        return "full" if weight > 0.8 else ("rebranding" if weight > 0.6 else "refresh")
    if mod == "D":
        # D: 0.6 lite / 1.0 full
        return "full" if weight >= 0.9 else "lite"
    if mod == "E":
        # E: 0.6 lite / 1.0 full / 1.5 plus
        if weight >= 1.4: return "plus"
        if weight >= 0.9: return "full"
        return "lite"
    return "full"

def _normalize_txt(s: str) -> str:
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def infer_c_base_level(brief: str) -> str:
    """
    Decide si C debe ir como:
    - "full" (sin naming)
    - "full + naming" (con naming)
    Priorizamos negaciones (si el brief dice explícitamente que NO quiere naming).
    """
    t = _normalize_txt(brief or "")

    # 1) Negaciones (ganan siempre)
    neg_phrases = [
        "sin naming",
        "no naming",
        "sin nombre",
        "no incluye naming",
        "no requiere naming",
        "no necesitamos naming",
        "no es necesario naming",
        "no hacer naming",
        "no queremos naming",
        "nombre ya definido",
        "nombre ya esta definido",
        "nombre ya está definido",
        "ya tenemos nombre",
        "ya hay nombre",
        "nombre definido",
        "nombre existente",
        "ya existe el nombre",
        "el nombre ya existe",
        "solo logo",
        "solo logotipo",
        "solo isologotipo",
    ]
    if any(p in t for p in neg_phrases):
        return "full"

    # 2) Señales positivas (con sinónimos)
    # Nota: evitamos que "nombre" solo active naming; pedimos contexto/acción.
    pos_phrases = [
        "naming",
        "brand name",
        "name creation",
        "crear nombre",
        "crear el nombre",
        "creacion de nombre",
        "creación de nombre",
        "definir nombre",
        "definicion de nombre",
        "definición de nombre",
        "ponerle nombre",
        "bautizar",
        "bautizo de marca",
        "nombre de marca",
        "nombre comercial",
        "nombre para la marca",
        "denominacion",
        "denominación",
        "renombrar",
        "cambio de nombre",
        "re naming",
        "re-naming",
        "nueva denominacion",
        "nueva denominación",
        "desarrollo de nombre",
        "desarrollar nombre",
    ]
    if any(p in t for p in pos_phrases):
        return "full + naming"

    return "full"

def _display_level(mod: str, level_key: str, *, c_base_level: Optional[str] = None) -> str:
    """
    Devuelve el nombre "humano" del nivel para UI/PDF.
    - E: renombra a paquetes ("Kit básico", "Kit full", "Campaña lanzamiento")
    - C: si corresponde, muestra "full + naming"
    """
    mod = (mod or "").strip().upper()
    level_key = (level_key or "").strip().lower()

    if mod == "E":
        return {
            "lite": "Kit básico",
            "full": "Kit full",
            "plus": "Campaña lanzamiento",
        }.get(level_key, level_key)

    if mod == "C":
        if level_key == "full" and (c_base_level or "").strip().lower() == "full + naming":
            return "full + naming"
        return level_key

    return level_key


def _deliverables_for_module_level(mod: str, level: str, *, brief: str, c_base_level: Optional[str] = None) -> List[str]:
    """
    Única fuente de verdad para entregables imprimibles: brief_parser.get_deliverables().
    """
    if mod == "E":
        e_level = "Kit básico" if level == "lite" else ("Kit full" if level == "full" else "Campaña lanzamiento")
        return get_deliverables("E", e_level)

    if mod == "C":
        c_base = c_base_level or infer_c_base_level(brief)
        if level == "plus":
            return get_deliverables("C", "plus", c_base_level=c_base)
        if level == "full":
            return get_deliverables("C", c_base)  # "full" o "full + naming"
        if level == "lite":
            return get_deliverables("C", "lite")
        # refresh/rebranding (para pricing) → entregables conservadores
        if level == "refresh":
            return get_deliverables("C", "lite")
        if level == "rebranding":
            return get_deliverables("C", c_base)
        return get_deliverables("C", c_base)

    # A/B/D
    if level not in ("lite", "full", "plus"):
        level = "lite"
    return get_deliverables(mod, level)

def _build_deliverables_flat(mod_weights: Dict[str, float], *, brief: str, c_base_level: Optional[str] = None) -> List[str]:
    """
    Lista plana deduplicada de entregables (si querés un bloque único).
    Respeta reglas por módulo a través de get_deliverables().
    """
    if not isinstance(mod_weights, dict):
        return []

    orden = ["A", "B", "C", "D", "E"]
    seen = set()
    out: List[str] = []

    for mod in orden:
        w = mod_weights.get(mod)
        try:
            w = float(w)
        except Exception:
            continue
        if not w or w <= 0:
            continue

        lvl = _level_for(mod, w)
        items = _deliverables_for_module_level(mod, lvl, brief=brief, c_base_level=c_base_level)
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)

    return out

# ===== PDF / wkhtmltopdf helpers =====
def _pdfkit_config():
    env_path = os.environ.get("WKHTMLTOPDF_PATH")
    if env_path and os.path.exists(env_path):
        return pdfkit.configuration(wkhtmltopdf=env_path)

    which_path = shutil.which("wkhtmltopdf")
    if which_path:
        return pdfkit.configuration(wkhtmltopdf=which_path)

    for p in ["/usr/bin/wkhtmltopdf", "/usr/local/bin/wkhtmltopdf"]:
        if os.path.exists(p):
            return pdfkit.configuration(wkhtmltopdf=p)

    raise OSError(
        "wkhtmltopdf no está instalado en el entorno. "
        "En Streamlit Cloud, agregá un archivo 'packages.txt' con la línea 'wkhtmltopdf' y redeploy. "
        "Localmente, instalalo según tu sistema."
    )

def _safe_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    return s or "cotizacion"

def _build_quote_context_from_session(rate_display: float, rate_ars_display: float) -> dict:
    q = st.session_state.get("last_quote") or {}
    choice = st.session_state.get("selected_quote_name") or "Lógico"
    amount = float(st.session_state.get("selected_quote_amount") or q.get("logico", 0.0))
    pdf_currency = (st.session_state.get("pdf_currency") or "USD").upper()

    brief = q.get("brief", "")
    mod_weights = q.get("mod_weights", q.get("modulos_pesos", {})) or {}
    c_base_level = q.get("c_base_level", None)

    return dict(
        cliente_nombre=q.get("cliente_nombre", ""),
        brief=brief,
        scenario_name=choice,
        amount_usd=amount,
        rate_cop=float(rate_display or 0),
        rate_ars=float(rate_ars_display or 0),
        pdf_currency=pdf_currency,
        mod_weights=mod_weights,
        c_base_level=c_base_level,
        coefs=q.get("coefs", {}),
        estudio_nombre="This is Bravo",
        estudio_web="www.thisisbravo.co",
        estudio_mail="hola@thisisbravo.co",
        studio_logo_url="https://thisisbravo.co/wp-content/uploads/2025/11/logo.png",
        primary_hex="#6B4FC1",
        secondary_hex="#F4D4BD",
        validity_days=30,
        payment_terms="50% al inicio del proyecto. 50% restante contra entrega de los materiales.",
        validity_text="Esta propuesta tiene una validez de 30 días a partir de la fecha de emisión.",
        deliverables=_build_deliverables_flat(mod_weights, brief=brief, c_base_level=c_base_level),
    )

def save_and_generate_pdf(rate_display: float, rate_ars_display: float) -> bool:
    try:
        q = st.session_state.get("last_quote") or {}
        if not q:
            return False

        ok = save_quote_to_sheets(
            q["cliente_nombre"],
            q["cliente_tipo"], q["urgencia"], q["complejidad"], q["idiomas"],
            q["stakeholders"], q["relacion"], q["brief"],
            q["base_usd"], q["adjusted_usd"], q["minimo"], q["logico"], q["maximo"],
            tasa_cop_usd=rate_display,
        )
        if not ok:
            return False

        ctx = _build_quote_context_from_session(rate_display, rate_ars_display)
        body_html = render_quote_html(**ctx)

        tmp_dir = Path("tmp_assets")
        tmp_dir.mkdir(exist_ok=True)

        footer_html = render_quote_footer_html(
            estudio_nombre=ctx.get("estudio_nombre", "This is Bravo"),
            estudio_web=ctx.get("estudio_web", "www.thisisbravo.co"),
            estudio_mail=ctx.get("estudio_mail", "hola@thisisbravo.co"),
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8", dir=tmp_dir
        ) as tmp_footer:
            tmp_footer.write(footer_html)
            footer_path = tmp_footer.name

        footer_url = "file://" + footer_path

        options = {
            "encoding": "UTF-8",
            "page-size": "A4",
            "margin-top": "20mm",
            "margin-right": "16mm",
            "margin-bottom": "35mm",
            "margin-left": "16mm",
            "footer-html": footer_url,
            "footer-spacing": "5",
            "enable-local-file-access": "",
            "load-error-handling": "ignore",
            "custom-header": [(
                "User-Agent",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"
            )],
            "allow": str(tmp_dir.resolve()),
        }

        pdf_bytes = pdfkit.from_string(
            body_html,
            False,
            configuration=_pdfkit_config(),
            options=options,
        )

        st.session_state["last_pdf_bytes"] = pdf_bytes
        fecha = datetime.now().strftime("%Y%m%d")
        cliente_slug = _safe_filename(ctx.get("cliente_nombre") or "cliente")
        st.session_state["last_pdf_name"] = f"{fecha}_Cotizacion {cliente_slug}.pdf"

        try:
            if os.path.exists(footer_path):
                os.unlink(footer_path)
        except Exception:
            pass

        return True

    except Exception as e:
        st.error(f"No se pudo completar el guardado/generación: {type(e).__name__}: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False

# ===== Tasa de cambio en vivo (COP + ARS) =====
@st.cache_data(ttl=3600, show_spinner=False)
def get_live_usd_rates() -> Optional[Tuple[Dict[str, float], str]]:
    """Devuelve (rates_dict, fuente_str). Cache 1h. Intenta 2 APIs, si fallan: None."""
    try:
        resp = requests.get(
            "https://api.exchangerate.host/latest",
            params={"base": "USD", "symbols": "COP,ARS"},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
            rates = data.get("rates", {}) or {}
            cop = float(rates.get("COP"))
            ars = float(rates.get("ARS"))
            ts = data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
            return {"COP": cop, "ARS": ars}, f"exchangerate.host · {ts}"
    except Exception:
        pass

    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        if resp.ok:
            data = resp.json()
            rates = data.get("rates", {}) or {}
            cop = float(rates.get("COP"))
            ars = float(rates.get("ARS"))
            ts = data.get("time_last_update_utc") or datetime.utcnow().strftime("%Y-%m-%d")
            return {"COP": cop, "ARS": ars}, f"open.er-api.com · {ts}"
    except Exception:
        pass

    return None

# ===== Google Sheets =====
def _sheet_client():
    creds_info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    return gc, creds.service_account_email

def save_quote_to_sheets(
    cliente_nombre: str,
    cliente_tipo: str,
    urgencia: str,
    complejidad: str,
    idiomas: int,
    stakeholders: str,
    relacion: str,
    brief: str,
    base_usd: float,
    adjusted_usd: float,
    minimo: float,
    logico: float,
    maximo: float,
    *,
    tasa_cop_usd: float,
) -> bool:
    try:
        gc, _ = _sheet_client()
        sh = gc.open_by_key(SHEET_ID)

        try:
            ws = sh.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=26)
            ws.append_row(
                [
                    "Fecha","Cliente","Tipo","Brief","Precio base USD",
                    "Min USD","Base USD","Max USD","tasa_cop_usd_usada","Notas",
                    "Cotizacion final","Escenario elegido","Monto elegido USD","Monto elegido COP"
                ],
                value_input_option="RAW",
            )

        headers = [h.strip() for h in ws.row_values(1)]
        header_to_payload_key = {
            "Fecha": "created_local",
            "Cliente": "cliente_nombre",
            "Tipo": "cliente_tipo",
            "Brief": "brief",
            "Precio base USD": "base_usd",
            "Min USD": "minimo_usd",
            "Base USD": "logico_usd",
            "Max USD": "maximo_usd",
            "Cotización elegida": "monto_elegido_usd",
            "tasa_cop_usd_usada": "tasa_cop_usd_usada",
            "Notas": "notas",
            "Cotizacion final": "cotizacion_final_usd",
            "Escenario elegido": "escenario_elegido",
            "Monto elegido USD": "monto_elegido_usd",
            "Monto elegido COP": "monto_elegido_cop",
        }

        local_now = datetime.now()
        payload = {
            "created_local": local_now.isoformat(timespec="seconds"),
            "cliente_nombre": (cliente_nombre or "").strip(),
            "cliente_tipo": cliente_tipo,
            "brief": (brief or "").strip(),
            "base_usd": float(base_usd),
            "ajustado_usd": float(adjusted_usd),
            "minimo_usd": float(minimo),
            "logico_usd": float(logico),
            "maximo_usd": float(maximo),
            "tasa_cop_usd_usada": float(tasa_cop_usd or 0),
            "notas": "",
            "cotizacion_final_usd": "",
        }

        choice = st.session_state.get("selected_quote_name", "")
        chosen_usd = float(st.session_state.get("selected_quote_amount") or 0)
        chosen_cop = to_cop_local(tasa_cop_usd, chosen_usd)
        payload.update({
            "escenario_elegido": choice,
            "monto_elegido_usd": chosen_usd,
            "monto_elegido_cop": chosen_cop,
        })

        row = []
        for h in headers:
            key = header_to_payload_key.get(h)
            row.append(payload.get(key, ""))

        # Primera fila vacía real (ancla Col A)
        from gspread.utils import rowcol_to_a1

        max_rows = ws.row_count
        col_a_values = ws.get(f"A1:A{max_rows}")
        col_a_formulas = ws.get(f"A1:A{max_rows}", value_render_option="FORMULA")

        last_used = 1  # header
        for i in range(2, max_rows + 1):
            v = (col_a_values[i - 1][0] if i - 1 < len(col_a_values) and col_a_values[i - 1] else "")
            f = (col_a_formulas[i - 1][0] if i - 1 < len(col_a_formulas) and col_a_formulas[i - 1] else "")

            v_norm = str(v).replace("\u00a0", " ").strip()
            f_norm = str(f).strip()

            if v_norm != "" or (f_norm.startswith("=") and f_norm != "="):
                last_used = i

        next_row = last_used + 1
        start = rowcol_to_a1(next_row, 1)
        end = rowcol_to_a1(next_row, len(headers))

        ws.update(f"{start}:{end}", [row], value_input_option="USER_ENTERED")
        return True

    except gspread.SpreadsheetNotFound:
        st.error("No se encontró el Sheet por ID. Verificá SHEET_ID y compartí el Sheet con la cuenta de servicio (Editor).")
    except Exception as e:
        st.exception(e)
    return False

# ===== Cálculo de cotización (fallback si falta pricing.py) =====
def safe_compute_quote(catalog: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    if _pricing and hasattr(_pricing, "compute_quote") and callable(_pricing.compute_quote):
        try:
            return _pricing.compute_quote(catalog, features)
        except Exception as e:
            st.warning(f"compute_quote falló, se usa cálculo básico: {e}")

    mods_cfg = catalog.get("modulos", {})
    weights: Dict[str, float] = features.get("modulos_pesos", {})
    base = 0.0

    for m, w in weights.items():
        cfg = mods_cfg.get(m, {})
        price = float(cfg.get("precio_base_usd", 0.0))
        if m == "E" and float(w) >= 1.0:
            price = min(price, 600.0)
        base += price * float(w)

    base = round(base, 2)

    def _normalize(s: str) -> str:
        s = str(s).strip().lower()
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    def keymatch(d: dict, key: str, default=1.0):
        if not isinstance(d, dict):
            return default
        key_n = _normalize(key)
        for k, v in d.items():
            if _normalize(k) == key_n:
                return v
        return d.get(key, default)

    C = catalog.get("coeficientes", {})
    c_cliente = float(keymatch(C.get("cliente", {}), features.get("cliente_tipo", "PyME"), 1.0))
    c_urg = float(keymatch(C.get("urgencia", {}), features.get("urgencia", "Normal"), 1.0))
    c_comp = float(keymatch(C.get("complejidad", {}), features.get("complejidad", "Media"), 1.0))
    c_rel = float(keymatch(C.get("relacion", {}), features.get("relacion", "Nuevo"), 1.0))

    idiomas_total = int(features.get("idiomas", 1))
    c_id_base = float(C.get("idiomas", {}).get("base", 1.0))
    c_id_extra = float(C.get("idiomas", {}).get("extra", 0.0))
    c_id = c_id_base + max(0, idiomas_total - 1) * c_id_extra

    stks = features.get("stakeholders", "uno")
    st_map = C.get("stakeholders", {})
    if isinstance(stks, int):
        if stks <= 1:
            c_st = 1.0
        elif stks == 2:
            c_st = float(keymatch(st_map, "dos", 1.04))
        else:
            c_st = float(keymatch(st_map, "tres_o_mas", 1.08))
    else:
        c_st = float(keymatch(st_map, stks, 1.0))

    total_coef = c_cliente * c_urg * c_comp * c_id * c_st * c_rel
    total_coef = min(total_coef, float(C.get("tope_total_coef", 1.4)))

    adjusted = round(base * total_coef, 2)
    return {
        "base_usd": base,
        "adjusted_usd": adjusted,
        "coefs": {
            "cliente": c_cliente,
            "urgencia": c_urg,
            "complejidad": c_comp,
            "idiomas": round(c_id, 3),
            "stakeholders": round(c_st, 3),
            "relacion": c_rel,
            "total_coef": round(total_coef, 3),
        },
        "scenarios": scen_from(catalog, adjusted),
    }

# ===== Render UI helpers =====
def render_result_cards(minimo, logico, maximo, base_usd, adjusted_usd, rate_display, rate_ars_display):
    st.markdown(
        f"<div class='bravo-meta'><b>Tarifa base: US$</b> {base_usd:,.2f}</div>",
        unsafe_allow_html=True,
    )

    usd_min = f"USD {minimo:,.2f}"
    usd_log = f"USD {logico:,.2f}"
    usd_max = f"USD {maximo:,.2f}"

    cop_min = f"~ COP {to_cop_local(rate_display, minimo):,}"
    cop_log = f"~ COP {to_cop_local(rate_display, logico):,}"
    cop_max = f"~ COP {to_cop_local(rate_display, maximo):,}"

    if rate_ars_display and float(rate_ars_display) > 0:
        ars_min = f"~ ARS {int(round(float(minimo) * float(rate_ars_display))):,}"
        ars_log = f"~ ARS {int(round(float(logico) * float(rate_ars_display))):,}"
        ars_max = f"~ ARS {int(round(float(maximo) * float(rate_ars_display))):,}"
    else:
        ars_min = "~ ARS N/D"
        ars_log = "~ ARS N/D"
        ars_max = "~ ARS N/D"

    st.markdown(
        f"""
<div class="bravo-grid">
  <div class="bravo-card" aria-label="Precio mínimo">
    <div class="label">Mínimo</div>
    <div class="value">{usd_min}</div>
    <div class="sub">{cop_min} · {ars_min}</div>
  </div>
  <div class="bravo-card" aria-label="Precio lógico">
    <div class="label">Lógico</div>
    <div class="value">{usd_log}</div>
    <div class="sub">{cop_log} · {ars_log}</div>
  </div>
  <div class="bravo-card" aria-label="Precio máximo">
    <div class="label">Máximo</div>
    <div class="value">{usd_max}</div>
    <div class="sub">{cop_max} · {ars_max}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_catalog_summary(catalog: Dict[str, Any]):
    st.subheader("Catálogo de costos    ")
    P = catalog.get("precios")
    if isinstance(P, dict) and P:
        a = float(P.get("A", 0)); b = float(P.get("B", 0))
        c_full = float(P.get("C_full", P.get("C", 0)))
        c_reb  = float(P.get("C_rebranding", 0))
        c_ref  = float(P.get("C_refresh", 0))
        d_full = float(P.get("D_full", P.get("D", 0)))
        d_lite = float(P.get("D_lite", 0))
        e_full = float(P.get("E_full", P.get("E", 0)))
        e_lite = float(P.get("E_lite", 0))
        e_plus = float(P.get("E_plus", 0))
        st.markdown(f"- A (Investigación): **USD {a:,.2f}**")
        st.markdown(f"- B (ADN de marca): **USD {b:,.2f}**")
        st.markdown(f"- C (Creación): **Full {c_full:,.2f} · Rebranding {c_reb:,.2f} · Refresh {c_ref:,.2f}**")
        st.markdown(f"- D (Manuales y guías de estilo): **Full {d_full:,.2f}** · **Lite {d_lite:,.2f}**")
        st.markdown(f"- E (Producción): **Kit full {e_full:,.2f} · Kit básico {e_lite:,.2f} · Campaña lanzamiento {e_plus:,.2f}**  _(tope full = 600)_")
        return

    mods = catalog.get("modulos", {})
    a = float(mods.get("A", {}).get("precio_base_usd", 0))
    b = float(mods.get("B", {}).get("precio_base_usd", 0))
    c = float(mods.get("C", {}).get("precio_base_usd", 0))
    d = float(mods.get("D", {}).get("precio_base_usd", 0))
    e = float(mods.get("E", {}).get("precio_base_usd", 0))
    st.markdown(f"- A (Investigación): **USD {a:,.2f}**")
    st.markdown(f"- B (ADN de marca): **USD {b:,.2f}**")
    st.markdown(f"- C (Creación base): **USD {c:,.2f}** · Rebranding=0.8× · Refresh=0.5×")
    st.markdown(f"- D (Manuales y guías de estilo): **USD {d:,.2f}** · Lite=0.6×")
    st.markdown(f"- E (Producción): **USD {e:,.2f}** · Kit básico=0.6× · Campaña lanzamiento=1.5×  _(tope full = 600)_")

def render_quote_html(
    *,
    cliente_nombre: str,
    brief: str,
    scenario_name: str,
    amount_usd: float,
    rate_cop: float,
    rate_ars: float = 0.0,
    pdf_currency: str = "USD",
    mod_weights: Dict[str, float],
    c_base_level: Optional[str] = None,
    coefs: Dict[str, float],
    validity_days: int = 30,
    estudio_nombre: str = "This is Bravo",
    estudio_web: str = "www.thisisbravo.co",
    estudio_mail: str = "hola@thisisbravo.co",
    studio_logo_url: str = "https://thisisbravo.co/wp-content/uploads/2025/11/logo.png",
    primary_hex: str = "#6B4FC1",
    secondary_hex: str = "#F4D4BD",
    deliverables: Optional[list] = None,
    payment_terms: str = "50% al inicio del proyecto. 50% restante contra entrega de los materiales.",
    validity_text: str = "Esta propuesta tiene una validez de 30 días a partir de la fecha de emisión.",
) -> str:
    _meses_titulo = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    hoy = datetime.now()
    fecha_emision = f"{hoy.day:02d} de {_meses_titulo[hoy.month-1]} de {hoy.year}"

    try:
        amount_cop = int(round(float(amount_usd) * float(rate_cop), 0))
    except Exception:
        amount_cop = 0

    try:
        amount_ars = int(round(float(amount_usd) * float(rate_ars), 0))
    except Exception:
        amount_ars = 0

    pdf_currency = (pdf_currency or "USD").upper()

    if pdf_currency == "COP":
        scenario_amount_main = f"COP {amount_cop:,}"
    elif pdf_currency == "ARS":
        scenario_amount_main = f"ARS {amount_ars:,}" if amount_ars else "ARS N/D"
    else:
        scenario_amount_main = f"USD {amount_usd:,.2f}"

    intro_text = (
        "A continuación presentamos el detalle del proyecto: "
        "las etapas, tareas y entregables que darán forma al trabajo, "
        "junto con los honorarios correspondientes."
    )

    etiquetas = {"A": "Investigación", "B": "ADN de marca", "C": "Creación", "D": "Manuales y guías de estilo", "E": "Producción"}
    breakdown = []

    c_base = c_base_level or infer_c_base_level(brief)

    for k, w in (mod_weights or {}).items():
        try:
            w = float(w)
        except Exception:
            continue
        if w <= 0:
            continue

        level_key = _level_for(k, w)
        level_ui = _display_level(k, level_key, c_base_level=c_base)

        breakdown.append(
            {
                "modulo": k,
                "nombre": etiquetas.get(k, k),
                "nivel": level_ui,
                "nivel_key": level_key,
            }
        )

    # Acciones/entregables por bloque via get_deliverables()
    c_base = c_base_level or infer_c_base_level(brief)
    acciones_expand = []

    # Orden lógico
    for mod in ["A", "B", "C", "D", "E"]:
        w = (mod_weights or {}).get(mod)
        if not w:
            continue
        try:
            w = float(w)
        except Exception:
            continue
        if w <= 0:
            continue

        lvl = _level_for(mod, w)
        try:
            entregables = _deliverables_for_module_level(mod, lvl, brief=brief, c_base_level=c_base)
        except Exception:
            entregables = []

        if entregables:
            acciones_expand.append({"accion": etiquetas.get(mod, mod), "entregables": entregables})

    env = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template("quote.html")

    context = {
        "studio_name": estudio_nombre,
        "studio_site": estudio_web,
        "studio_email": estudio_mail,
        "studio_logo_url": studio_logo_url,
        "primary_hex": primary_hex,
        "secondary_hex": secondary_hex,
        "fecha_emision": fecha_emision,
        "client_name": cliente_nombre or "",
        "intro_text": intro_text,
        "scenario_name": scenario_name,
        "scenario_amount_main": scenario_amount_main,
        "scenario_amount_sub1": "",
        "scenario_amount_sub2": "",
        "breakdown": breakdown,
        "deliverables": deliverables or [],
        "payment_terms": payment_terms,
        "validity_text": validity_text,
        "coefs": coefs or {},
        "acciones_expand": acciones_expand,
    }
    return tpl.render(**context)

def render_quote_footer_html(
    *,
    estudio_nombre: str = "This is Bravo",
    estudio_web: str = "www.thisisbravo.co",
    estudio_mail: str = "hola@thisisbravo.co",
    estudio_eslogan="LATAM BRAND STUDIO",
    studio_logo_url: str = "https://thisisbravo.co/wp-content/uploads/2025/11/logo-2.png",
    **kwargs
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template("quote_footer.html")
    context = {
        "studio_name": estudio_nombre,
        "studio_site": estudio_web,
        "studio_email": estudio_mail,
        "studio_logo_url": studio_logo_url,
        "studio_slogan": estudio_eslogan,
    }
    return tpl.render(**context)

# ===== Estado base =====
if "last_quote" not in st.session_state:
    st.session_state["last_quote"] = None

def clear_quote_state() -> None:
    for k in [
        "cliente_nombre", "brief_text",
        "f_cliente_tipo", "f_urgencia", "f_complejidad", "f_idiomas", "f_stakeholders", "f_relacion",
        "last_quote", "selected_quote_name", "selected_quote_amount",
        "quote_choice_radio", "pdf_currency",
        "last_pdf_bytes", "last_pdf_name",
        "btn_calcular", "btn_reset",
    ]:
        st.session_state.pop(k, None)

# ===== Cargar catálogo =====
catalog = load_catalog_safely()

# ===== Sidebar: tasas + tema =====
catalog_rate_cop = float(
    catalog.get("moneda", {}).get("usd_to_cop", catalog.get("cop_per_usd", catalog.get("tasa_cop", 4300)))
)
catalog_rate_ars = float(catalog.get("moneda", {}).get("usd_to_ars", 0) or 0)

live = get_live_usd_rates()
if live:
    rates, rate_source = live
    rate_display = float(rates.get("COP", catalog_rate_cop) or catalog_rate_cop)
    rate_ars_display = float(rates.get("ARS", catalog_rate_ars) or catalog_rate_ars)
else:
    rate_display = catalog_rate_cop
    rate_ars_display = catalog_rate_ars
    rate_source = "catálogo (fallback)"

with st.sidebar:
    st.header("Tasa de cambio")
    ars_line = f"**{money(rate_ars_display)} ARS / USD**" if rate_ars_display else "**ARS / USD: N/D**"
    st.caption(
        f"**{money(rate_display)} COP / USD**  \n"
        f"{ars_line}  \n"
        f"<span style='opacity:.75'>{rate_source}</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    if "theme_dark" not in st.session_state:
        st.session_state["theme_dark"] = True
    st.toggle("Modo oscuro", key="theme_dark")
    theme_mode = "dark" if st.session_state["theme_dark"] else "light"

inject_theme(theme_mode)

# ===== UI principal =====
st.title("Cotizador — This is Bravo")

hint_box = st.empty()
if not st.session_state.get("last_quote"):
    hint_box.info("Cargá un brief y presioná **Calcular** para ver resultados.")
else:
    hint_box.empty()

left_col, right_col = st.columns([7, 5])

with left_col:
    st.markdown("### Brief")
    with st.container(border=True):
        cliente_nombre = st.text_input("Cliente", placeholder="Ej: ACME SA", key="cliente_nombre")
        brief = st.text_area(
            "Alcance del proyecto",
            height=220,
            placeholder="Ej: Re-branding regional, manual de identidad full, pack de 12 piezas, listo en 3 semanas…",
            key="brief_text",
        )

    btn_col1, btn_col2, spacer = st.columns([1, 1, 6], gap="small")
    with btn_col1:
        calcular = st.button("Calcular", key="btn_calcular", type="primary")
    with btn_col2:
        reset = st.button("Limpiar", key="btn_reset", type="secondary")

with right_col:
    st.markdown("### Parámetros")
    c1, c2 = st.columns(2)
    with c1:
        cliente_tipo = st.selectbox(
            "Tipo de cliente",
            ["Corporativo", "Regional", "PyME", "Emprendimiento", "Startup", "Fundacion"],
            index=2,
            help="Tipo y tamaño de la organización",
            key="f_cliente_tipo",
        )
    with c2:
        urgencia = st.selectbox(
            "Urgencia",
            ["Normal", "Rapida", "Express"],
            index=0,
            help="Nivel de urgencia del proyecto",
            key="f_urgencia",
        )
    c3, c4 = st.columns(2)
    with c3:
        complejidad = st.selectbox(
            "Complejidad",
            ["Baja", "Media", "Alta"],
            index=1,
            help="Complejidad técnica del proyecto",
            key="f_complejidad",
        )
    with c4:
        idiomas = st.number_input(
            "Idiomas (total)",
            min_value=1, max_value=10, value=1, step=1,
            help="Total de idiomas a producir",
            key="f_idiomas",
        )
    c5, c6 = st.columns(2)
    with c5:
        stakeholders = st.selectbox(
            "Decisores",
            ["uno", "dos", "tres_o_mas"],
            index=0,
            format_func=lambda x: {"uno": "1", "dos": "2", "tres_o_mas": "3+"}.get(x, x),
            help="Número de instancias de aprobación.",
            key="f_stakeholders",
        )
    with c6:
        relacion = st.selectbox(
            "Relación",
            ["Nuevo", "Recurrente"],
            index=0,
            help="Tipo de relación con el cliente",
            key="f_relacion",
        )

if reset:
    clear_quote_state()
    st.rerun()

# ===== Secciones (orden controlado) =====
result_section = st.container()
checks_section = st.container()

def render_checks(q: Dict[str, Any]):
    with checks_section:
        st.subheader("Comprobaciones")
        etiquetas = {"A": "Research", "B": "Brand DNA", "C": "Creación", "D": "Brandbook", "E": "Producción"}

        c_base_level = q.get("c_base_level") or infer_c_base_level(q.get("brief", ""))

        partes = []
        for m, w in (q.get("mod_weights") or {}).items():
            try:
                w = float(w)
            except Exception:
                continue
            if not w or w <= 0:
                continue
            lvl_key = _level_for(m, w)
            lvl = _display_level(m, lvl_key, c_base_level=c_base_level)
            partes.append(f"{m}: {etiquetas.get(m, m)} ({lvl}).")

        st.caption("Resumen de etapas detectadas: " + (" • ".join(partes) if partes else "—"))

        with st.expander("Detección de módulos", expanded=False):
            st.json(q.get("mod_weights", {}))
            if q.get("reasons"):
                st.caption("Razones: " + " | ".join(q["reasons"]))

        with st.expander("Coeficientes aplicados", expanded=False):
            st.json(q.get("coefs", {}))


def render_result_ui(q: Dict[str, Any], rate_display: float, rate_ars_display: float):
    st.subheader("Resultado")
    render_result_cards(
        q["minimo"], q["logico"], q["maximo"],
        q["base_usd"], q["adjusted_usd"],
        rate_display, rate_ars_display
    )

    with st.form("quote_actions"):
        st.markdown("#### Elegí una opción")
        opciones = {"Mínimo": q["minimo"], "Lógico": q["logico"], "Máximo": q["maximo"]}
        default_idx_map = {"Mínimo": 0, "Lógico": 1, "Máximo": 2}
        default_idx = default_idx_map.get(st.session_state.get("selected_quote_name", "Lógico"), 1)

        choice = st.radio(
            "Opción de cotización",
            options=list(opciones.keys()),
            horizontal=True,
            index=default_idx,
            key="quote_choice_radio",
            label_visibility="collapsed",
        )

        st.selectbox(
            "Moneda del PDF",
            ["USD", "COP", "ARS"],
            index=["USD", "COP", "ARS"].index(st.session_state.get("pdf_currency", "USD")),
            key="pdf_currency",
            help="Define en qué moneda se mostrará el monto principal del PDF.",
        )

        submit = st.form_submit_button("Guardar cotización", use_container_width=True)

    st.session_state["selected_quote_name"] = choice
    st.session_state["selected_quote_amount"] = float(opciones[choice])
    st.caption(f"Opción elegida: **{choice}** — **USD {opciones[choice]:,.2f}**")

    if submit:
        ok = save_and_generate_pdf(rate_display, rate_ars_display)
        if ok:
            st.success("Cotización guardada y PDF generado. Abajo podés bajarlo.")

    if st.session_state.get("last_pdf_bytes"):
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.download_button(
            "Bajar PDF",
            data=st.session_state["last_pdf_bytes"],
            file_name=st.session_state.get("last_pdf_name", "cotizacion.pdf"),
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf_btn",
        )

# ===== Lógica principal =====
if calcular:
    if not (brief or "").strip():
        st.warning("Escribí un brief para continuar.")
    else:
        st.session_state.pop("last_pdf_bytes", None)
        st.session_state.pop("last_pdf_name", None)

        parsed = detect_module_weights(brief)
        mod_weights = parsed.get("modulos_pesos", {}) or {}

        if not mod_weights:
            st.warning("No detecté módulos en el brief. Sumá señales claras (benchmark, ADN, logo, manual, aplicaciones, etc.) y volvé a calcular.")
        else:
            c_base_level = infer_c_base_level(brief)

            features = {
                "modulos_pesos": mod_weights,
                "cliente_tipo": cliente_tipo,
                "urgencia": urgencia,
                "complejidad": complejidad,
                "idiomas": int(idiomas),
                "stakeholders": stakeholders,
                "relacion": relacion,
                "c_base_level": c_base_level,  # <-- clave para sumar C_naming si aplica
            }

            result = safe_compute_quote(catalog, features)
            base_usd = float(result.get("base_usd", 0.0))
            adjusted_usd = float(result.get("adjusted_usd", 0.0))
            coefs = result.get("coefs", {})
            scenarios = result.get("scenarios", {})

            minimo = scenarios.get("min") or scenarios.get("minimo") or 0.0
            logico = scenarios.get("logic") or scenarios.get("logico") or adjusted_usd
            maximo = scenarios.get("max") or scenarios.get("maximo") or 0.0

            reasons = parsed.get("reasons", parsed.get("razones", [])) or []
            c_base_level = infer_c_base_level(brief)

            st.session_state["last_quote"] = {
                "cliente_nombre": (cliente_nombre or "").strip(),
                "cliente_tipo": cliente_tipo,
                "urgencia": urgencia,
                "complejidad": complejidad,
                "idiomas": int(idiomas),
                "stakeholders": stakeholders,
                "relacion": relacion,
                "brief": (brief or "").strip(),
                "base_usd": float(base_usd),
                "adjusted_usd": float(adjusted_usd),
                "minimo": float(minimo),
                "logico": float(logico),
                "maximo": float(maximo),
                "mod_weights": mod_weights,
                "c_base_level": c_base_level,
                "coefs": coefs,
                "reasons": reasons,
            }

            st.session_state["selected_quote_name"] = st.session_state.get("selected_quote_name", "Lógico")
            st.session_state["selected_quote_amount"] = {
                "Mínimo": minimo, "Lógico": logico, "Máximo": maximo
            }.get(st.session_state["selected_quote_name"], logico)

            hint_box.empty()
            st.divider()

            q = st.session_state["last_quote"]
            with result_section:
                render_result_ui(q, rate_display, rate_ars_display)
            render_checks(q)

elif st.session_state.get("last_quote"):
    q = st.session_state["last_quote"]
    with result_section:
        render_result_ui(q, rate_display, rate_ars_display)
    render_checks(q)

# ===== Catálogo al pie =====
render_catalog_summary(catalog)
