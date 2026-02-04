from sqlalchemy.orm import Session
from datetime import datetime, date, time as time_type
from typing import List, Optional
from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.models.agendamento import Agendamento
from app.models.enums import SistemaOrigem
from app.scraper.next_appointments import NextAppointmentsScraper


class AppointmentSyncService:
    def __init__(self):
        self.scraper = NextAppointmentsScraper()

    def get_all_cpfs(self, session: Session | None = None) -> List[str]:
        """
        Retrieves all CPFs from the database.
        """
        should_close = session is None
        if not session:
            session = get_session()

        try:
            cpfs = session.query(Agendamento.cpf).distinct().all()
            return [cpf[0] for cpf in cpfs]
        finally:
            if should_close:
                session.close()

    def get_db_appointments(
        self, cpf: str, session: Session | None = None
    ) -> List[Agendamento]:
        """
        Retrieves all appointments from the database for a given CPF.
        """
        should_close = session is None
        if not session:
            session = get_session()

        try:
            appointments = (
                session.query(Agendamento)
                .filter(Agendamento.cpf == cpf)
                .order_by(Agendamento.data_consulta.desc())
                .all()
            )
            return appointments
        finally:
            if should_close:
                session.close()

    def get_latest_db_appointment_date(
        self, cpf: str, session: Session | None = None
    ) -> Optional[date]:
        """
        Gets the date of the most recent appointment for a patient in the database.
        """
        appointments = self.get_db_appointments(cpf, session)
        if not appointments:
            return None

        latest: date | None = appointments[0].data_consulta
        return latest

    def determine_appointment_type(
        self, website_appointments: List[dict], db_latest_date: Optional[date]
    ) -> dict:
        """
        Determines if the latest appointment from the website is:
        - First appointment (no history)
        - Follow-up appointment (has history)
        - Surgery (based on procedure name)
        """
        if not website_appointments:
            return {
                "is_first_appointment": False,
                "is_follow_up": False,
                "is_surgery": False,
                "reason": "No appointments found",
            }

        latest_appointment = sorted(
            website_appointments,
            key=lambda x: (
                x.get("data_consulta") or date.min,
                x.get("hora_consulta") or time_type(0, 0),
            ),
            reverse=True,
        )[0]

        procedimento = latest_appointment.get("procedimento", "").lower()
        is_surgery = any(
            keyword in procedimento
            for keyword in [
                "cirurgia",
                "surgery",
                "procedimento cirúrgico",
                "exame cirúrgico",
            ]
        )

        is_first_appointment = latest_appointment.get("primeira_consulta", False)

        has_previous_history = len(website_appointments) > 1 or (
            len(website_appointments) == 1 and not is_first_appointment
        )

        return {
            "is_first_appointment": is_first_appointment,
            "is_follow_up": has_previous_history and not is_first_appointment,
            "is_surgery": is_surgery,
            "latest_appointment": latest_appointment,
        }

    def sync_all_appointments(self) -> dict:
        """
        Syncs all appointments from the website for all systems.
        This method is designed for cronjob execution every 15 minutes.
        """
        print("Starting full appointment sync from website for all systems")
        
        systems = [SistemaOrigem.OURO, SistemaOrigem.OF]
        all_results = []
        
        added_total = 0
        updated_total = 0
        
        session = get_session()
        try:
            for sistema_enum in systems:
                print(f"\n--- Syncing system: {sistema_enum.value.upper()} ---")
                self.scraper.set_sistema(sistema_enum.value)
                website_result = self.scraper.get_next_appointments()

                if website_result.get("status") != "success":
                    print(f"Failed to fetch website data for {sistema_enum}: {website_result}")
                    continue

                website_appointments = website_result.get("appointments", [])
                print(f"Found {len(website_appointments)} appointments on website for {sistema_enum}")

                for web_app in website_appointments:
                    try:
                        codigo = web_app.get("codigo")
                        if not codigo:
                            continue
                        
                        try:
                            codigo_int = int(codigo)
                        except ValueError:
                            continue

                        # Find patient in DB
                        patient = session.query(DadosCliente).filter_by(
                            codigo=codigo_int,
                            sistema_origem=sistema_enum
                        ).first()

                        if not patient:
                            print(f"  Warning: Patient {codigo} not found in {sistema_enum.value}. Skipping.")
                            continue

                        existing_appointment = (
                            session.query(Agendamento)
                            .filter(
                                Agendamento.paciente_id == patient.id,
                                Agendamento.data_consulta == web_app.get("data_consulta"),
                                Agendamento.hora_consulta == web_app.get("hora_consulta"),
                            )
                            .first()
                        )

                        if existing_appointment:
                            existing_appointment.profissional = web_app.get("profissional")
                            existing_appointment.procedimento = web_app.get("procedimento")
                            existing_appointment.status = web_app.get("status")
                            updated_total += 1
                        else:
                            agendamento = Agendamento(
                                paciente_id=patient.id,
                                sistema_origem=sistema_enum,
                                cpf=patient.cpf,
                                codigo=patient.codigo,
                                nome_paciente=web_app.get("nome_paciente", patient.nomewpp),
                                data_consulta=web_app.get("data_consulta"),
                                hora_consulta=web_app.get("hora_consulta"),
                                data_nascimento=patient.data_nascimento or "1900-01-01",
                                telefone=web_app.get("telefone") or patient.telefone or patient.cad_telefone,
                                profissional=web_app.get("profissional"),
                                especialidade=web_app.get("especialidade") or "Padrão",
                                status=web_app.get("status"),
                                procedimento=web_app.get("procedimento"),
                                observacoes=web_app.get("observacoes") or "Sem observações",
                                canal_agendamento="website_sync",
                                created_at=datetime.now(),
                            )
                            session.add(agendamento)
                            added_total += 1

                    except Exception as e:
                        print(f"  Error processing appointment for code {codigo}: {e}")
                        continue

                session.commit()
                print(f"Completed sync for {sistema_enum.value}.")

            return {
                "status": "success",
                "new_appointments_added": added_total,
                "appointments_updated": updated_total,
                "sync_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            session.rollback()
            print(f"Critical error during full sync: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

    def compare_and_sync(
        self, cpf: str, nome_paciente: str, medico: str | None = None
    ) -> dict:
        """
        Compares website data with database data and syncs missing appointments.
        Returns a summary of the sync operation.
        """
        print(f"Starting sync for CPF: {cpf}, Patient: {nome_paciente}")

        website_result = self.scraper.get_next_appointments()

        if website_result.get("status") != "success":
            print(f"Failed to fetch website data: {website_result}")
            return {
                "status": "error",
                "message": "Failed to fetch website data",
                "details": website_result,
            }

        website_appointments = website_result.get("appointments", [])
        print(f"Found {len(website_appointments)} appointments on website")

        session = get_session()
        try:
            db_latest_date = self.get_latest_db_appointment_date(cpf, session)
            print(f"Latest DB appointment date: {db_latest_date}")

            new_appointments_to_add = []

            for web_app in website_appointments:
                web_date = web_app.get("data_consulta")
                if not web_date:
                    continue

                is_new = False
                if db_latest_date is None:
                    is_new = True
                elif web_date > db_latest_date:
                    is_new = True

                if is_new:
                    new_appointments_to_add.append(web_app)

            print(f"Found {len(new_appointments_to_add)} new appointments to sync")

            added_count = 0
            for web_app in new_appointments_to_add:
                try:
                    agendamento = Agendamento(
                        cpf=cpf,
                        codigo=web_app.get("codigo", ""),
                        nome_paciente=web_app.get("nome_paciente", nome_paciente),
                        data_consulta=web_app.get("data_consulta"),
                        hora_consulta=web_app.get("hora_consulta"),
                        profissional=web_app.get("profissional"),
                        especialidade=web_app.get("especialidade"),
                        primeira_consulta=web_app.get("primeira_consulta", False),
                        status=web_app.get("status"),
                        procedimento=web_app.get("procedimento"),
                        observacoes=web_app.get("observacoes"),
                        canal_agendamento="website_sync",
                        created_at=datetime.now(),
                    )

                    session.add(agendamento)
                    added_count += 1
                    print(
                        f"Added appointment: {web_app.get('data_consulta')} at {web_app.get('hora_consulta')}"
                    )
                except Exception as e:
                    print(f"Error adding appointment: {e}")
                    continue

            session.commit()

            appointment_type_info = self.determine_appointment_type(
                website_appointments, db_latest_date
            )

            return {
                "status": "success",
                "cpf": cpf,
                "total_website_appointments": len(website_appointments),
                "new_appointments_added": added_count,
                "latest_db_date": db_latest_date,
                "appointment_type_info": appointment_type_info,
            }

        except Exception as e:
            session.rollback()
            print(f"Error during sync: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()

    def sync_all_recent_patients(self, days_back: int = 7) -> dict:
        """
        Syncs appointments for all patients who had appointments in the last N days.
        """
        session = get_session()
        try:
            cutoff_date = datetime.now().date()

            recent_appointments = (
                session.query(Agendamento.cpf, Agendamento.nome_paciente)
                .filter(Agendamento.data_consulta >= cutoff_date)
                .distinct()
                .all()
            )

            print(f"Found {len(recent_appointments)} recent patients to sync")

            sync_results = []
            for cpf, nome_paciente in recent_appointments:
                result = self.compare_and_sync(cpf, nome_paciente)
                sync_results.append(result)

            successful_syncs = sum(
                1 for r in sync_results if r.get("status") == "success"
            )
            total_new_appointments = sum(
                r.get("new_appointments_added", 0) for r in sync_results
            )

            return {
                "status": "success",
                "total_patients_synced": len(recent_appointments),
                "successful_syncs": successful_syncs,
                "total_new_appointments": total_new_appointments,
                "details": sync_results,
            }

        except Exception as e:
            print(f"Error in sync_all_recent_patients: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()

if __name__ == "__main__":
    sync = AppointmentSyncService()
    # sync.sync_all_appointments()
    cpfs = sync.get_all_cpfs()
    print(cpfs)