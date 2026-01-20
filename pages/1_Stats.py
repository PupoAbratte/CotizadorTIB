# pages/1_Stats.py — Dashboard de cotizaciones (Google Sheets)
import re
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import gspread
from google.oauth2 import service_account

# =========================
# Estilo dark (Matplotlib)
# =========================
DARK_FG = "#E6E6E6"     # texto/ticks claros
DARK_GRID = "#2A2F3A"   # grilla sutil

def style_dark_axes(ax):
    ax.set_facecolor("none")
    ax.figure.patch.set_alpha(0)

    # Tamaños (más compactos)
    ax.tick_params(colors=DARK_FG, labelsize=9)
    ax.title.set_color(DARK_FG)
    ax.title.set_fontsize(11)
    ax.xaxis.label.set_color(DARK_FG)
    ax.yaxis.label.set_color(DARK_FG)
    ax.xaxis.label.set_fontsize(9)
    ax.yaxis.label.set_fontsize(9)

    for spine in ax.spines.values():
        spine.set_color(DARK_GRID)

    ax.grid(True, color=DARK_GRID, alpha=0.35, linewidth=0.8)
    return ax

def fmt_usd(x: float) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.2f}"

def _parse_money_to_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()
    if not s or s.lower() in {"none", "nan"}:
        return None

    s = s.replace("US$", "").replace("USD", "").replace("$", "").strip()
    s = re.sub(r"[^\d,.\-]", "", s)

    # Normalizar separadores (miles/decimales)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        parts = s.split(",")
        if len(parts[-1]) in (1, 2):
            s = "".join(parts[:-1]) + "." + parts[-1]
        else:
            s = s.replace(",", "")

    try:
        return float(s)
    except Exception:
        return None

def shorten_label(s: str, max_len: int = 18) -> str:
    s = str(s).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"

# =========================
# Parseo de fecha (incluye meses en español)
# =========================
MESES_ES = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}

def parse_fecha_es(x):
    """
    Soporta:
    - '5/12/2025 15:13:33'
    - '5/12/2025'
    - '5-Diciembre-2025' (mes en español)
    """
    if x is None:
        return pd.NaT
    s = str(x).strip()
    if not s:
        return pd.NaT

    # 1) Intento directo (dayfirst=True para LATAM)
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if not pd.isna(dt):
        return dt

    # 2) Caso '5-Diciembre-2025'
    s2 = s.lower()
    for mes, num in MESES_ES.items():
        if f"-{mes}-" in s2:
            s2 = s2.replace(f"-{mes}-", f"-{num}-")
            break

    return pd.to_datetime(s2, errors="coerce", dayfirst=True)

# =========================
# UI
# =========================
st.set_page_config(page_title="Dashboard de cotizaciones — This is Bravo", page_icon="📊", layout="wide")
from auth import require_login
require_login(session_hours=3)

st.title("Dashboard de cotizaciones")
st.write(
    "Esta sección muestra el desempeño histórico de nuestras propuestas comerciales. "
    "Analiza montos base, montos finales y montos aprobados, para establecer tendencias "
    "que nos permitan tomar decisiones más estratégicas en el proceso de cotización."
)

# =========================
# Cargar datos (Sheets)
# =========================
try:
    SHEET_ID = st.secrets["SHEET_ID"]
    WORKSHEET_NAME = st.secrets.get("WORKSHEET_NAME", "Quotes")

    creds_info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
except Exception as e:
    st.info(
        f"No pude leer datos del Google Sheet: {type(e).__name__}. "
        "Verificá secrets y permisos (compartir con la cuenta de servicio)."
    )
    st.stop()

if df.empty:
    st.info("Aún no hay cotizaciones registradas en la hoja. Probá generar alguna desde la página principal.")
    st.stop()

# =========================
# Normalización columnas
# =========================
df.columns = [c.strip() for c in df.columns]

rename_map = {
    "Precio base US": "base_sin_overhead_usd",
    "Precio base USD": "base_sin_overhead_usd",
    "Min USD": "minimo_usd",
    "Base USD": "logico_usd",
    "Max USD": "maximo_usd",
    "Cotización elegida": "cotizacion_enviada_usd",
    "Cotización Aprobada": "cotizacion_aprobada_usd",
    "Cliente": "cliente_nombre",
    "Tipo": "cliente_tipo",
    "Fecha": "fecha",
}
df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

# =========================
# Parse moneda
# =========================
money_cols = [
    "base_sin_overhead_usd",
    "minimo_usd",
    "logico_usd",
    "maximo_usd",
    "cotizacion_enviada_usd",
    "cotizacion_aprobada_usd",
]
for col in money_cols:
    if col in df.columns:
        df[col] = df[col].apply(_parse_money_to_float)

# =========================
# Fechas (NO filtramos df completo; solo creamos df_ts para series)
# =========================
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
elif "fecha" in df.columns:
    df["timestamp"] = df["fecha"].apply(parse_fecha_es)
else:
    df["timestamp"] = pd.NaT

# df completo (para KPI de conteo)
total_cotizaciones = len(df)

# df_ts solo para gráficos mensuales (requiere timestamp)
df_ts = df[df["timestamp"].notna()].copy()
if not df_ts.empty:
    df_ts["mes"] = df_ts["timestamp"].dt.to_period("M").astype(str)

# Flags (en ambos, pero KPIs usan df completo)
df["is_aprobada"] = df["cotizacion_aprobada_usd"].notna() if "cotizacion_aprobada_usd" in df.columns else False
if not df_ts.empty:
    df_ts["is_aprobada"] = df_ts["cotizacion_aprobada_usd"].notna() if "cotizacion_aprobada_usd" in df_ts.columns else False

# =========================
# KPIs (arriba) — usan df completo (no pierden filas)
# =========================
base_promedio = df["base_sin_overhead_usd"].mean() if "base_sin_overhead_usd" in df.columns else None
enviada_promedio = df["cotizacion_enviada_usd"].mean() if "cotizacion_enviada_usd" in df.columns else None

aprobadas_count = int(df["is_aprobada"].sum()) if "is_aprobada" in df.columns else 0
aprobacion_rate = (aprobadas_count / total_cotizaciones) if total_cotizaciones > 0 else 0.0

ticket_promedio_global = None
if "cotizacion_aprobada_usd" in df.columns and aprobadas_count > 0:
    ticket_promedio_global = df.loc[df["is_aprobada"], "cotizacion_aprobada_usd"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Cotizaciones realizadas", f"{total_cotizaciones}")
c2.metric("Monto base promedio (USD)", fmt_usd(base_promedio))
c3.metric("Cotización enviada promedio (USD)", fmt_usd(enviada_promedio))
c4.metric("Ticket promedio (USD)", fmt_usd(ticket_promedio_global))
c5.metric("Tasa de aprobación (%)", f"{aprobacion_rate*100:,.1f}")

st.markdown("---")

# =========================
# Agregaciones para gráficos (usan df_ts)
# =========================
enviada_mes = None
aprobada_mes = None

if not df_ts.empty and {"mes", "cotizacion_enviada_usd"}.issubset(df_ts.columns):
    enviada_mes = (
        df_ts.groupby("mes")["cotizacion_enviada_usd"]
        .mean()
        .rename("enviada_promedio")
        .reset_index()
    )

if not df_ts.empty and {"mes", "cotizacion_aprobada_usd"}.issubset(df_ts.columns):
    tmp = df_ts[df_ts["is_aprobada"]].groupby("mes")["cotizacion_aprobada_usd"].mean()
    aprobada_mes = tmp.rename("aprobada_promedio").reset_index()

# Donut por tipo (usa df completo)
propuestas_tipo = None
if "cliente_tipo" in df.columns:
    propuestas_tipo = (
        df["cliente_tipo"]
        .fillna("Sin tipo")
        .value_counts()
        .rename_axis("cliente_tipo")
        .reset_index(name="cantidad")
    )

# =========================
# Layout (2 columnas)
# =========================
colA, colB = st.columns(2, gap="large")

with colA:
    st.subheader("Cotización enviada promedio por mes (USD)")
    if enviada_mes is None or enviada_mes.empty:
        st.caption("No hay datos suficientes con fecha válida para calcular el promedio enviado por mes.")
    else:
        fig1, ax1 = plt.subplots(figsize=(6, 3))
        ax1.plot(enviada_mes["mes"], enviada_mes["enviada_promedio"], marker="o")
        plt.xticks(rotation=30, ha="right")
        style_dark_axes(ax1)
        st.pyplot(fig1, transparent=True, use_container_width=True)

with colB:
    st.subheader("Ticket aprobado promedio por mes (USD)")
    if aprobada_mes is None or aprobada_mes.empty:
        st.caption("Aún no hay cotizaciones aprobadas (con fecha válida) cargadas.")
    else:
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.plot(aprobada_mes["mes"], aprobada_mes["aprobada_promedio"], marker="o")
        plt.xticks(rotation=30, ha="right")
        style_dark_axes(ax2)
        st.pyplot(fig2, transparent=True, use_container_width=True)

colC, colD = st.columns(2, gap="large")

with colC:
    st.subheader("Propuestas por tipo de cliente (cantidad)")
    if propuestas_tipo is None or propuestas_tipo.empty:
        st.caption("No hay datos de tipo de cliente.")
    else:
        fig3, ax3 = plt.subplots(figsize=(6, 3.2))

        labels_raw = propuestas_tipo["cliente_tipo"].astype(str).tolist()
        labels = [shorten_label(x, 18) for x in labels_raw]
        sizes = propuestas_tipo["cantidad"].astype(float).tolist()

        # Si hay un solo tipo, no mostramos porcentajes (evita el 100% arriba del aro)
        show_pct = (len(sizes) > 1)

        wedges, texts, autotexts = ax3.pie(
            sizes,
            labels=None,
            autopct=(lambda p: f"{p:.0f}%" if (show_pct and p >= 8) else ""),
            startangle=90,
            wedgeprops=dict(width=0.42, edgecolor=DARK_GRID),
        )

        centre_circle = plt.Circle((0, 0), 0.58, fc="none", ec=DARK_GRID, lw=1)
        ax3.add_artist(centre_circle)

        ax3.axis("equal")
        ax3.set_facecolor("none")
        fig3.patch.set_alpha(0)

        for at in autotexts:
            at.set_color(DARK_FG)
            at.set_fontsize(8)

        # Reservar margen a la derecha para que la leyenda no se corte
        fig3.subplots_adjust(right=0.78)

        ax3.legend(
            wedges,
            labels,
            loc="center left",
            bbox_to_anchor=(0.82, 0.5),
            frameon=False,
            labelcolor=DARK_FG,
            fontsize=8,
            title_fontsize=8,
            handlelength=1.2,
            handletextpad=0.6,
            borderaxespad=0.0,
        )

        st.pyplot(fig3, transparent=True, use_container_width=True)

with colD:
    st.subheader("Notas")
    st.caption(
        "Si alguna fila del Sheet tiene un formato de fecha no reconocible, igual cuenta para KPIs, "
        "pero no entra en los gráficos mensuales."
    )

st.caption("Fuente: Google Sheets (Worksheet: Quotes).")