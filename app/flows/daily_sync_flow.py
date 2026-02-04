from prefect import flow
from app.flows.patient_flow import patient_sync_flow
from app.flows.history_flow import history_sync_flow

@flow(name="Daily Sequential Sync", log_prints=True)
async def daily_sync_flow():
    print("Iniciando fluxo diário sequencial...")
    
    print("Passo 1: Sincronização de Pacientes")
    await patient_sync_flow()
    
    print("Passo 2: Sincronização de Histórico de Agendamentos")
    await history_sync_flow()
    
    print("Fluxo diário sequencial finalizado.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(daily_sync_flow())
