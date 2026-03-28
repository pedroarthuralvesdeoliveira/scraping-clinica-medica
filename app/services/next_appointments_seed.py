from datetime import datetime, date, timedelta
from app.core.database import get_session
from app.models.agendamento import Agendamento
from app.models.enums import SistemaOrigem
from app.scraper.next_appointments import NextAppointmentsScraper
from app.services.doctor_service import get_or_create_professional
from app.models.dados_cliente import DadosCliente

class NextAppointmentsService:
    def __init__(self):
        self.scraper = NextAppointmentsScraper()

    def sync_next_appointments(self) -> dict:
        print("Starting next appointments sync process...")
        
        session = get_session()
        stats = {
            "total_scraped": 0,
            "added": 0,
            "updated": 0,
            "cancelled": 0,
            "errors": 0
        }

        try:
            # Note: NextAppointmentsScraper currently handles its own login and sequence
            # It exports an Excel and parses it.
            result = self.scraper.get_next_appointments()
            
            if result.get("status") != "success":
                print(f"Scraper failed: {result.get('message')}")
                return result

            appointments_data = result.get("appointments", [])
            stats["total_scraped"] = len(appointments_data)

            for apt_data in appointments_data:
                try:
                    codigo_str = apt_data.get("codigo")
                    if not codigo_str:
                        continue

                    codigo_int = int(codigo_str) if codigo_str.isdigit() else None
                    if not codigo_int:
                        continue

                    sistema = SistemaOrigem.OURO

                    existing = session.query(Agendamento).filter_by(
                        codigo=codigo_int,
                        sistema_origem=sistema.value,
                        data_consulta=apt_data.get("data_consulta"),
                        hora_consulta=apt_data.get("hora_consulta"),
                    ).first()

                    patient = session.query(DadosCliente).filter(
                        DadosCliente.codigo == codigo_int
                    ).first()

                    now = datetime.now()

                    if existing:
                        existing.status = apt_data.get("status")
                        existing.procedimento = apt_data.get("procedimento")
                        existing.profissional = apt_data.get("profissional") or existing.profissional
                        existing.updated_at = now
                        if patient:
                            existing.nome_paciente = patient.nomewpp or existing.nome_paciente
                            if patient.data_nascimento:
                                existing.data_nascimento = patient.data_nascimento
                        stats["updated"] += 1
                    else:
                        prof_name = apt_data.get("profissional")
                        prof_id = get_or_create_professional(session, prof_name, sistema)

                        new_apt = Agendamento(
                            paciente_id=patient.id if patient else None,
                            profissional_id=prof_id,
                            sistema_origem=sistema.value,
                            codigo=codigo_int,
                            nome_paciente=patient.nomewpp if patient and patient.nomewpp else (apt_data.get("nome_paciente") or ""),
                            telefone=apt_data.get("telefone") or "",
                            cpf=patient.cpf if patient and patient.cpf else "",
                            data_nascimento=patient.data_nascimento if patient and patient.data_nascimento else datetime(1900, 1, 1).date(),
                            data_consulta=apt_data.get("data_consulta"),
                            hora_consulta=apt_data.get("hora_consulta"),
                            profissional=prof_name or "",
                            especialidade=apt_data.get("especialidade") or "",
                            procedimento=apt_data.get("procedimento"),
                            status=apt_data.get("status"),
                            primeira_consulta=apt_data.get("primeira_consulta"),
                            observacoes=apt_data.get("observacoes"),
                            created_at=now,
                        )
                        session.add(new_apt)
                        stats["added"] += 1

                except Exception as e:
                    print(f"Error processing appointment for code {apt_data.get('codigo')}: {e}")
                    session.rollback()
                    stats["errors"] += 1

            # Detect cancelled/deleted appointments:
            # Appointments in DB within the scraped date range but NOT in the Excel
            scraped_keys = set()
            for apt_data in appointments_data:
                codigo_str = apt_data.get("codigo")
                if codigo_str and codigo_str.isdigit():
                    scraped_keys.add(
                        (int(codigo_str), apt_data.get("data_consulta"), apt_data.get("hora_consulta"))
                    )

            today = date.today()
            end_date = today + timedelta(days=30)
            sistema = SistemaOrigem.OURO

            db_future_appointments = session.query(Agendamento).filter(
                Agendamento.sistema_origem == sistema.value,
                Agendamento.data_consulta >= today,
                Agendamento.data_consulta <= end_date,
                Agendamento.status != "Cancelado",
            ).all()

            now = datetime.now()
            for db_apt in db_future_appointments:
                key = (db_apt.codigo, db_apt.data_consulta, db_apt.hora_consulta)
                if key not in scraped_keys:
                    db_apt.status = "Cancelado"
                    db_apt.updated_at = now
                    stats["cancelled"] += 1

            session.commit()
            return {"status": "success", "stats": stats}

        except Exception as e:
            session.rollback()
            print(f"Critical error in sync_next_appointments: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

if __name__ == "__main__":
    service = NextAppointmentsService()
    print(service.sync_next_appointments())
