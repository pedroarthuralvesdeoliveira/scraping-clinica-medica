from prefect import flow

from app.flows.history_flow import history_sync_flow
from app.flows.next_appointments_flow import next_appointments_sync_flow
from app.flows.patient_flow import patient_sync_flow


@flow(name="Daily Incremental Sync", log_prints=True)
async def daily_sync_flow():
    print("Iniciando fluxo diário incremental...")

    print("Passo 1: Sincronização de Pacientes")
    result_patients = await patient_sync_flow()

    print("Passo 2: Sincronização de Histórico de Agendamentos")
    reuslt_history = await history_sync_flow(
        skip_if_has_recent_history=True, days_threshold=30, workers_per_system=2
    )

    print("Passo 3: Sincronização de Próximos Agendamentos")
    result_next = await next_appointments_sync_flow()

    print("Fluxo diário sequencial finalizado.")

    return {
        "patients": result_patients,
        "history": reuslt_history,
        "next_appointments": result_next,
    }


if __name__ == "__main__":
    import asyncio

    asyncio.run(daily_sync_flow())
