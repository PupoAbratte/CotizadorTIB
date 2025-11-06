import streamlit as st
from parser import parse_brief
from pricing import load_catalog, base_price_usd, apply_bundles, apply_coefs, to_scenarios, to_cop, explain, money
from storage import init_db, save_quote, list_quotes

st.set_page_config(page_title="Bravo – Cotizador", page_icon="💸", layout="wide")

@st.cache_resource
def _catalog():
    return load_catalog()

@st.cache_resource
def _init_db():
    init_db()
    return True

def apply_theme_styles(theme):
    """Aplica CSS personalizado según el tema seleccionado"""
    
    if theme == "Oscuro":
        colors = {
            "primary": "#FF1B15",
            "secondary": "#6B4FC1",
            "accent": "#C0B7F9",
            "background": "#0E0E0E",
            "surface": "#1A1A1A",
            "surface_hover": "#252525",
            "text": "#FFFFFF",
            "text_secondary": "#C0B7F9",
            "border": "#6B4FC1",
            "metric_bg": "#1A1A1A",
            "success": "#4CAF50",
            "info": "#6B4FC1",
            "warning": "#FF9800",
        }
    else:  # Claro
        colors = {
            "primary": "#220897",
            "secondary": "#FF1B15",
            "accent": "#6B4FC1",
            "background": "#FFFFFF",
            "surface": "#F8F8F8",
            "surface_hover": "#F0F0F0",
            "text": "#000000",
            "text_secondary": "#220897",
            "border": "#D9D9D9",
            "metric_bg": "#F4D4BD",
            "success": "#2E7D32",
            "info": "#220897",
            "warning": "#E65100",
        }
    
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Fuente global */
    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    
    /* Fondo principal */
    .stApp {{
        background-color: {colors['background']};
        color: {colors['text']};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {colors['surface']};
        border-right: 1px solid {colors['border']};
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: {colors['text']};
    }}
    
    /* Headers y títulos */
    h1, h2, h3, h4, h5, h6 {{
        color: {colors['text']} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {colors['surface']};
        padding: 8px;
        border-radius: 8px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        border-radius: 6px;
        color: {colors['text_secondary']};
        font-weight: 500;
        padding: 8px 16px;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {colors['surface_hover']};
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {colors['primary']} !important;
        color: #FFFFFF !important;
    }}
    
    /* Métricas */
    [data-testid="stMetricValue"] {{
        color: {colors['primary']} !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {colors['text']} !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }}
    
    [data-testid="metric-container"] {{
        background-color: {colors['metric_bg']};
        padding: 20px;
        border-radius: 12px;
        border: 1px solid {colors['border']};
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    
    /* Botones primarios */
    .stButton > button[kind="primary"] {{
        background-color: {colors['primary']};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: {colors['secondary']};
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}
    
    /* Botones secundarios */
    .stButton > button {{
        background-color: {colors['surface']};
        color: {colors['text']};
        border: 2px solid {colors['border']};
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.2s ease;
    }}
    
    .stButton > button:hover {{
        border-color: {colors['primary']};
        background-color: {colors['surface_hover']};
    }}
    
    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {{
        background-color: {colors['surface']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
    }}
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {colors['primary']};
        box-shadow: 0 0 0 1px {colors['primary']};
    }}
    
    /* Selectbox */
    [data-baseweb="select"] {{
        background-color: {colors['surface']};
    }}
    
    [data-baseweb="select"] > div {{
        background-color: {colors['surface']} !important;
        border-color: {colors['border']} !important;
    }}
    
    /* Number input */
    .stNumberInput > div > div > input {{
        background-color: {colors['surface']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
    }}
    
    /* Divider */
    hr {{
        border-color: {colors['border']};
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {colors['surface']};
        color: {colors['text']};
        border-radius: 8px;
        font-weight: 500;
    }}
    
    .streamlit-expanderHeader:hover {{
        background-color: {colors['surface_hover']};
    }}
    
    /* Success/Info/Warning boxes */
    .stSuccess {{
        background-color: {colors['success']}22;
        border-left: 4px solid {colors['success']};
        color: {colors['text']};
    }}
    
    .stInfo {{
        background-color: {colors['info']}22;
        border-left: 4px solid {colors['info']};
        color: {colors['text']};
    }}
    
    .stWarning {{
        background-color: {colors['warning']}22;
        border-left: 4px solid {colors['warning']};
        color: {colors['text']};
    }}
    
    /* Checkbox */
    .stCheckbox {{
        color: {colors['text']};
    }}
    
    /* Captions */
    .stCaption {{
        color: {colors['text_secondary']} !important;
        opacity: 0.8;
    }}
    
    /* DataFrames */
    .stDataFrame {{
        border: 1px solid {colors['border']};
        border-radius: 8px;
    }}
    
    /* Toggle especial para tema */
    [data-testid="stSidebar"] .stRadio > label {{
        font-weight: 600;
        color: {colors['text']};
        font-size: 0.95rem;
    }}
    
    /* Links */
    a {{
        color: {colors['primary']};
    }}
    
    a:hover {{
        color: {colors['secondary']};
    }}
    
    /* Markdown text */
    .stMarkdown {{
        color: {colors['text']};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def ui_header():
    st.markdown("### This is Bravo · Cotizador de propuestas")
    st.caption("Detecta etapas desde un brief, aplica coeficientes, muestra rangos y guarda historial para estadísticas.")

def sidebar_inputs(catalog):
    with st.sidebar:
        # Selector de tema al inicio del sidebar
        st.markdown("#### 🎨 Tema")
        theme = st.radio(
            "Selecciona el tema",
            options=["Oscuro", "Claro"],
            index=0,
            key="theme_selector",
            label_visibility="collapsed"
        )
        
        # Aplicar estilos según tema seleccionado
        apply_theme_styles(theme)
        
        st.divider()
        
        st.header("Parámetros del proyecto")
        cliente_nombre = st.text_input("Nombre del cliente", value="")
        cliente_tipo = st.selectbox("Tipo de cliente", ["corporativo","regional","pyme","emprendimiento","fundacion"], index=2)
        urgencia = st.selectbox("Urgencia", ["normal","rapida","express"], index=0)
        complejidad = st.selectbox("Complejidad", ["baja","media","alta"], index=1)
        idiomas = st.number_input("Idiomas (cantidad)", min_value=1, max_value=10, value=1, step=1)
        stakeholders = st.selectbox("Decisores", ["uno","dos","tres_o_mas"], index=0)
        relacion = st.selectbox("Relación", ["nuevo","recurrente"], index=0)
        st.divider()
        mostrar_debug = st.toggle("Mostrar debug (avanzado)", value=False)
    return {
        "cliente_nombre": cliente_nombre,
        "cliente_tipo": cliente_tipo,
        "urgencia": urgencia,
        "complejidad": complejidad,
        "idiomas": idiomas,
        "stakeholders": stakeholders,
        "relacion": relacion,
        "debug": mostrar_debug,
        "theme": theme
    }

def render_result_cards(catalog, adjusted_usd):
    S = to_scenarios(catalog, adjusted_usd)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Mínimo", f"USD {money(S['minimo'])}", help="Escenario conservador")
        st.write(f"~ COP {to_cop(catalog, S['minimo']):,}")
    with col2:
        st.metric("Lógico", f"USD {money(S['logico'])}", help="Precio recomendado")
        st.write(f"~ COP {to_cop(catalog, S['logico']):,}")
    with col3:
        st.metric("Máximo", f"USD {money(S['maximo'])}", help="Escenario premium / riesgo alto")
        st.write(f"~ COP {to_cop(catalog, S['maximo']):,}")
    return S

def render_edit_block(mod_levels):
    st.subheader("Editar visualmente antes de guardar")
    mods = {}
    colA, colB = st.columns(2)
    with colA:
        a_on = st.checkbox("A – Research", value=("A" in mod_levels))
        if a_on: mods["A"] = 1.0
        b_on = st.checkbox("B – Brand DNA", value=("B" in mod_levels))
        if b_on:
            b_lvl = st.selectbox("Nivel B", ["lite","full"], index=0 if mod_levels.get("B","lite")=="lite" else 1, key="b_lvl")
            mods["B"] = b_lvl
        c_on = st.checkbox("C – Creación", value=("C" in mod_levels))
        if c_on:
            c_lvl = st.selectbox("Nivel C", ["refresh","rebranding","full"], index=["refresh","rebranding","full"].index(mod_levels.get("C","full")), key="c_lvl")
            mods["C"] = c_lvl
    with colB:
        d_on = st.checkbox("D – Brandbook", value=("D" in mod_levels))
        if d_on:
            d_lvl = st.selectbox("Nivel D", ["lite","full"], index=0 if mod_levels.get("D","lite")=="lite" else 1, key="d_lvl")
            mods["D"] = d_lvl
        e_on = st.checkbox("E – Implementación", value=("E" in mod_levels))
        if e_on:
            e_lvl = st.selectbox("Nivel E", ["lite","full","plus"], index=["lite","full","plus"].index(mod_levels.get("E","full")), key="e_lvl")
            mods["E"] = e_lvl
    return mods

def main():
    _init_db()
    catalog = _catalog()
    
    # Inicializar tema por defecto si no existe
    if 'theme_selector' not in st.session_state:
        st.session_state.theme_selector = "Oscuro"
    
    ui_header()

    tabs = st.tabs(["🧮 Cotizador", "📊 Historial & Stats", "⚙️ Configuración/Debug"])

    with tabs[0]:
        params = sidebar_inputs(catalog)
        brief = st.text_area("Pegá el brief (texto libre)", height=180, placeholder="Contanos qué necesitan (p. ej., naming, concepto, logotipo, manual, pack de 8 piezas, lanzamiento en 3 semanas, etc.)")

        if st.button("Calcular", type="primary"):
            parsed = parse_brief(brief)
            mod_levels = parsed["modulos_pesos"]
            razones = parsed["razones"]

            base_usd = base_price_usd(catalog, mod_levels)
            base_usd = apply_bundles(catalog, mod_levels, base_usd)
            adjusted_usd, coefs = apply_coefs(
                catalog, base_usd,
                params["cliente_tipo"], params["urgencia"], params["complejidad"],
                int(params["idiomas"]), params["stakeholders"], params["relacion"]
            )

            st.success("Resultado")
            st.write(f"**Base (USD):** {money(base_usd)} → **Ajustado (USD):** {money(adjusted_usd)}")
            escenarios = render_result_cards(catalog, adjusted_usd)

            st.subheader("Resumen de etapas detectadas")
            st.write(explain(mod_levels, razones, coefs).replace("\n", "  \n"))

            with st.expander("Editar visualmente (opcional)"):
                edited = render_edit_block(mod_levels)
                if edited:
                    base2 = apply_bundles(catalog, edited, base_price_usd(catalog, edited))
                    adj2, coefs2 = apply_coefs(
                        catalog, base2,
                        params["cliente_tipo"], params["urgencia"], params["complejidad"],
                        int(params["idiomas"]), params["stakeholders"], params["relacion"]
                    )
                    st.info(f"Recalculo: Base USD {money(base2)} → Ajustado USD {money(adj2)}")
                    escenarios2 = render_result_cards(catalog, adj2)
                    if st.button("Guardar cotización (versión editada)"):
                        qid = save_quote(
                            params["cliente_nombre"], params["cliente_tipo"], brief,
                            edited, base2, adj2, escenarios2, coefs2
                        )
                        st.success(f"Guardado (# {qid})")
                else:
                    if st.button("Guardar cotización (detección automática)"):
                        qid = save_quote(
                            params["cliente_nombre"], params["cliente_tipo"], brief,
                            mod_levels, base_usd, adjusted_usd, escenarios, coefs
                        )
                        st.success(f"Guardado (# {qid})")

            if params["debug"]:
                with st.expander("Debug (oculto por defecto)"):
                    st.json(parsed)

    with tabs[1]:
        st.subheader("Historial de cotizaciones")
        rows = list_quotes(limit=200)
        if not rows:
            st.info("Aún no hay cotizaciones guardadas.")
        else:
            import pandas as pd, json
            data = []
            for (qid, ts, cname, ctype, base_usd, adj_usd, esc, mods) in rows:
                esc_d = json.loads(esc)
                data.append({
                    "ID": qid,
                    "Fecha": ts,
                    "Cliente": cname or "(s/d)",
                    "Tipo": ctype,
                    "Base USD": base_usd,
                    "Lógico USD": esc_d.get("logico"),
                    "Mínimo USD": esc_d.get("minimo"),
                    "Máximo USD": esc_d.get("maximo"),
                    "Módulos": mods
                })
            st.dataframe(pd.DataFrame(data))

            st.markdown("#### Indicadores rápidos")
            df = pd.DataFrame(data)
            st.write(f"- Cotizaciones guardadas: **{len(df)}**")
            if len(df):
                st.write(f"- Ticket medio (Lógico): **USD {df['Lógico USD'].mean():.2f}**")

    with tabs[2]:
        st.subheader("Catálogo (resumen)")
        P = catalog.get("precios", {})
        st.write(f"- A (Research): **USD {P.get('A',0):,.2f}**")
        st.write(f"- B (Brand DNA): **USD {P.get('B',0):,.2f}** (Lite = 0.6×)")
        st.write(f"- C (Creación): **Full {P.get('C_full',0):,.2f} · Rebranding {P.get('C_rebranding',0):,.2f} · Refresh {P.get('C_refresh',0):,.2f}**")
        st.write(f"- D (Brandbook): **Full {P.get('D_full',0):,.2f} · Lite {P.get('D_lite',0):,.2f}**")
        st.write(f"- E (Implementación): **Full {P.get('E_full',0):,.2f} · Lite {P.get('E_lite',0):,.2f} · Plus {P.get('E_plus',0):,.2f}**")
        st.caption("Nota: E_full se fijó en USD 600 como máximo (según tu ajuste).")

if __name__ == "__main__":
    main()