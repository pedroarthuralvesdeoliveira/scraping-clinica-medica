from prefect import flow, task
from app.services.history_seed import AppointmentHistoryService

@task(
    name="Scrape Appointment History",
    retries=2,
    retry_delay_seconds=30,
    description="Busca histórico de agendamentos para pacientes ativos por sistema."
)
async def run_history_seed_task():
    service = AppointmentHistoryService()
    try:
        result = service.seed_history()
        return result
    except Exception as e:
        raise e

@flow(name="Daily Appointment History Flow", log_prints=True)
async def history_sync_flow():
    print("Iniciando busca frequente de histórico...")
    result = await run_history_seed_task()
    
    if result.get("status") == "success":
        stats = result.get("stats", {})
        print(f"Histórico atualizado: {stats.get('appointments_added')} novos agendamentos.")
    else:
        print(f"Erro ao buscar histórico: {result.get('message')}")
        
    return result

if __name__ == "__main__":
    history_sync_flow()
