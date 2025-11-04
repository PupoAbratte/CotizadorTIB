import streamlit as st
from parser import parse_brief
from pricing import load_catalog, base_price_usd, apply_bundles, apply_coefs, to_scenarios, to_cop, explain, money
from storage import init_db, save_quote, list_quotes

st.set_page_config(page_title="Bravo — Cotizador", page_icon="💸", layout="wide")

@st.cache_resource
def _catalog():
    return load_catalog()

@st.cache_resource
def _init_db():
    init_db()
    return True

def ui_header():
    st.markdown("### This is Bravo · Cotizador de propuestas")
    st.caption("Detecta etapas desde un brief, aplica coeficientes, muestra rangos y guarda historial para estadísticas.")

def sidebar_inputs(catalog):
    with st.sidebar:
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
        "debug": mostrar_debug
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
        a_on = st.checkbox("A — Research", value=("A" in mod_levels))
        if a_on: mods["A"] = 1.0
        b_on = st.checkbox("B — Brand DNA", value=("B" in mod_levels))
        if b_on:
            b_lvl = st.selectbox("Nivel B", ["lite","full"], index=0 if mod_levels.get("B","lite")=="lite" else 1, key="b_lvl")
            mods["B"] = b_lvl
        c_on = st.checkbox("C — Creación", value=("C" in mod_levels))
        if c_on:
            c_lvl = st.selectbox("Nivel C", ["refresh","rebranding","full"], index=["refresh","rebranding","full"].index(mod_levels.get("C","full")), key="c_lvl")
            mods["C"] = c_lvl
    with colB:
        d_on = st.checkbox("D — Brandbook", value=("D" in mod_levels))
        if d_on:
            d_lvl = st.selectbox("Nivel D", ["lite","full"], index=0 if mod_levels.get("D","lite")=="lite" else 1, key="d_lvl")
            mods["D"] = d_lvl
        e_on = st.checkbox("E — Implementación", value=("E" in mod_levels))
        if e_on:
            e_lvl = st.selectbox("Nivel E", ["lite","full","plus"], index=["lite","full","plus"].index(mod_levels.get("E","full")), key="e_lvl")
            mods["E"] = e_lvl
    return mods

def main():
    _init_db()
    catalog = _catalog()
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