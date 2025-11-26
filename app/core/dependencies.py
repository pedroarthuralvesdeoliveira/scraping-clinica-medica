from functools import lru_cache
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from .config import Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@lru_cache
def get_settings():
    return Settings()

async def get_api_key(
    key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings)
):
    if key == settings.api_key:
        return key
    else:
        raise HTTPException(
            status_code=403, detail="Chave de API inválida ou ausente"
        )
