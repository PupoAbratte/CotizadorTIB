# pages/90_🔧_Tests.py — Suite de tests con tarjetas arriba y comprobaciones colapsables
import streamlit as st
from brief_parser import detect_module_weights, debug_parse
from pricing import (
    load_catalog, base_price_usd, apply_bundles, apply_coefs,
    to_scenarios, to_cop
)

st.set_page_config(page_title="Tests — Bravo Cotizador", layout="wide")

# === Estilos (mismo look & feel que app.py) ===
st.markdown("""
<style>
.bravo-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:8px;}
@media (max-width:1100px){.bravo-grid{grid-template-columns:1fr;}}
.bravo-card{background:#111418;border:1px solid #2a2f36;border-radius:14px;padding:16px;}
.bravo-card.primary{border-color:#3ff576;background:linear-gradient(180deg,#1a1f25,#14181d);}
.bravo-card .label{font-size:.85rem;color:#a6adbb;margin-bottom:4px;letter-spacing:.2px;}
.bravo-card .value{font-weight:700;font-size:1.6rem;line-height:1.2;}
.bravo-card .sub{font-size:.9rem;color:#8b93a2;margin-top:4px;}
.bravo-meta{
  margin: 22px 0 12px 0;
  padding: 14px 16px;
  background:#0f141a;
  border:1px solid #2a2f36;
  border-radius:12px;
  text-align:center;
  color:rgba(220,230,245,.9);
  font-size:1rem;
}
</style>
""", unsafe_allow_html=True)

# === Catálogo cacheado ===
@st.cache_resource
def _catalog():
    try:
        return load_catalog("catalog.json")
    except TypeError:
        return load_catalog()

CAT = _catalog()

CASES = {
    "A1 Auditoria completa": "Necesitamos una auditoria y benchmark competitivo con analisis de audiencia e insights accionables.",
    "B1 ADN Full": "Queremos definir el ADN de marca con proposito, arquetipo, territorios y storytelling.",
    "C1 Naming+Logo": "Necesitamos naming y un nuevo logo con concepto creativo.",
    "C2 Rebranding full": "Hacer rebranding de la identidad actual sin cambiar el nombre; evolucionar identidad y estilo.",
    "C3 Refresh": "Hacer un refresh del logo, modernizar colores y ajustar tipografia.",
    "D1 Brandbook full": "Manual de marca / brandbook completo con grillas, paleta y usos.",
    "D2 Lite": "Necesitamos paleta de color, tipografia y usos del logo (kit basico).",
    "E1 Pack lanzamiento": "Pack de 12 piezas para lanzamiento: social media, ppt, banners y brochure.",
    "E2 Lite": "Necesitamos 3 piezas: un banner, una firma de mail y un post de redes.",
    "Negaciones": "No cambiar logo ni hacer investigacion; solo naming.",
    "ONG C+D": "Fundacion: logo y manual basico (2-3 piezas).",
    "Lanzamiento sin piezas": "Habra lanzamiento pero sin materiales ni campania."
}

st.title("Suite de tests")

# === Inputs ===
cli = st.selectbox("Cliente", list(CAT["coeficientes"]["cliente"].keys()), index=2)
urg = st.selectbox("Urgencia", list(CAT["coeficientes"]["urgencia"].keys()), index=0)
comp = st.selectbox("Complejidad", list(CAT["coeficientes"]["complejidad"].keys()), index=1)
idi = st.number_input("Idiomas", 1, 6, 1)
stk = st.selectbox("Decisores", ["uno","dos","tres_o_mas"], index=0)
rel = st.selectbox("Relación", list(CAT["coeficientes"]["relacion"].keys()), index=0)

case_name = st.selectbox("Caso", list(CASES.keys()))
brief = st.text_area("Brief (editable)", value=CASES[case_name], height=150)

# Botón fijo justo debajo de los campos (queda ahí siempre)
run = st.button("Probar caso", use_container_width=True)

# Contenedores para controlar el orden
cards_top = st.container()      # Tarjetas arriba
checks_bottom = st.container()  # Comprobaciones (colapsables) debajo

# === Helper tarjetas ===
def render_result_cards(minimo, logico, maximo):
    usd_min = f"USD {minimo:,.2f}"; usd_log = f"USD {logico:,.2f}"; usd_max = f"USD {maximo:,.2f}"
    cop_min = f"~ COP {to_cop(CAT, minimo):,}"; cop_log = f"~ COP {to_cop(CAT, logico):,}"; cop_max = f"~ COP {to_cop(CAT, maximo):,}"
    st.markdown(f"""
    <div class="bravo-grid">
      <div class="bravo-card" aria-label="Precio mínimo">
        <div class="label">Mínimo</div>
        <div class="value">{usd_min}</div>
        <div class="sub">{cop_min}</div>
      </div>
      <div class="bravo-card primary" aria-label="Precio lógico">
        <div class="label">Lógico</div>
        <div class="value">{usd_log}</div>
        <div class="sub">{cop_log}</div>
      </div>
      <div class="bravo-card" aria-label="Precio máximo">
        <div class="label">Máximo</div>
        <div class="value">{usd_max}</div>
        <div class="sub">{cop_max}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# === Helper pretty views ===
def pretty_coefs(coefs: dict):
    labels = {
        "cliente": "Cliente",
        "urgencia": "Urgencia",
        "complejidad": "Complejidad",
        "idiomas": "Idiomas (factor)",
        "stakeholders": "Decisores",
        "relacion": "Relación",
        "total_coef": "Coeficiente total",
    }
    rows = []
    for k in ["cliente","urgencia","complejidad","idiomas","stakeholders","relacion","total_coef"]:
        if k in coefs:
            rows.append({"Factor": labels[k], "×": f"{float(coefs[k]):.2f}"})
    st.table(rows)

def pretty_mods(pesos: dict):
    etiquetas = {"A":"Research","B":"Brand DNA","C":"Creación","D":"Brandbook","E":"Implementación"}
    rows = []
    for m, w in pesos.items():
        rows.append({"Módulo": f"{m} — {etiquetas.get(m,m)}", "Peso": f"{float(w):.2f}"})
    st.table(rows)

def pretty_details(detalles: dict, razones: list):
    if not detalles and not razones:
        st.write("—")
        return
    bullets = []
    if detalles:
        mode = detalles.get("mode")
        if mode: bullets.append(f"**Modo:** {mode}")
        flags = []
        for f in ["has_naming","has_logo","wants_rebrand","wants_refresh"]:
            if f in detalles:
                flags.append(f"{f.replace('_',' ')}: {'sí' if detalles[f] else 'no'}")
        if flags: bullets.append("**Flags:** " + " · ".join(flags))
        strong = detalles.get("strong") or []
        if strong: bullets.append("**Claves detectadas:** " + ", ".join(strong))
    if razones:
        bullets.append("**Razones:** " + " | ".join(razones))
    st.markdown("\n\n".join([f"- {b}" for b in bullets]) or "—")

# === Acción ===
if run:
    # 1) Parse
    parsed = detect_module_weights(brief)
    pesos = parsed.get("modulos_pesos", {})
    razones = parsed.get("reasons", [])
    detalles = parsed.get("detalles") or debug_parse(brief)

    # 2) Pricing
    base_usd = base_price_usd(CAT, pesos)
    base_usd_bundled = apply_bundles(CAT, pesos, base_usd)
    adjusted_usd, coefs = apply_coefs(CAT, base_usd_bundled, cli, urg, comp, int(idi), stk, rel)
    escenarios = to_scenarios(CAT, adjusted_usd)

    # Tarjetas ARRIBA
    with cards_top:
        st.subheader("Escenarios")
        render_result_cards(
            escenarios.get("minimo") or escenarios.get("min") or 0.0,
            escenarios.get("logico") or escenarios.get("logic") or adjusted_usd,
            escenarios.get("maximo") or escenarios.get("max") or 0.0,
        )

    # Comprobaciones (colapsables) DEBAJO
    with checks_bottom:
        # Recuadro base (primero) y recién DEBAJO el título/expander
        st.markdown(
            f"<div class='bravo-meta'><b>Tarifa base (USD):</b> {base_usd_bundled:,.2f} → "
            f"<b>Ajustado (USD):</b> {adjusted_usd:,.2f}</div>",
            unsafe_allow_html=True
        )

        with st.expander("Base y coeficientes", expanded=False):
            pretty_coefs(coefs)

        with st.expander("Módulos", expanded=False):
            pretty_mods(pesos)

        with st.expander("Detalles", expanded=False):
            pretty_details(detalles, razones)