import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("DAITFO_API_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        return api_key or "unsecured"
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if api_key == ADMIN_KEY:
        return api_key
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )

def verify_admin_key(api_key: str = Security(api_key_header)):
    if not ADMIN_KEY:
        return verify_api_key(api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if api_key == ADMIN_KEY:
        return api_key
    if api_key == API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )
