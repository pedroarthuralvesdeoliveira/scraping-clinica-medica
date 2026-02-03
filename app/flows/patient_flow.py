from prefect import flow, task
from app.services.patient_seed import PatientSeedService

@task(
    name="Sync Patients Data",
    retries=3, 
    retry_delay_seconds=60,
    description="Extrai pacientes do Excel e atualiza CPFs no banco de dados."
)
async def run_patient_seed_task():
    service = PatientSeedService()
    try:
        result = service.seed_patients()
        return result
    except Exception as e:
        raise e

@flow(name="Main Patient Sync Flow", log_prints=True)
async def patient_sync_flow():
    print("Iniciando a orquestração do fluxo de pacientes...")
    
    result = await run_patient_seed_task()
    
    if result.get("status") == "success":
        print(f"Sincronização concluída com sucesso: {result.get('added')} novos, {result.get('updated')} atualizados.")
    else:
        print(f"Erro na sincronização: {result.get('message')}")
        
    return result

if __name__ == "__main__":
    patient_sync_flow()
