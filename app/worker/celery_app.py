from ..core.dependencies import get_settings
from celery import Celery

settings = get_settings()

if "localhost" in settings.redis_url:
    print(
        "DEBUG: 'localhost' detectado. Forçando '127.0.0.1' para evitar problemas de IPv6."
    )
    redis_url = settings.redis_url.replace("localhost", "127.0.0.1")
else:
    redis_url = settings.redis_url

celery = Celery(
    "celery_worker", broker=redis_url, backend=redis_url, include=["app.worker.tasks"]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_soft_time_limit=300,
    task_time_limit=600,
)
