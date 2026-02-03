from prefect import flow, task
from app.services.next_appointments_seed import NextAppointmentsService

@task(
    name="Sync Next Appointments",
    retries=2,
    retry_delay_seconds=30,
    description="Busca próximos agendamentos e atualiza no banco de dados."
)
async def run_next_appointments_task():
    service = NextAppointmentsService()
    try:
        result = service.sync_next_appointments()
        return result
    except Exception as e:
        raise e

@flow(name="Next Appointments Sync Flow", log_prints=True)
async def next_appointments_sync_flow():
    print("Iniciando busca frequente de próximos agendamentos...")
    result = await run_next_appointments_task()
    
    if result.get("status") == "success":
        stats = result.get("stats", {})
        print(f"Sincronização concluída: {stats.get('added')} novos, {stats.get('updated')} atualizados.")
    else:
        print(f"Erro ao buscar agendamentos: {result.get('message')}")
        
    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(next_appointments_sync_flow())
