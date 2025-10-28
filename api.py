import uvicorn
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from schedule_appointment import schedule_appointment
from cancel_appointment import cancel_appointment
from verify_doctors_calendar import verify_doctors_calendar

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


API_KEY = os.environ.get("API_KEY", "SUA_CHAVE_SECRETA_MUITO_FORTE") 
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
    print(f"Recebido job de agendamento para: {payload.nome_paciente}")
    
    paciente_info = {
        "nome": payload.nome_paciente,
        "data_nascimento": payload.data_nascimento,
        "cpf": payload.cpf,
        "telefone": payload.telefone,
        "tipo_atendimento": payload.tipo_atendimento
    }

    resultado = schedule_appointment(
        payload.medico,
        payload.data_desejada,
        paciente_info,             
        payload.horario_desejado,  
        payload.tipo_atendimento
    )
    return resultado

@app.post("/cancel", dependencies=[Depends(get_api_key)], summary="Cancelar consulta")
def api_cancel(payload: CancelPayload):
    """
    Recebe um JSON do N8N e cancela uma consulta.
    """
    print(f"Recebido job de cancelamento para: {payload.nome_paciente}")
    resultado = cancel_appointment(
        payload.medico,
        payload.data_desejada,
        payload.horario_desejado,
        payload.nome_paciente
    )
    return resultado

@app.get("/availability", dependencies=[Depends(get_api_key)], summary="Verificar disponibilidade de consulta")
def api_check_availability(medico: str, data_desejada: str = None, horario_desejado: str = None, horario_inicial: str = None, horario_final: str = None):
    """
    Verifica a disponibilidade.
    Ex: /availability?medico=Dr.Nome&data_desejada=25/10/2025&horario_desejado=14:00
    Ex: /availability?medico=Dr.Nome (para achar o próximo livre)
    """
    print(f"Recebido job de verificação para: {medico}")
    resultado = verify_doctors_calendar(
        medico,
        data_desejada,
        horario_desejado,
        horario_inicial,
        horario_final
    )
    return resultado

if __name__ == "__main__":
    print("Iniciando API de automação em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)