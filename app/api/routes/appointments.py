from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from ...core.dependencies import get_api_key
from ..schemas.common import CancelPayload, SchedulePayload, VerifyPayload, SyncPayload
from ...worker.celery_app import celery

router = APIRouter()


@router.post(
    "/schedule", dependencies=[Depends(get_api_key)], summary="Agendar consulta"
)
def api_schedule(payload: SchedulePayload):
    """
    Recebe um JSON do N8N e agenda uma consulta.
    """
    print(
        f"API recebeu job de agendamento para: {payload.nome_paciente}. Enfileirando..."
    )

    paciente_info = {
        "nome": payload.nome_paciente,
        "data_nascimento": payload.data_nascimento,
        "cpf": payload.cpf,
        "telefone": payload.telefone,
        "tipo_atendimento": payload.tipo_atendimento,
        "convenio": payload.convenio,
    }

    task = celery.send_task(
        "schedule_appointment_task",
        args=[
            payload.medico,
            payload.data_desejada,
            paciente_info,
            payload.horario_desejado,
            payload.tipo_atendimento,
        ],
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}


@router.post(
    "/cancel", dependencies=[Depends(get_api_key)], summary="Cancelar consulta"
)
def api_cancel(payload: CancelPayload):
    """
    Recebe um JSON do N8N e cancela uma consulta.
    """
    print(
        f"API recebeu job de cancelamento para: {payload.nome_paciente}. Enfileirando..."
    )

    task = celery.send_task(
        "cancel_appointment_task",
        args=[
            payload.medico,
            payload.data_desejada,
            payload.horario_desejado,
            payload.nome_paciente,
            payload.cpf,
        ],
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}


@router.get(
    "/availability",
    dependencies=[Depends(get_api_key)],
    summary="Verificar disponibilidade de consulta",
)
def api_check_availability(payload: VerifyPayload = Depends()):
    """
    Verifica a disponibilidade.
    Ex: /availability?medico=Dr.Nome&data_desejada=25/10/2025&horario_desejado=14:00
    Ex: /availability?medico=Dr.Nome (para achar o próximo livre)
    """
    print(f"API recebeu job de verificação para: {payload.medico}. Enfileirando...")

    task = celery.send_task(
        "verify_doctors_calendar_task",
        args=[
            payload.medico,
            payload.data_desejada,
            payload.horario_desejado,
            payload.horario_inicial,
            payload.horario_final,
        ],
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}


@router.get("/task_status/{task_id}", summary="Verificar status de uma tarefa Celery")
def get_task_status(task_id: str):
    """
    Consulta o backend do Celery (Redis) para obter o status e o resultado de uma tarefa.
    """
    task_result_obj: AsyncResult = AsyncResult(task_id, app=celery)

    response = {"task_id": task_id, "status": task_result_obj.status, "result": None}

    if task_result_obj.ready():
        result = task_result_obj.get()
        response["result"] = result

    elif task_result_obj.status == "PENDING":
        response["result"] = "Tarefa ainda não iniciada."
    elif task_result_obj.status == "STARTED":
        response["result"] = "Tarefa em execução."

    return JSONResponse(status_code=200, content=response)


@router.post(
    "/sync",
    dependencies=[Depends(get_api_key)],
    summary="Sincronizar agendamentos do paciente",
)
def api_sync(payload: SyncPayload):
    """
    Sincroniza os agendamentos de um paciente do site para o banco de dados.
    """
    print(
        f"API recebeu job de sincronização para: {payload.nome_paciente} (CPF: {payload.cpf}). Enfileirando..."
    )

    task = celery.send_task(
        "sync_patient_appointments_task",
        args=[
            payload.cpf,
            payload.nome_paciente,
            payload.medico,
        ],
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}
