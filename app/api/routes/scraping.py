from fastapi import APIRouter, Depends, Query
from ...core.dependencies import get_api_key
from ..schemas.responses import TaskQueuedResponse
from ...worker.celery_app import celery

router = APIRouter(prefix="/scraping", tags=["Scraping"])


@router.get(
    "/patient-history/{telefone}",
    dependencies=[Depends(get_api_key)],
    summary="Buscar histórico de agendamentos de um paciente por telefone via scraping",
    response_model=TaskQueuedResponse
)
def api_get_patient_history(
    telefone: str,
) -> TaskQueuedResponse:
    """
    Dispara scraping do histórico de agendamentos de um paciente pelo telefone.
    Retorna task_id para consultar o resultado via /task_status/{task_id}.
    """
    print(f"API recebeu busca de histórico para telefone: {telefone}. Enfileirando...")

    task = celery.send_task(
        "get_patient_history_task",
        args=[telefone],
    )

    return TaskQueuedResponse(task_id=task.id)


@router.get(
    "/next-appointments",
    dependencies=[Depends(get_api_key)],
    summary="Buscar próximos agendamentos via scraping",
    response_model=TaskQueuedResponse
)
def api_get_next_appointments(
    sistema: str = Query("OF", description="Sistema: 'OF' ou 'OURO'")
) -> TaskQueuedResponse:
    """
    Dispara scraping dos próximos agendamentos do sistema.
    Exporta Excel do site e retorna os dados parseados.
    Retorna task_id para consultar o resultado via /task_status/{task_id}.
    """
    print(f"API recebeu busca de próximos agendamentos ({sistema}). Enfileirando...")

    task = celery.send_task(
        "get_next_appointments_task",
        args=[sistema],
    )

    return TaskQueuedResponse(task_id=task.id)


@router.get(
    "/active-patients",
    dependencies=[Depends(get_api_key)],
    summary="Buscar pacientes ativos via scraping",
    response_model=TaskQueuedResponse
)
def api_get_active_patients() -> TaskQueuedResponse:
    """
    Dispara scraping de todos os pacientes ativos do sistema.
    Retorna task_id para consultar o resultado via /task_status/{task_id}.
    """
    print("API recebeu busca de pacientes ativos. Enfileirando...")

    task = celery.send_task(
        "get_active_patients_task",
        args=[],
    )

    return TaskQueuedResponse(task_id=task.id)
