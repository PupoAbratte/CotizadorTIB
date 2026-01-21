# auth.py — login persistente por cookie + expiración (sliding) + logout consistente
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
import extra_streamlit_components as stx

COOKIE_NAME = "bravo_auth"
SESSION_HOURS_DEFAULT = 3  # ajustable


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload_b64: str, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _make_token(email: str, exp_epoch: int, secret: str) -> str:
    payload = {"email": email, "exp": exp_epoch}
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig_b64 = _sign(payload_b64, secret)
    return f"{payload_b64}.{sig_b64}"


def _verify_token(token: str, secret: str) -> Optional[dict]:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected = _sign(payload_b64, secret)
        if not hmac.compare_digest(sig_b64, expected):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if not payload.get("email"):
            return None
        return payload
    except Exception:
        return None


def _get_cookies_with_retry(cm, timeout_s: float = 0.25):
    # El componente puede devolver vacío o stale 1 ciclo; reintenta un toque.
    start = time.time()
    last = {}
    while True:
        last = cm.get_all() or {}
        if (time.time() - start) > timeout_s:
            return last
        # si vino algo, devolvemos enseguida
        if last is not None:
            return last
        time.sleep(0.01)


def _expire_cookie(cm, key: str):
    # Expirar en el pasado (más confiable que delete)
    cm.set(
        COOKIE_NAME,
        "",
        expires_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
        key=key,
    )


def require_login(session_hours: float = SESSION_HOURS_DEFAULT) -> bool:
    users = dict(st.secrets.get("auth", {}).get("users", {}))

    # Modo abierto si no hay usuarios configurados
    if not users:
        return True

    secret = st.secrets.get("AUTH_COOKIE_SECRET")
    if not secret:
        st.error("Falta AUTH_COOKIE_SECRET en secrets. Agregalo para habilitar login persistente.")
        st.stop()

    cm = stx.CookieManager()

    # Si acabás de cerrar sesión: NO re-autenticar por cookie en este ciclo
    if st.session_state.get("logout_pending"):
        _expire_cookie(cm, key="unset_auth_cookie_pending")
        token = None
    else:
        cookies = _get_cookies_with_retry(cm)
        token = (cookies or {}).get(COOKIE_NAME)

    # Auto-login por cookie (solo si NO hay logout_pending)
    if not st.session_state.get("auth_ok") and token and not st.session_state.get("logout_pending"):
        payload = _verify_token(token, secret)
        if payload:
            st.session_state["auth_ok"] = True
            st.session_state["auth_email"] = payload["email"]

    # Logueado: sidebar + logout + sliding expiration
    if st.session_state.get("auth_ok"):
        with st.sidebar:
            email = st.session_state.get("auth_email", "")
            st.markdown(
                f"""
                <div class="session-box">
                <div style="font-size:0.85rem; color:var(--text-muted); margin-bottom:4px;">
                    Sesión:
                </div>
                <div style="font-weight:400; color:var(--text);">
                    {email}
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Cerrar sesión", key="logout_btn"):
                # 1) limpiar estado
                st.session_state.pop("auth_ok", None)
                st.session_state.pop("auth_email", None)

                # 2) marcar logout y expirar cookie
                st.session_state["logout_pending"] = True
                _expire_cookie(cm, key="unset_auth_cookie_click")
                st.rerun()

        # Sliding expiration (renueva cookie cada run)
        exp_epoch = int(time.time() + float(session_hours) * 3600)
        email = st.session_state.get("auth_email", "")
        new_token = _make_token(email, exp_epoch, secret)
        cm.set(
            COOKIE_NAME,
            new_token,
            expires_at=datetime.fromtimestamp(exp_epoch, tz=timezone.utc),
            key="set_auth_cookie",
        )

        # Si quedó logout_pending por un run viejo, lo limpiamos
        st.session_state.pop("logout_pending", None)
        return True

    # No logueado: formulario
    st.title("Accedé con tus credenciales")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value="", key="auth_email_input")
        pwd = st.text_input("Contraseña", type="password", value="", key="auth_pwd_input")
        submit = st.form_submit_button("Entrar")

    if submit:
        if email in users and pwd == users[email]:
            exp_epoch = int(time.time() + float(session_hours) * 3600)
            st.session_state["auth_ok"] = True
            st.session_state["auth_email"] = email
            st.session_state.pop("logout_pending", None)

            token = _make_token(email, exp_epoch, secret)
            cm.set(
                COOKIE_NAME,
                token,
                expires_at=datetime.fromtimestamp(exp_epoch, tz=timezone.utc),
                key="set_auth_cookie_login",
            )
            st.rerun()
        else:
            st.error("Credenciales inválidas. Probá de nuevo.")

    st.stop()