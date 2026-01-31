from jose import JWTError, jwt
from app.config import settings


def verify_supabase_jwt(token: str) -> dict | None:
    """Verify JWT signed by Supabase and return payload (sub, email, etc.) or None."""
    if not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_exp": True},
        )
        return payload
    except JWTError:
        return None
