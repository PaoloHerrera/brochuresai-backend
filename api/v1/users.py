from fastapi import APIRouter, HTTPException, Request

from .deps import (
    MAX_BROCHURES_PER_USER,
    ensure_user,
    get_client_ip,
    get_conn,
    reset_brochures_if_new_day,
)

router = APIRouter()


@router.get("/users/get_remaining/")
async def get_remaining_brochures(request: Request, anon_id: str = ""):
    try:
        user_ip = get_client_ip(request)
        user = ensure_user(user_ip, anon_id if anon_id else None)

        # Resetear si ha cambiado el día (solo por fecha)
        conn = get_conn()
        try:
            user = reset_brochures_if_new_day(conn, user)
        finally:
            conn.close()

        remaining = max(0, MAX_BROCHURES_PER_USER - int(user.get("brochures_count", 0)))
        return {
            "success": True,
            "anon_id": user["anon_id"],
            "brochures_used": int(user.get("brochures_count", 0)),
            "brochures_remaining": remaining,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
