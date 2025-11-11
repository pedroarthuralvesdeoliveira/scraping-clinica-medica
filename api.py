import uvicorn
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
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
    convenio: str | None = None

class CancelPayload(BaseModel):
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str


API_KEY = os.environ.get("API_KEY", "SUA_CHAVE_DE_API") 
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
        "tipo_atendimento": payload.tipo_atendimento,
        "convenio": payload.convenio
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
    task_result_obj: AsyncResult = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "status": task_result_obj.status,
        "result": None
    }

    if task_result_obj.ready():
        result = task_result_obj.get()
        response["result"] = result

        if isinstance(result, dict) and result.get("status") == "unavailable":
            return JSONResponse(status_code=409, content=response)
        elif isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=500, content=response) 

    elif task_result_obj.status == "PENDING":
        response["result"] = "Tarefa ainda não iniciada."
    elif task_result_obj.status == "STARTED":
        response["result"] = "Tarefa em execução."

    return JSONResponse(status_code=200, content=response)


if __name__ == "__main__":
    print("Iniciando API de automação em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)