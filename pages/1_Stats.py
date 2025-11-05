# pages/1_Stats.py — lee de Google Sheets (fallback informativo si no hay datos)
import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import gspread
from google.oauth2 import service_account

st.set_page_config(page_title="Estadísticas — This is Bravo", page_icon="📊", layout="wide")
st.title("📊 Estadísticas — This is Bravo")

# --- Cargar datos desde Google Sheets ---
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
    rows = ws.get_all_records()  # lista de dicts
    df = pd.DataFrame(rows)
except Exception as e:
    st.info(f"No pude leer datos del Google Sheet: {type(e).__name__}. "
            "Verificá secrets y permisos (compartir con la cuenta de servicio).")
    st.stop()

if df.empty:
    st.info("Aún no hay cotizaciones registradas en la hoja. Probá generar alguna desde la página principal.")
    st.stop()

# --- Preprocesamiento liviano ---
for col in ("minimo_usd", "logico_usd", "maximo_usd"):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["mes"] = df["timestamp"].dt.to_period("M").astype(str)
elif "Fecha" in df.columns:
    # Si tu hoja tiene una columna 'Fecha' ISO
    df["timestamp"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["mes"] = df["timestamp"].dt.to_period("M").astype(str)

# --- KPIs ---
total_cotizaciones = len(df)
ticket_promedio = df["logico_usd"].mean() if "logico_usd" in df else 0.0
ticket_min = df["minimo_usd"].mean() if "minimo_usd" in df else 0.0
ticket_max = df["maximo_usd"].mean() if "maximo_usd" in df else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cotizaciones registradas", f"{total_cotizaciones}")
c2.metric("Ticket lógico promedio (USD)", f"{ticket_promedio:,.2f}")
c3.metric("Mínimo promedio (USD)", f"{ticket_min:,.2f}")
c4.metric("Máximo promedio (USD)", f"{ticket_max:,.2f}")

st.markdown("---")

# --- Gráfico: distribución por tipo de cliente ---
if "cliente_tipo" in df.columns:
    st.subheader("Distribución por tipo de cliente")
    counts = df["cliente_tipo"].value_counts().sort_values(ascending=False)
    fig1, ax1 = plt.subplots()
    counts.plot(kind="bar", ax=ax1)  # sin colores/estilos explícitos
    ax1.set_xlabel("Tipo de cliente"); ax1.set_ylabel("Cantidad"); ax1.set_title("Cantidad por cliente")
    st.pyplot(fig1)

# --- Gráfico: ticket promedio por tipo de cliente ---
if {"cliente_tipo","logico_usd"}.issubset(df.columns):
    st.subheader("Ticket lógico promedio por tipo de cliente (USD)")
    avg_client = df.groupby("cliente_tipo")["logico_usd"].mean().sort_values(ascending=False)
    fig2, ax2 = plt.subplots()
    avg_client.plot(kind="bar", ax=ax2)
    ax2.set_xlabel("Tipo de cliente"); ax2.set_ylabel("USD"); ax2.set_title("Promedio por cliente")
    st.pyplot(fig2)

# --- Gráfico: evolución mensual ---
if {"mes","logico_usd"}.issubset(df.columns):
    st.subheader("Evolución mensual — Total lógico (USD)")
    monthly = df.groupby("mes")["logico_usd"].sum().reset_index()
    fig3, ax3 = plt.subplots()
    ax3.plot(monthly["mes"], monthly["logico_usd"], marker="o")
    ax3.set_xlabel("Mes"); ax3.set_ylabel("USD"); ax3.set_title("Suma mensual (no implica ventas)")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig3)

st.caption("Fuente: Google Sheets (Worksheet: Quotes).")