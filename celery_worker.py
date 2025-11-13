import os

from celery import Celery
from dotenv import load_dotenv

from schedule_appointment import schedule_appointment as schedule_task_func
from cancel_appointment import cancel_appointment as cancel_task_func
from verify_doctors_calendar import verify_doctors_calendar as verify_task_func 

load_dotenv()

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery = Celery (
    'celery_worker', 
    broker=redis_url,
    backend=redis_url
)

@celery.task(name='schedule_appointment_task')
def schedule_appointment_task(
    medico: str, 
    data_desejada: str, 
    paciente_info: dict, 
    horario_desejado: str | None = None, 
    tipo_atendimento: str | None = "Primeira vez",
):
    print(f"Worker recebeu tarefa de agendamento para: {paciente_info.get('nome')}")
    result = schedule_task_func(medico, data_desejada, paciente_info, horario_desejado, tipo_atendimento)
    print(f"Worker finalizou tarefa de agendamento. Resultado: {result}")
    return result 

@celery.task(name='cancel_appointment_task')
def cancel_appointment_task(medico, data_desejada, horario_desejado, nome_paciente):
    print(f"Worker recebeu tarefa de cancelamento para: {nome_paciente}")
    result = cancel_task_func(medico, data_desejada, horario_desejado, nome_paciente)
    print(f"Worker finalizou tarefa de cancelamento. Resultado: {result}")
    return result

@celery.task(name='verify_doctors_calendar_task')
def verify_doctors_calendar_task(medico: str, data_desejada: str | None = None, horario_desejado: str | None = None, horario_inicial: str | None = "07:00", horario_final: str | None = "19:30"):
    print(f"Worker recebeu tarefa de verificação para: {medico}")
    result = verify_task_func(medico, data_desejada, horario_desejado, horario_inicial, horario_final)
    print(f"Worker finalizou tarefa de verificação. Resultado: {result}")
    return result

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,
)