from celery import shared_task
from app.scraper.appointment_scheduler import AppointmentScheduler
from app.scraper.appointment_canceller import AppointmentCanceller
from app.scraper.availability_checker import AvailabilityChecker

@shared_task(name='schedule_appointment_task')
def schedule_appointment_task(
    medico: str, 
    data_desejada: str, 
    paciente_info: dict, 
    horario_desejado: str | None = None, 
    tipo_atendimento: str | None = "Primeira vez",
):
    print(f"Worker recebeu tarefa de agendamento para: {paciente_info.get('nome')}")
    appointmentScheduler = AppointmentScheduler()
    result = appointmentScheduler.schedule_appointment(medico, data_desejada, paciente_info, horario_desejado, tipo_atendimento)
    print(f"Worker finalizou tarefa de agendamento. Resultado: {result}")
    return result 

@shared_task(name='cancel_appointment_task')
def cancel_appointment_task(medico, data_desejada, horario_desejado, nome_paciente):
    print(f"Worker recebeu tarefa de cancelamento para: {nome_paciente}")
    appointmentCanceller = AppointmentCanceller()
    result = appointmentCanceller.cancel_appointment(medico, data_desejada, horario_desejado, nome_paciente)
    print(f"Worker finalizou tarefa de cancelamento. Resultado: {result}")
    return result

@shared_task(name='verify_doctors_calendar_task')
def verify_doctors_calendar_task(medico: str, data_desejada: str | None = None, horario_desejado: str | None = None, horario_inicial: str | None = "07:00", horario_final: str | None = "19:30"):
    print(f"Worker recebeu tarefa de verificação para: {medico}")
    availabilityChecker = AvailabilityChecker()
    result = availabilityChecker.verify_doctors_calendar(medico, data_desejada, horario_desejado, horario_inicial, horario_final)
    print(f"Worker finalizou tarefa de verificação. Resultado: {result}")
    return result