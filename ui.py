# ui.py
import streamlit as st

def setup_ui(*, page_title="Cotizador — This is Bravo", layout="wide", session_hours=3):
    from auth import require_login

    st.set_page_config(page_title=page_title, layout=layout)

    inject_font_and_base()

    # Mantiene el comportamiento actual del toggle global
    if "theme_dark" not in st.session_state:
        st.session_state["theme_dark"] = True
    theme_mode = "dark" if st.session_state["theme_dark"] else "light"
    inject_theme(theme_mode)

    require_login(session_hours=session_hours)


def inject_font_and_base() -> None:
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
  /* Forzar DM Sans global (pisar Source Sans de Streamlit/emotion) */
  html, body,
  [data-testid="stAppViewContainer"],
  [data-testid="stSidebar"],
  [class^="st-emotion-cache"],
  [class^="st-emotion-cache"] * {
    font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
  }

  /* Mantener monospace donde corresponde */
  code, pre, kbd, samp {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
  }

  /* Ajustes tipográficos */
  h1, h2, h3, h4 { font-weight: 700 !important; }
  h1 { font-size: 2rem !important; }
  h2 { font-size: 1.5rem !important; }
  h3 { font-size: 1.25rem !important; }

  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
</style>
""",
        unsafe_allow_html=True,
    )


def inject_theme(mode: str = "dark") -> None:
    """
    Tema con contraste AA, jerarquía clara y acento #6B4FC1.
    Hover del acento: #C0B7F9. Radio global: 8px.
    """

    if mode == "dark":
        css_vars = """
:root{
  --bg:#0B0F14;
  --surface:#111827;
  --surface-2:#0F172A;
  --surface-hover:#1F2937;

  --text:#E5E7EB;
  --text-secondary:#F3F4F6;
  --text-muted:#A7B0BF;
  --text-disabled:#8A93A3;

  --border:#1F2937;
  --border-strong:#2B3645;

  --accent:#6B4FC1;
  --accent-hover:#C0B7F9;
  --ring:#60A5FA;

  --radius:8px;

  --shadow:0 4px 6px -1px rgba(0,0,0,.45), 0 2px 4px -2px rgba(0,0,0,.35);
  --shadow-lg:0 10px 15px -3px rgba(0,0,0,.55), 0 4px 6px -4px rgba(0,0,0,.45);
}
"""
    else:
        css_vars = """
:root{
  --bg:#FFFFFF;
  --surface:#F8FAFC;
  --surface-2:#EEF2F7;
  --surface-hover:#E5EAF1;

  --text:#111827;
  --text-secondary:#0A0A0A;
  --text-muted:#475569;
  --text-disabled:#94A3B8;

  --border:#D1D9E6;
  --border-strong:#C0CADB;

  --accent:#6B4FC1;
  --accent-hover:#C0B7F9;
  --ring:#3B82F6;

  --radius:8px;

  --shadow:0 1px 3px 0 rgba(0,0,0,.10), 0 1px 2px -1px rgba(0,0,0,.08);
  --shadow-lg:0 10px 15px -3px rgba(0,0,0,.12), 0 4px 6px -4px rgba(0,0,0,.10);
}
"""

    st.markdown(
        "<style>\n"
        + css_vars
        + r"""
/* ===== BASE ===== */
[data-testid="stAppViewContainer"]{
  background:var(--bg);
  color:var(--text);
  transition: background-color 0.25s ease, color 0.25s ease;
}
[data-testid="stSidebar"]{
  background:var(--surface-2);
  color:var(--text);
  border-right:1px solid var(--border);
  transition: background-color 0.25s ease, color 0.25s ease;
}
[data-testid="stSidebar"] *{ color:var(--text); }

/* ===== BUTTONS ===== */
/* Primary */
[data-testid="stBaseButton-primary"] button,
[data-testid="baseButton-primary"] button,
button[data-testid="baseButton-primary"],
button[data-testid="stBaseButton-primary"],
.stDownloadButton>button{
  background:var(--accent) !important;
  color:#FFFFFF !important;
  border:1px solid var(--accent-hover) !important;
  border-radius:var(--radius) !important;
  font-weight:600 !important;
  padding:0.35rem 0.9rem !important;
  line-height:1.1 !important;
  box-shadow:var(--shadow) !important;
  transition:all 0.2s ease !important;
}
[data-testid="stBaseButton-primary"] button:hover,
[data-testid="baseButton-primary"] button:hover,
button[data-testid="baseButton-primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
.stDownloadButton>button:hover{
  background:var(--accent-hover) !important;
  box-shadow:var(--shadow-lg) !important;
  transform:translateY(-1px);
}
[data-testid="stBaseButton-primary"] button:active,
[data-testid="baseButton-primary"] button:active,
.stDownloadButton>button:active{
  transform:translateY(0);
  box-shadow:var(--shadow) !important;
}
[data-testid="stBaseButton-primary"] button:focus,
[data-testid="baseButton-primary"] button:focus,
.stDownloadButton>button:focus{
  outline:2px solid var(--ring) !important;
  outline-offset:2px !important;
}

/* Secondary */
[data-testid="stBaseButton-secondary"] button,
[data-testid="baseButton-secondary"] button,
button[data-testid="baseButton-secondary"],
button[data-testid="stBaseButton-secondary"]{
  background:var(--surface-2) !important;
  color:var(--text) !important;
  border:1px solid var(--border-strong) !important;
  border-radius:var(--radius) !important;
  font-weight:600 !important;
  padding:0.35rem 0.9rem !important;
  line-height:1.1 !important;
  box-shadow:none !important;
  transition:all 0.2s ease !important;
}
[data-testid="stBaseButton-secondary"] button:hover,
[data-testid="baseButton-secondary"] button:hover,
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover{
  background:var(--surface-hover) !important;
  border-color:var(--border-strong) !important;
  transform:translateY(-1px);
}
[data-testid="stBaseButton-secondary"] button:active,
[data-testid="baseButton-secondary"] button:active{
  transform:translateY(0);
}
[data-testid="stBaseButton-secondary"] button:focus,
[data-testid="baseButton-secondary"] button:focus{
  outline:2px solid var(--ring) !important;
  outline-offset:2px !important;
}

/* Sidebar buttons: texto blanco (sobre surfaces oscuras) */
[data-testid="stSidebar"] .stButton>button,
[data-testid="stSidebar"] .stDownloadButton>button{
  color:#FFFFFF !important;
}

/* ===== INPUTS ===== */
.stTextInput>div>div>input,
.stTextArea textarea,
.stSelectbox>div>div,
.stNumberInput input{
  background:var(--surface) !important;
  color:var(--text) !important;
  border:1.5px solid var(--border) !important;
  border-radius:var(--radius) !important;
  box-shadow:var(--shadow) !important;
  transition:border-color 0.2s ease, box-shadow 0.2s ease;
}
.stTextInput>div>div>input:hover,
.stTextArea textarea:hover,
.stSelectbox>div>div:hover,
.stNumberInput input:hover{
  border-color:var(--border-strong) !important;
}
.stTextInput>div>div>input:focus,
.stTextArea textarea:focus,
.stSelectbox [role="combobox"]:focus,
.stNumberInput input:focus{
  border-color:var(--accent) !important;
  outline:2px solid var(--ring) !important;
  outline-offset:2px !important;
  box-shadow:var(--shadow-lg) !important;
}
::placeholder{ color:var(--text-disabled) !important; opacity:1; }

/* Radios/checkboxes: evitar “rojos” del browser */
.stRadio input[type="radio"], input[type="radio"]{
  accent-color: var(--accent) !important;
}
[role="radiogroup"]>div{ gap:0.75rem; }
[role="radiogroup"] label{
  background:var(--surface) !important;
  border:1.5px solid var(--border) !important;
  border-radius:var(--radius) !important;
  padding:0.5rem 0.75rem !important;
  transition:all 0.2s ease;
}
[role="radiogroup"] label:hover{
  border-color:var(--border-strong) !important;
  background:var(--surface-hover) !important;
}
[role="radiogroup"] label[aria-checked="true"]{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(96,165,250,.20) !important;
}

/* ===== CARDS (resultado) ===== */
.bravo-grid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:16px;
  margin-top:12px;
}
@media (max-width:1100px){ .bravo-grid{ grid-template-columns:1fr; } }

.bravo-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:18px;
  color:var(--text);
  box-shadow:var(--shadow);
  transition:all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.bravo-card:hover{
  transform:translateY(-2px);
  box-shadow:var(--shadow-lg);
  border-color:var(--border-strong);
}
.bravo-card .label{
  font-size:0.85rem;
  color:var(--text-muted);
  margin-bottom:6px;
  letter-spacing:0.3px;
  font-weight:500;
  text-transform:uppercase;
}
.bravo-card .value{
  font-weight:700;
  font-size:1.75rem;
  line-height:1.2;
  color:var(--text);
}
.bravo-card .sub{
  font-size:0.9rem;
  margin-top:6px;
  color:var(--text-secondary);
}

/* Meta info */
.bravo-meta{
  margin:10px 0 14px 0;
  padding:12px 14px;
  background:var(--surface-2);
  color:var(--text-secondary);
  border:1px solid var(--border-strong);
  border-radius:var(--radius);
  text-align:center;
  font-size:1rem;
  font-weight:500;
  box-shadow:var(--shadow);
}

/* Alerts & dividers */
hr{ border:none; border-top:1px solid var(--border); margin:1.5rem 0; }
.stAlert{ border-radius:var(--radius) !important; border:1px solid var(--border) !important; }

/* ===== FIX: evitar que se vea el nombre del ícono (fallback) =====
   Streamlit/Material Icons a veces renderiza el nombre del ícono como texto
   (ej: keyboard_double_arrow_left). Esto lo oculta sin romper el toggle.
*/
[data-testid="stIconMaterial"]{
  font-size: 0 !important;
  line-height: 0 !important;
}

/* Si el SVG del ícono está presente, mantenelo visible */
[data-testid="stIconMaterial"] svg{
  font-size: 1rem !important;
  line-height: 1 !important;
}

/* Scrollbar (opcional) */
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-track{ background:var(--surface-2); }
::-webkit-scrollbar-thumb{ background:var(--border-strong); border-radius:5px; }
::-webkit-scrollbar-thumb:hover{ background:var(--text-muted); }
</style>
""",
        unsafe_allow_html=True,
    )

