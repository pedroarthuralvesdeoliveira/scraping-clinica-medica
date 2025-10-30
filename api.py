import uvicorn
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from celery.result import AsyncResult
import os
from dotenv import load_dotenv

from celery_worker import schedule_appointment_task, cancel_appointment_task, verify_doctors_calendar_task, celery

load_dotenv() 


class SchedulePayload(BaseModel):
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str
    data_nascimento: str
    cpf: str
    telefone: str
    tipo_atendimento: str

class CancelPayload(BaseModel):
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str


API_KEY = os.environ.get("API_KEY", "53051fe441b9cdf8d8c8bbf663475acc87ae399b75723eb0a4e265f48c6de646") 
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(key: str = Security(api_key_header)):
    if key == API_KEY:
        return key
    else:
        raise HTTPException(
            status_code=403, detail="Chave de API inválida ou ausente"
        )

app = FastAPI(title="SoftClyn Bot API")


@app.post("/schedule", dependencies=[Depends(get_api_key)], summary="Agendar consulta")
def api_schedule(payload: SchedulePayload):
    """
    Recebe um JSON do N8N e agenda uma consulta.
    """
    print(f"API recebeu job de agendamento para: {payload.nome_paciente}. Enfileirando...")    
    
    paciente_info = {
        "nome": payload.nome_paciente,
        "data_nascimento": payload.data_nascimento,
        "cpf": payload.cpf,
        "telefone": payload.telefone,
        "tipo_atendimento": payload.tipo_atendimento
    }

    task = schedule_appointment_task.delay(
        payload.medico,
        payload.data_desejada,
        paciente_info,
        payload.horario_desejado,
        payload.tipo_atendimento
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}

@app.post("/cancel", dependencies=[Depends(get_api_key)], summary="Cancelar consulta")
def api_cancel(payload: CancelPayload):
    """
    Recebe um JSON do N8N e cancela uma consulta.
    """
    print(f"API recebeu job de cancelamento para: {payload.nome_paciente}. Enfileirando...")    
    
    task = cancel_appointment_task.delay(
        payload.medico,
        payload.data_desejada,
        payload.horario_desejado,
        payload.nome_paciente
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}

@app.get("/availability", dependencies=[Depends(get_api_key)], summary="Verificar disponibilidade de consulta")
def api_check_availability(medico: str, data_desejada: str = None, horario_desejado: str = None, horario_inicial: str = None, horario_final: str = None):
    """
    Verifica a disponibilidade.
    Ex: /availability?medico=Dr.Nome&data_desejada=25/10/2025&horario_desejado=14:00
    Ex: /availability?medico=Dr.Nome (para achar o próximo livre)
    """
    print(f"API recebeu job de verificação para: {medico}. Enfileirando...")
    
    task = verify_doctors_calendar_task.delay(
        medico,
        data_desejada,
        horario_desejado,
        horario_inicial,
        horario_final
    )

    return {"status": "tarefa_enfileirada", "task_id": task.id}

@app.get("/task_status/{task_id}", summary="Verificar status de uma tarefa Celery")
def get_task_status(task_id: str):
    """
    Consulta o backend do Celery (Redis) para obter o status e o resultado de uma tarefa.
    """
    task_result = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "result": None
    }

    if task_result.successful():
        response["result"] = task_result.get() 
    elif task_result.failed():
        try:
            response["result"] = str(task_result.info) if task_result.info else "Falha sem detalhes adicionais."
        except Exception:
            response["result"] = "Erro ao obter detalhes da falha."
    return response

if __name__ == "__main__":
    print("Iniciando API de automação em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)