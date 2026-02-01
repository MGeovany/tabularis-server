import hashlib
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from jose.utils import base64url_decode

from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.config import settings
from app.logging_config import get_logger


logger = get_logger("app.auth")
_warned_missing_secret = False

_jwks_cache: dict | None = None
_jwks_cache_at: float = 0.0
_JWKS_TTL_SEC = 10 * 60


def _token_fingerprint(token: str) -> str:
    # Stable fingerprint for correlating logs without printing the token.
    return hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _load_jwks() -> dict | None:
    """Fetch and cache Supabase JWKS used for RS256 verification."""
    global _jwks_cache, _jwks_cache_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_at) < _JWKS_TTL_SEC:
        return _jwks_cache

    if not settings.supabase_url:
        return None

    # Supabase public JWKS (no auth required)
    url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=3) as res:  # noqa: S310
            body = res.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        if not isinstance(data, dict) or "keys" not in data:
            logger.warning("JWKS fetch ok but shape unexpected url=%s", url)
            return None
        _jwks_cache = data
        _jwks_cache_at = now
        return _jwks_cache
    except Exception as e:
        logger.warning("JWKS fetch failed url=%s err=%s", url, type(e).__name__)
        return None


def _rsa_pem_from_jwk(key: dict) -> str:
    n_raw = key.get("n")
    e_raw = key.get("e")
    if not isinstance(n_raw, str) or not isinstance(e_raw, str):
        raise ValueError("Invalid RSA jwk")

    n = int.from_bytes(base64url_decode(n_raw.encode("utf-8")), "big")
    e = int.from_bytes(base64url_decode(e_raw.encode("utf-8")), "big")
    pub = rsa.RSAPublicNumbers(e, n).public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return pem.decode("utf-8")


def _ec_pem_from_jwk(key: dict) -> str:
    crv = key.get("crv")
    x_raw = key.get("x")
    y_raw = key.get("y")
    if crv != "P-256" or not isinstance(x_raw, str) or not isinstance(y_raw, str):
        raise ValueError("Invalid EC jwk")

    x = int.from_bytes(base64url_decode(x_raw.encode("utf-8")), "big")
    y = int.from_bytes(base64url_decode(y_raw.encode("utf-8")), "big")
    pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return pem.decode("utf-8")


def _public_pem_from_jwk(key: dict) -> str:
    kty = key.get("kty")
    if kty == "RSA":
        return _rsa_pem_from_jwk(key)
    if kty == "EC":
        return _ec_pem_from_jwk(key)
    raise ValueError(f"Unsupported jwk kty={kty!r}")


def verify_supabase_jwt(token: str) -> dict | None:
    """Verify JWT signed by Supabase and return payload (sub, email, etc.) or None."""
    global _warned_missing_secret
    fp = _token_fingerprint(token)

    alg: str | None = None
    kid: str | None = None
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        kid = header.get("kid")
        logger.info("JWT header fp=%s alg=%r kid=%r typ=%r", fp, alg, kid, header.get("typ"))
    except Exception as e:
        logger.warning("JWT header read failed fp=%s err=%s", fp, type(e).__name__)
    try:
        # Useful context (safe): show unverified claims in case we're hitting the wrong project.
        try:
            claims = jwt.get_unverified_claims(token)
            logger.info(
                "JWT received fp=%s iss=%r ref=%r aud=%r sub=%r exp=%r iat=%r role=%r",
                fp,
                claims.get("iss"),
                claims.get("ref"),
                claims.get("aud"),
                claims.get("sub"),
                claims.get("exp"),
                claims.get("iat"),
                claims.get("role"),
            )
        except Exception as e:
            logger.warning(
                "JWT received but could not read unverified claims fp=%s err=%s",
                fp,
                type(e).__name__,
            )

        if alg and str(alg).upper().startswith("HS"):
            if not settings.supabase_jwt_secret:
                # If we don't have a secret configured, every request will look like "invalid token".
                # Log once with enough context to debug env loading (without printing secrets).
                if not _warned_missing_secret:
                    _warned_missing_secret = True
                    env_path = Path(".env")
                    logger.error(
                        "Supabase JWT secret missing; cwd=%s env_file_exists=%s SUPABASE_URL=%r",
                        os.getcwd(),
                        env_path.exists(),
                        settings.supabase_url,
                    )
                return None

            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=[str(alg)],
                options={"verify_aud": False, "verify_exp": True},
            )
            return payload

        if alg in {"RS256", "ES256"}:
            jwks = _load_jwks()
            keys = jwks.get("keys") if isinstance(jwks, dict) else None
            if not isinstance(keys, list) or not keys:
                logger.warning("JWKS not available; cannot verify %s fp=%s", alg, fp)
                return None

            key = None
            if kid:
                key = next((k for k in keys if isinstance(k, dict) and k.get("kid") == kid), None)
            if key is None:
                key = next((k for k in keys if isinstance(k, dict)), None)
            if not isinstance(key, dict):
                logger.warning("JWKS has no matching key fp=%s kid=%r", fp, kid)
                return None

            try:
                pem = _public_pem_from_jwk(key)
            except Exception as e:
                logger.warning(
                    "JWKS key parse failed fp=%s kid=%r kty=%r err=%s",
                    fp,
                    kid,
                    key.get("kty"),
                    type(e).__name__,
                )
                return None
            payload = jwt.decode(
                token,
                pem,
                algorithms=[alg],
                options={"verify_aud": False, "verify_exp": True},
            )
            return payload

        if alg:
            logger.warning("JWT unsupported alg fp=%s alg=%r", fp, alg)
        else:
            logger.warning("JWT alg missing fp=%s", fp)
        return None
    except ExpiredSignatureError:
        logger.warning("JWT expired fp=%s", fp)
        return None
    except JWTClaimsError as e:
        logger.warning(
            "JWT claims error fp=%s msg=%s",
            fp,
            str(e)[:240],
        )
        return None
    except JWTError as e:
        # Common: signature mismatch (wrong secret) or alg mismatch.
        logger.warning(
            "JWT verify failed fp=%s msg=%s secret_len=%s",
            fp,
            str(e)[:240],
            len(settings.supabase_jwt_secret or ""),
        )
        return None
