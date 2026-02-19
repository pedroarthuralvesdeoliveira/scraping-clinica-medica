from app.scraper.patient_history_scraper import PatientHistoryScraper
from app.scraper.next_appointments import NextAppointmentsScraper
from app.scraper.get_active_patients import GetActivePatients
from celery import shared_task
import redis
from contextlib import contextmanager
from app.core.dependencies import get_settings
from app.scraper.appointment_scheduler import AppointmentScheduler
from app.scraper.appointment_canceller import AppointmentCanceller
from app.scraper.availability_checker import AvailabilityChecker

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

    appointmentScheduler = None
    try:
        with redis_lock(lock_key, timeout=30, expire=300):
            print(f"Lock adquirido: {lock_key}. Iniciando agendamento...")
            appointmentScheduler = AppointmentScheduler()
            result = appointmentScheduler.schedule_appointment(
                medico, data_desejada, paciente_info, horario_desejado, tipo_atendimento
            )
            print(f"Worker finalizou tarefa de agendamento. Resultado: {result}")

            return result
    except Exception as e:
        print(f"Erro ao processar tarefa de agendamento (Lock/Outro): {e}")
        return {
            "status": "error",
            "message": f"Falha na execução ou lock timeout: {str(e)}",
        }
    finally:
        if appointmentScheduler:
            appointmentScheduler.quit()


@shared_task(name="cancel_appointment_task")
def cancel_appointment_task(
    medico, data_desejada, horario_desejado, nome_paciente, cpf=None
):
    print(f"Worker recebeu tarefa de cancelamento para: {nome_paciente}")
    appointmentCanceller = AppointmentCanceller()
    try:
        result = appointmentCanceller.cancel_appointment(
            medico, data_desejada, horario_desejado, nome_paciente
        )
        print(f"Worker finalizou tarefa de cancelamento. Resultado: {result}")
        return result
    except Exception as e:
        print(f"Erro ao processar tarefa de cancelamento: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        appointmentCanceller.quit()


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
    try:
        result = availabilityChecker.verify_doctors_calendar(
            medico, data_desejada, horario_desejado, horario_inicial, horario_final
        )
        print(f"Worker finalizou tarefa de verificação. Resultado: {result}")
        return result
    except Exception as e:
        print(f"Erro ao processar tarefa de verificação: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        availabilityChecker.quit()


@shared_task(name="get_patient_history_task")
def get_patient_history_task(telefone: str):
    """
    Scrapes patient appointment history by phone number.
    Looks up the patient code from DB, then scrapes history from the website.
    Returns the scraped data directly without persisting to DB.
    """
    from app.core.database import get_session
    from app.models.dados_cliente import DadosCliente

    print(f"Worker recebeu tarefa de histórico para telefone: {telefone}")

    # TODO: puxa do scraping, não do banco

    ## Primeiro buscamos o código do paciente no banco usando o telefone
    
    session = get_session()
    try:
        patient = session.query(DadosCliente).filter(
            DadosCliente.telefone == telefone
        ).first()
        
        if not patient or not patient.codigo:
            return {
                "status": "error",
                "message": f"Paciente não encontrado para telefone: {telefone}"
            }
        
        patient_code = str(patient.codigo)
        print(f"Código encontrado: {patient_code} para telefone: {telefone}")
    finally:
        session.close()
    
    scraper = PatientHistoryScraper()
    try:
        result = scraper.get_patient_history(patient_code, search_type="codigo")
        print(f"Worker finalizou busca de histórico. Status: {result.get('status')}")
        return result
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        scraper.close()


@shared_task(name="get_next_appointments_task")
def get_next_appointments_task(sistema: str = "OF"):
    """
    Scrapes upcoming appointments from the website via Excel export.
    Returns the scraped data directly without persisting to DB.
    """
    print(f"Worker recebeu tarefa de próximos agendamentos ({sistema})")
    scraper = NextAppointmentsScraper()
    try:
        scraper.set_sistema(sistema)
        result = scraper.get_next_appointments()
        
        appointments = result.get("appointments", [])
        if not appointments and sistema != "OURO":
            print(f"Nenhum agendamento encontrado no sistema {sistema}. Tentando sistema OURO...")
            scraper.set_sistema("OURO")
            result = scraper.get_next_appointments()
            
        print(f"Worker finalizou busca de próximos agendamentos. Status: {result.get('status')}")
        return result
    except Exception as e:
        print(f"Erro ao buscar próximos agendamentos: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        scraper.close()


@shared_task(name="get_active_patients_task")
def get_active_patients_task():
    """
    Scrapes all active patients from the website.
    Returns the scraped data directly without persisting to DB.
    """
    print("Worker recebeu tarefa de pacientes ativos")
    scraper = GetActivePatients()
    try:
        result = scraper.get_all_active_patients()
        print(f"Worker finalizou busca de pacientes ativos. Status: {result.get('status')}")
        return result
    except Exception as e:
        print(f"Erro ao buscar pacientes ativos: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        scraper.close()


@shared_task(name="search_patient_history_task")
def search_patient_history_task(search_type: str, search_value: str):
    """
    Searches for a patient by name, CPF, phone, or date of birth.
    Looks up in the database first, then scrapes from endoclin if not found.
    Searches both OF and OURO systems. Returns only future appointments.
    """
    from app.core.database import get_session
    from app.models.dados_cliente import DadosCliente
    from app.models.telefones_paciente import TelefonesPaciente
    from app.models.enums import SistemaOrigem
    from datetime import datetime
    from sqlalchemy import or_
    import re

    print(f"Worker recebeu busca de histórico: tipo={search_type}, valor={search_value}")

    scraper_type_map = {
        "nome": "nome",
        "cpf": "cpf",
        "telefone": "telefone",
        "data_nascimento": "dataNascimento",
    }
    scraper_search_type = scraper_type_map.get(search_type, search_type)

    session = get_session()
    scraper = PatientHistoryScraper()
    all_appointments = []
    patients_found = []

    try:
        if search_type == "data_nascimento":
            patients_with_apts = _search_by_birth_date(
                session, scraper, search_value, SistemaOrigem
            )
            return {
                "status": "success",
                "search_type": search_type,
                "search_value": search_value,
                "patients": patients_with_apts,
                "total_count": sum(len(p["appointments"]) for p in patients_with_apts),
            }

        for sistema_str in ["OF", "OURO"]:
            sistema_enum = SistemaOrigem(sistema_str)
            print(f"\n--- Processando sistema: {sistema_str} ---")

            scraper.set_sistema(sistema_str)

            # Step 1: Try to find patient in database
            patient = _find_patient_in_db(
                session, search_type, search_value, sistema_enum
            )

            if patient and patient.codigo:
                identifier = str(patient.codigo)
                effective_search_type = "codigo"
                patients_found.append({
                    "id": patient.id,
                    "nome": patient.nomewpp,
                    "codigo": patient.codigo,
                    "sistema": sistema_str,
                    "source": "database",
                })
                print(
                    f"Paciente encontrado no banco: codigo={patient.codigo}, "
                    f"nome={patient.nomewpp}, sistema={sistema_str}"
                )
            elif patient and not patient.codigo:
                identifier = search_value
                effective_search_type = scraper_search_type
                patients_found.append({
                    "id": patient.id,
                    "nome": patient.nomewpp,
                    "codigo": None,
                    "sistema": sistema_str,
                    "source": "database_sem_codigo",
                })
                print(
                    f"Paciente no banco sem codigo: nome={patient.nomewpp}, "
                    f"sistema={sistema_str}. Buscando na endoclin por {search_type}."
                )
            else:
                identifier = search_value
                effective_search_type = scraper_search_type
                print(
                    f"Paciente não encontrado no banco para {sistema_str}. "
                    f"Buscando na endoclin por {search_type}."
                )

            # Step 2: Scrape appointment history
            try:
                result = scraper.get_patient_history(
                    identifier, search_type=effective_search_type
                )

                if result.get("status") == "success":
                    appointments = result.get("appointments", [])

                    for apt in appointments:
                        apt["sistema"] = sistema_str

                    all_appointments.extend(appointments)
                    print(
                        f"Encontrados {len(appointments)} agendamentos em {sistema_str}."
                    )

                    if patient is None:
                        scraped = result.get("patient_info")
                        if scraped and scraped.get("codigo"):
                            found = session.query(DadosCliente).filter(
                                DadosCliente.codigo == int(scraped["codigo"]),
                                DadosCliente.sistema_origem == sistema_enum,
                            ).first()
                            if found:
                                try:
                                    dob = datetime.strptime(search_value, "%d/%m/%Y").date()
                                    found.data_nascimento = dob
                                    session.commit()
                                    print(
                                        f"data_nascimento atualizada para paciente "
                                        f"codigo={found.codigo}, sistema={sistema_str}"
                                    )
                                except Exception as e:
                                    session.rollback()
                                    print(f"Erro ao atualizar data_nascimento: {e}")
                                patients_found.append({
                                    "id": found.id,
                                    "nome": found.nomewpp,
                                    "codigo": found.codigo,
                                    "sistema": sistema_str,
                                    "source": "database_updated",
                                })
                            else:
                                patients_found.append({
                                    "id": None,
                                    "nome": scraped.get("nome"),
                                    "codigo": scraped.get("codigo"),
                                    "sistema": sistema_str,
                                    "source": "scraper",
                                })
                else:
                    print(
                        f"Scraper retornou erro para {sistema_str}: "
                        f"{result.get('message')}"
                    )
            except Exception as e:
                print(f"Erro no scraping de {sistema_str}: {e}")
                continue

        # Group appointments by sistema and embed in each patient
        apts_by_sistema = {}
        for apt in all_appointments:
            apts_by_sistema.setdefault(apt["sistema"], []).append(apt)

        # Sort each group by date descending
        for sistema_apts in apts_by_sistema.values():
            sistema_apts.sort(
                key=lambda x: datetime.strptime(x["data_atendimento"], "%d/%m/%Y"),
                reverse=True,
            )

        patients_with_apts = []
        for p in patients_found:
            entry = dict(p)
            entry["appointments"] = apts_by_sistema.get(p["sistema"], [])
            patients_with_apts.append(entry)

        return {
            "status": "success",
            "search_type": search_type,
            "search_value": search_value,
            "patients": patients_with_apts,
            "total_count": len(all_appointments),
        }

    except Exception as e:
        print(f"Erro em search_patient_history_task: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        session.close()
        scraper.quit()


def _search_by_birth_date(session, scraper, birth_date_str: str, SistemaOrigem) -> list[dict]:
    """
    Searches for ALL patients matching a birth date across OF and OURO systems.
    For each match, retrieves appointment history by patient code.
    Returns list of patient dicts each with their own 'appointments' list.
    """
    from app.models.dados_cliente import DadosCliente
    from datetime import datetime

    results = []

    for sistema_str in ["OF", "OURO"]:
        sistema_enum = SistemaOrigem(sistema_str)
        scraper.set_sistema(sistema_str)
        print(f"\n--- Busca por data_nascimento no sistema: {sistema_str} ---")

        # Get all matching codes from the website search
        website_patients = scraper.get_patient_codes_from_search(
            birth_date_str, "data_nascimento"
        )

        if not website_patients:
            print(f"Nenhum paciente encontrado no site {sistema_str} para {birth_date_str}.")
            continue

        for wp in website_patients:
            codigo_int = int(wp["codigo"])

            # Check if patient exists in DB
            db_patient = session.query(DadosCliente).filter(
                DadosCliente.codigo == codigo_int,
                DadosCliente.sistema_origem == sistema_enum,
            ).first()

            source = "database" if db_patient else "scraper"

            # Update data_nascimento in DB if missing
            if db_patient and not db_patient.data_nascimento:
                try:
                    dob = datetime.strptime(birth_date_str, "%d/%m/%Y").date()
                    db_patient.data_nascimento = dob
                    session.commit()
                    print(f"data_nascimento atualizada para codigo={codigo_int}, sistema={sistema_str}")
                except Exception as e:
                    session.rollback()
                    print(f"Erro ao atualizar data_nascimento: {e}")

            # Scrape history by code (unique result, no ambiguity)
            try:
                result = scraper.get_patient_history(wp["codigo"], search_type="codigo")
            except Exception as e:
                print(f"Erro ao buscar histórico do codigo {wp['codigo']}: {e}")
                result = {"status": "error"}

            appointments: list = []
            if result.get("status") == "success":
                raw = result.get("appointments")
                appointments = raw if isinstance(raw, list) else []
                for apt in appointments:
                    apt["sistema"] = sistema_str
                appointments.sort(
                    key=lambda x: datetime.strptime(x["data_atendimento"], "%d/%m/%Y"),
                    reverse=True,
                )
                print(f"  {len(appointments)} agendamento(s) para {wp['nome']} ({sistema_str})")

            results.append({
                "id": db_patient.id if db_patient else None,
                "nome": db_patient.nomewpp if db_patient else wp["nome"],
                "codigo": codigo_int,
                "sistema": sistema_str,
                "source": source,
                "appointments": appointments,
            })

    return results


def _find_patient_in_db(session, search_type, search_value, sistema_enum):
    """
    Searches for a patient in dados_cliente by the given criteria.
    Returns the first matching DadosCliente or None.
    """
    from app.models.dados_cliente import DadosCliente
    from app.models.telefones_paciente import TelefonesPaciente
    from datetime import datetime
    from sqlalchemy import or_
    import re

    base_query = session.query(DadosCliente).filter(
        DadosCliente.sistema_origem == sistema_enum
    )

    if search_type == "nome":
        return base_query.filter(
            DadosCliente.nomewpp.ilike(f"%{search_value}%")
        ).first()

    elif search_type == "cpf":
        cpf_digits = re.sub(r"\D", "", search_value)
        return base_query.filter(
            DadosCliente.cpf == cpf_digits
        ).first()

    elif search_type == "telefone":
        phone_digits = re.sub(r"\D", "", search_value)
        if not phone_digits:
            return None

        # Check dados_cliente.telefone and cad_telefone
        patient = base_query.filter(
            or_(
                DadosCliente.telefone.like(f"%{phone_digits}%"),
                DadosCliente.cad_telefone.like(f"%{phone_digits}%"),
            )
        ).first()

        if patient:
            return patient

        # Check telefones_paciente table
        tel_record = session.query(TelefonesPaciente).join(
            DadosCliente,
            TelefonesPaciente.cliente_codigo == DadosCliente.id
        ).filter(
            DadosCliente.sistema_origem == sistema_enum,
            TelefonesPaciente.numero.like(f"%{phone_digits}%"),
        ).first()

        if tel_record:
            return session.query(DadosCliente).get(tel_record.cliente_codigo)

        return None

    elif search_type == "data_nascimento":
        try:
            dob = datetime.strptime(search_value, "%d/%m/%Y").date()
        except ValueError:
            print(f"Formato de data inválido: {search_value}. Esperado DD/MM/YYYY.")
            return None

        return base_query.filter(
            DadosCliente.data_nascimento == dob
        ).first()

    return None