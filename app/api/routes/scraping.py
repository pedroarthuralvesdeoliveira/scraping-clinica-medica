from fastapi import APIRouter, Depends, Query
from ...core.dependencies import get_api_key
from ..schemas.responses import TaskQueuedResponse
from ...worker.celery_app import celery

router = APIRouter(prefix="/scraping", tags=["Scraping"])


@router.get(
    "/patient-history/{patient_code}",
    dependencies=[Depends(get_api_key)],
    summary="Buscar histórico de agendamentos de um paciente via scraping",
    response_model=TaskQueuedResponse
)
def api_get_patient_history(
    patient_code: str,
    search_type: str = Query("codigo", description="Tipo de busca: 'codigo' ou 'cpf'")
) -> TaskQueuedResponse:
    """
    Dispara scraping do histórico de agendamentos de um paciente.
    Retorna task_id para consultar o resultado via /task_status/{task_id}.
    """
    print(f"API recebeu busca de histórico para: {patient_code} (tipo: {search_type}). Enfileirando...")

    task = celery.send_task(
        "get_patient_history_task",
        args=[patient_code, search_type],
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
