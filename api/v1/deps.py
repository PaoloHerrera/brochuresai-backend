import os
import sqlite3
import uuid
from datetime import date, datetime
from fastapi import Request
from config import settings

# Quota configurable via env, default 3
MAX_BROCHURES_PER_USER = int(settings.max_brochures_per_user)


def _db_path_from_env() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./data/brochuresai.db")
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    # fallback
    return "./data/brochuresai.db"


def get_conn():
    conn = sqlite3.connect(_db_path_from_env(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_anon_id(conn: sqlite3.Connection, anon_id: str):
    cur = conn.execute("SELECT * FROM users WHERE anon_id = ?", (anon_id,))
    return cur.fetchone()


def get_user_by_ip(conn: sqlite3.Connection, ip: str):
    cur = conn.execute("SELECT * FROM users WHERE ip_address = ? ORDER BY created_at DESC LIMIT 1", (ip,))
    return cur.fetchone()


def create_user(conn: sqlite3.Connection, ip: str) -> sqlite3.Row:
    new_anon = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO users (ip_address, anon_id, brochures_count, created_at, updated_at) VALUES (?, ?, 0, datetime('now'), datetime('now'))",
        (ip, new_anon),
    )
    conn.commit()
    return get_user_by_anon_id(conn, new_anon)


def ensure_user(ip: str, anon_id: str | None):
    conn = get_conn()
    try:
        row = None
        if anon_id:
            row = get_user_by_anon_id(conn, anon_id)
        if row is None and ip:
            row = get_user_by_ip(conn, ip)
        if row is None:
            row = create_user(conn, ip)
        return dict(row)
    finally:
        conn.close()


def increment_brochures(anon_id: str):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE users SET brochures_count = brochures_count + 1, updated_at = datetime('now') WHERE anon_id = ?",
            (anon_id,),
        )
        conn.commit()
    finally:
        conn.close()


# Resetea el contador si ha cambiado el día (comparando solo la parte de fecha, sin horas/minutos)
def reset_brochures_if_new_day(conn: sqlite3.Connection, user: dict | sqlite3.Row) -> dict:
    # Acepta tanto dict como sqlite3.Row
    user_dict = dict(user) if isinstance(user, sqlite3.Row) else (user or {})
    updated_at = user_dict.get("updated_at")
    if not updated_at:
        return user_dict

    # Parsear fecha de updated_at (SQLite datetime('now') -> 'YYYY-MM-DD HH:MM:SS')
    try:
        updated_day = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        # Fallback por si viniera con fracciones de segundo o formato ISO
        try:
            updated_day = datetime.fromisoformat(updated_at).date()
        except Exception:
            return user_dict

    today = date.today()
    if today > updated_day:
        # Ha comenzado un nuevo día: resetear contador y actualizar updated_at
        conn.execute(
            "UPDATE users SET brochures_count = 0, updated_at = datetime('now') WHERE anon_id = ?",
            (user_dict["anon_id"],),
        )
        conn.commit()
        # Refrescar usuario desde BD para devolver valores actualizados
        cur = conn.execute("SELECT * FROM users WHERE anon_id = ?", (user_dict["anon_id"],))
        row = cur.fetchone()
        return dict(row) if row else user_dict

    return user_dict


def get_client_ip(request: Request) -> str:
    # Si confiamos en el proxy frontal, aceptamos X-Forwarded-For / X-Real-IP
    if settings.trust_proxy:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
            if ip:
                return ip
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()
    # Fallback: IP del socket directo
    return request.client.host if request.client else "unknown"

def set_full_language(language: str) -> str:
    if language == "en":
        return "English"
    if language == "es":
        return "Spanish"
    return "English"