from fastapi import APIRouter
from datetime import datetime
from ..schemas.responses import HealthCheckResponse

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    """Endpoint para verificar a saúde da API"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now()
    )