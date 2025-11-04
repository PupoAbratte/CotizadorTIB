import sqlite3
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

DB_PATH = "quotes.db"

def _connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    with _connect() as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            cliente_nombre TEXT,
            cliente_tipo TEXT,
            brief TEXT,
            mod_levels TEXT,
            base_usd REAL,
            adjusted_usd REAL,
            escenarios TEXT,
            coefs TEXT
        )
        """)
        con.commit()

def save_quote(cliente_nombre: str, cliente_tipo: str, brief: str,
               mod_levels: Dict[str, Any], base_usd: float,
               adjusted_usd: float, escenarios: Dict[str, float],
               coefs: Dict[str, float]) -> int:
    with _connect() as con:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO quotes (ts, cliente_nombre, cliente_tipo, brief, mod_levels, base_usd, adjusted_usd, escenarios, coefs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            cliente_nombre,
            cliente_tipo,
            brief,
            json.dumps(mod_levels, ensure_ascii=False),
            base_usd,
            adjusted_usd,
            json.dumps(escenarios),
            json.dumps(coefs)
        ))
        con.commit()
        return cur.lastrowid

def list_quotes(limit: int = 200) -> List[Tuple]:
    with _connect() as con:
        cur = con.cursor()
        cur.execute("""
        SELECT id, ts, cliente_nombre, cliente_tipo, base_usd, adjusted_usd, escenarios, mod_levels
        FROM quotes ORDER BY id DESC LIMIT ?
        """, (limit,))
        return cur.fetchall()