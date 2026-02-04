from prefect import flow, task
from app.services.history_seed import AppointmentHistoryService

@task(
    name="Scrape Appointment History",
    retries=2,
    retry_delay_seconds=30,
    description="Busca histórico de agendamentos para pacientes ativos por sistema."
)
async def run_history_seed_task(skip_if_has_recent_history: bool = False, days_threshold: int = 7):
    service = AppointmentHistoryService()
    try:
        result = service.seed_history(
            skip_if_has_recent_history=skip_if_has_recent_history,
            days_threshold=days_threshold
        )
        return result
    except Exception as e:
        raise e

@flow(name="Daily Appointment History Flow", log_prints=True)
async def history_sync_flow(skip_if_has_recent_history: bool = False, days_threshold: int = 7):
    """
    Flow para sincronizar histórico de agendamentos.
    
    Args:
        skip_if_has_recent_history: Se True, pula pacientes que já têm histórico recente
        days_threshold: Número de dias para considerar como "recente" (default: 7)
    """
    print(f"Iniciando busca de histórico (skip_recent={skip_if_has_recent_history}, days={days_threshold})...")
    result = await run_history_seed_task(
        skip_if_has_recent_history=skip_if_has_recent_history,
        days_threshold=days_threshold
    )
    
    if result.get("status") == "success":
        stats = result.get("stats", {})
        print(f"Histórico atualizado:")
        print(f"  - Novos agendamentos: {stats.get('appointments_added')}")
        print(f"  - Pacientes processados: {stats.get('total_patients_processed')}")
        if skip_if_has_recent_history:
            print(f"  - Pacientes pulados (histórico recente): {stats.get('patients_skipped_has_recent', 0)}")
    else:
        print(f"Erro ao buscar histórico: {result.get('message')}")
        
    return result

if __name__ == "__main__":
    # Para teste local com skip habilitado
    import asyncio
    asyncio.run(history_sync_flow(skip_if_has_recent_history=True, days_threshold=7))
