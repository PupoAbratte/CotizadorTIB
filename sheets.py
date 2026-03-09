# sheets.py — Comunicación con Google Sheets
# Extraído de app.py para separar la lógica de persistencia de la UI.

from datetime import datetime
from typing import Dict, Any

import gspread
import streamlit as st
from google.oauth2 import service_account
from gspread.utils import rowcol_to_a1


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
    sheet_id: str,
    worksheet_name: str,
    *,
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
    tasa_cop_usd: float,
    escenario_elegido: str,
    monto_elegido_usd: float,
    monto_elegido_cop: int,
) -> bool:
    try:
        gc, _ = _sheet_client()
        sh = gc.open_by_key(sheet_id)

        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=26)
            ws.append_row(
                [
                    "Fecha", "Cliente", "Tipo", "Brief", "Precio base USD",
                    "Min USD", "Base USD", "Max USD", "tasa_cop_usd_usada", "Notas",
                    "Cotizacion final", "Escenario elegido", "Monto elegido USD", "Monto elegido COP"
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
            "escenario_elegido": escenario_elegido,
            "monto_elegido_usd": monto_elegido_usd,
            "monto_elegido_cop": monto_elegido_cop,
        }

        row = []
        for h in headers:
            key = header_to_payload_key.get(h)
            row.append(payload.get(key, ""))

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
