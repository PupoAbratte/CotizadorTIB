import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Estadísticas — This is Bravo", page_icon="📊", layout="wide")

LOG_FILE = os.path.join("logs", "quotes.csv")
st.title("📊 Estadísticas — This is Bravo")

if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
    st.info("Aún no hay cotizaciones registradas. Volvé cuando generes algunas desde la página principal.")
    st.stop()

# Cargar datos
df = pd.read_csv(LOG_FILE)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["fecha"] = df["timestamp"].dt.date
    df["mes"] = df["timestamp"].dt.to_period("M").astype(str)

# KPIs
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

# Distribución por tipo de cliente
if "cliente_tipo" in df.columns:
    st.subheader("Distribución por tipo de cliente")
    counts = df["cliente_tipo"].value_counts().sort_values(ascending=False)
    fig1, ax1 = plt.subplots()
    counts.plot(kind="bar", ax=ax1)  # sin estilos ni colores específicos
    ax1.set_xlabel("Tipo de cliente"); ax1.set_ylabel("Cantidad"); ax1.set_title("Cantidad por cliente")
    st.pyplot(fig1)

# Ticket promedio por tipo de cliente
if {"cliente_tipo","logico_usd"}.issubset(df.columns):
    st.subheader("Ticket lógico promedio por tipo de cliente (USD)")
    avg_client = df.groupby("cliente_tipo")["logico_usd"].mean().sort_values(ascending=False)
    fig2, ax2 = plt.subplots()
    avg_client.plot(kind="bar", ax=ax2)
    ax2.set_xlabel("Tipo de cliente"); ax2.set_ylabel("USD"); ax2.set_title("Promedio por cliente")
    st.pyplot(fig2)

# Evolución mensual
if {"mes","logico_usd"}.issubset(df.columns):
    st.subheader("Evolución mensual — Total lógico (USD)")
    monthly = df.groupby("mes")["logico_usd"].sum().reset_index()
    fig3, ax3 = plt.subplots()
    ax3.plot(monthly["mes"], monthly["logico_usd"], marker="o")
    ax3.set_xlabel("Mes"); ax3.set_ylabel("USD"); ax3.set_title("Suma mensual (no implica ventas)")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig3)

st.caption("Fuente: logs/quotes.csv. Todo corre local.")