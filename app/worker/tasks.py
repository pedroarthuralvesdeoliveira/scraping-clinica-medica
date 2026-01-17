from celery import shared_task
import redis
from contextlib import contextmanager
from app.core.dependencies import get_settings
from app.scraper.appointment_scheduler import AppointmentScheduler
from app.scraper.appointment_canceller import AppointmentCanceller
from app.scraper.availability_checker import AvailabilityChecker
from app.services.appointment_sync import AppointmentSyncService

settings = get_settings()
redis_url = settings.redis_url
if "localhost" in redis_url:
    redis_url = redis_url.replace("localhost", "127.0.0.1")

redis_client = redis.from_url(redis_url)


@contextmanager
def redis_lock(lock_name, timeout=60, expire=300):
    """
    Simples implementação de Lock distribuído com Redis.
    timeout: Tempo máximo esperando para adquirir o lock.
    expire: Tempo de vida do lock (evita deadlock se o worker morrer).
    """
    lock = redis_client.lock(lock_name, timeout=expire)
    acquired = lock.acquire(blocking=True, blocking_timeout=timeout)

    if not acquired:
        raise Exception(
            f"Não foi possível adquirir o lock para {lock_name} após {timeout} segundos."
        )

    try:
        yield
    finally:
        try:
            if lock.owned():
                lock.release()
        except Exception:
            pass


@shared_task(name="schedule_appointment_task")
def schedule_appointment_task(
    medico: str,
    data_desejada: str,
    paciente_info: dict,
    horario_desejado: str | None = None,
    tipo_atendimento: str | None = "Primeira vez",
):
    print(f"Worker recebeu tarefa de agendamento para: {paciente_info.get('nome')}")

    cpf = paciente_info.get("cpf", "unknown")
    nome = paciente_info.get("nome", "unknown")
    horario = horario_desejado if horario_desejado else "any"
    lock_key = f"lock:schedule:{medico}:{data_desejada}:{horario}:{cpf}"

    print(f"Tentando adquirir lock: {lock_key}")

    try:
        with redis_lock(lock_key, timeout=30, expire=300):
            print(f"Lock adquirido: {lock_key}. Iniciando agendamento...")
            appointmentScheduler = AppointmentScheduler()
            result = appointmentScheduler.schedule_appointment(
                medico, data_desejada, paciente_info, horario_desejado, tipo_atendimento
            )
            print(f"Worker finalizou tarefa de agendamento. Resultado: {result}")

            if result.get("status") == "success":
                print("Agendamento bem-sucedido. Iniciando sincronização...")
                sync_result = sync_patient_appointments_task(cpf, nome, medico)
                result["sync_result"] = sync_result

            return result
    except Exception as e:
        print(f"Erro ao processar tarefa de agendamento (Lock/Outro): {e}")
        return {
            "status": "error",
            "message": f"Falha na execução ou lock timeout: {str(e)}",
        }


@shared_task(name="cancel_appointment_task")
def cancel_appointment_task(
    medico, data_desejada, horario_desejado, nome_paciente, cpf=None
):
    print(f"Worker recebeu tarefa de cancelamento para: {nome_paciente}")
    appointmentCanceller = AppointmentCanceller()
    result = appointmentCanceller.cancel_appointment(
        medico, data_desejada, horario_desejado, nome_paciente
    )
    print(f"Worker finalizou tarefa de cancelamento. Resultado: {result}")

    if result.get("status") == "success" and cpf:
        print("Cancelamento bem-sucedido. Iniciando sincronização...")
        sync_result = sync_patient_appointments_task(cpf, nome_paciente, medico)
        result["sync_result"] = sync_result

    return result


@shared_task(name="verify_doctors_calendar_task")
def verify_doctors_calendar_task(
    medico: str,
    data_desejada: str | None = None,
    horario_desejado: str | None = None,
    horario_inicial: str | None = "07:00",
    horario_final: str | None = "19:30",
):
    print(f"Worker recebeu tarefa de verificação para: {medico}")
    availabilityChecker = AvailabilityChecker()
    result = availabilityChecker.verify_doctors_calendar(
        medico, data_desejada, horario_desejado, horario_inicial, horario_final
    )
    print(f"Worker finalizou tarefa de verificação. Resultado: {result}")
    return result


@shared_task(name="sync_patient_appointments_task")
def sync_patient_appointments_task(
    cpf: str, nome_paciente: str, medico: str | None = None
):
    print(f"Worker recebeu tarefa de sincronização para CPF: {cpf}")

    lock_key = f"lock:sync:{cpf}"

    try:
        with redis_lock(lock_key, timeout=30, expire=300):
            sync_service = AppointmentSyncService()
            result = sync_service.compare_and_sync(cpf, nome_paciente, medico)
            print(f"Worker finalizou tarefa de sincronização. Resultado: {result}")
            return result
    except Exception as e:
        print(f"Erro ao processar tarefa de sincronização: {e}")
        return {
            "status": "error",
            "message": f"Falha na execução ou lock timeout: {str(e)}",
        }


@shared_task(name="sync_all_recent_patients_task")
def sync_all_recent_patients_task():
    print("Worker iniciou tarefa de sincronização de todos os pacientes recentes")

    lock_key = "lock:sync_all"

    try:
        with redis_lock(lock_key, timeout=300, expire=1800):
            sync_service = AppointmentSyncService()
            result = sync_service.sync_all_recent_patients(days_back=30)
            print(
                f"Worker finalizou tarefa de sincronização de todos os pacientes. Resultado: {result}"
            )
            return result
    except Exception as e:
        print(f"Erro ao processar tarefa de sincronização de todos os pacientes: {e}")
        return {
            "status": "error",
            "message": f"Falha na execução ou lock timeout: {str(e)}",
        }
