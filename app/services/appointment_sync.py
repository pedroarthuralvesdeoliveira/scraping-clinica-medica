from sqlalchemy.orm import Session
from datetime import datetime, date, time as time_type
from typing import List, Optional
from app.core.database import get_session
from app.models.agendamento import Agendamento
from app.scraper.patient_history_scraper import PatientHistoryScraper


class AppointmentSyncService:
    def __init__(self):
        self.scraper = PatientHistoryScraper()

    def get_db_appointments(
        self, cpf: str, session: Session | None = None
    ) -> List[Agendamento]:
        """
        Retrieves all appointments from the database for a given CPF.
        """
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
            if not session:
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

        latest = appointments[0].data_consulta
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

    def compare_and_sync(
        self, cpf: str, nome_paciente: str, medico: str | None = None
    ) -> dict:
        """
        Compares website data with database data and syncs missing appointments.
        Returns a summary of the sync operation.
        """
        print(f"Starting sync for CPF: {cpf}, Patient: {nome_paciente}")

        website_result = self.scraper.get_patient_history(cpf)

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
                        nome_paciente=nome_paciente,
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
