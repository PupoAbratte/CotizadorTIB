# pdf_generator.py — Generación de PDF con WeasyPrint
# Extraído de app.py para aislar la dependencia de WeasyPrint.

import re

import requests
import weasyprint


def safe_filename(s: str) -> str:
    """Convierte un string en un nombre de archivo seguro."""
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    return s or "cotizacion"


def _url_fetcher(url):
    """Fetcher que permite a WeasyPrint descargar imágenes remotas (logos, etc.)."""
    if url.startswith("http"):
        resp = requests.get(url, timeout=15)
        return {
            "string": resp.content,
            "mime_type": resp.headers.get("Content-Type", "image/png"),
        }
    return weasyprint.default_url_fetcher(url)


def generate_pdf(html_string: str) -> bytes:
    """Recibe HTML renderizado y devuelve bytes de PDF."""
    return weasyprint.HTML(
        string=html_string,
        url_fetcher=_url_fetcher,
    ).write_pdf()
