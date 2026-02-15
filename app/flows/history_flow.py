from prefect import flow, task
from app.services.history_seed import AppointmentHistoryService


def _get_patient_count(sistema_str: str) -> int:
    """Returns the number of patients for a given system."""
    from app.core.database import get_session
    from app.models.dados_cliente import DadosCliente
    session = get_session()
    try:
        return session.query(DadosCliente).filter_by(sistema_origem=sistema_str).count()
    finally:
        session.close()


@task(
    name="Scrape History - Sistema/Chunk",
    retries=1,
    retry_delay_seconds=60,
    description="Busca histórico de agendamentos para um sistema (com suporte a offset/limit para paralelismo)."
)
def run_history_for_sistema(
    sistema_filter: str,
    offset: int = 0,
    limit: int | None = None,
    skip_if_has_recent_history: bool = False,
    days_threshold: int = 7,
):
    """
    Synchronous task so Prefect runs it in a thread pool (ConcurrentTaskRunner),
    allowing true parallelism with blocking Selenium code.
    Each invocation creates its own Chrome instance.
    """
    service = AppointmentHistoryService()
    return service.seed_history(
        sistema_filter=sistema_filter,
        offset=offset,
        limit=limit,
        skip_if_has_recent_history=skip_if_has_recent_history,
        days_threshold=days_threshold,
    )


@flow(
    name="Daily Appointment History Flow",
    log_prints=True,
)
def history_sync_flow(
    skip_if_has_recent_history: bool = False,
    days_threshold: int = 7,
    workers_per_system: int = 1,
):
    """
    Flow para sincronizar histórico de agendamentos.

    Args:
        skip_if_has_recent_history: Pula pacientes que já têm histórico recente no DB.
        days_threshold: Número de dias para considerar como "recente" (default: 7).
        workers_per_system: Número de workers (Chromes) por sistema. Default 1.
            workers_per_system=1 → OURO e OF rodam em paralelo (2 Chromes total).
            workers_per_system=2 → 4 Chromes total, cada sistema dividido em 2 chunks.
    """
    sistemas = ["ouro", "of"]
    futures = []

    for sistema in sistemas:
        if workers_per_system <= 1:
            f = run_history_for_sistema.submit(
                sistema,
                skip_if_has_recent_history=skip_if_has_recent_history,
                days_threshold=days_threshold,
            )
            futures.append((sistema, f))
        else:
            total = _get_patient_count(sistema)
            chunk = max(1, -(-total // workers_per_system))  # ceil division
            print(f"[{sistema}] {total} pacientes → {workers_per_system} workers, ~{chunk} por worker")
            for i in range(workers_per_system):
                offset = i * chunk
                if offset >= total:
                    break
                label = f"{sistema}[{offset}:{offset + chunk}]"
                f = run_history_for_sistema.submit(
                    sistema,
                    offset=offset,
                    limit=chunk,
                    skip_if_has_recent_history=skip_if_has_recent_history,
                    days_threshold=days_threshold,
                )
                futures.append((label, f))

    # Collect results (blocks until all tasks finish)
    total_added = 0
    total_processed = 0
    total_skipped = 0
    total_errors = 0

    for label, f in futures:
        result = f.result()
        if result.get("status") == "success":
            stats = result.get("stats", {})
            added = stats.get("appointments_added", 0)
            processed = stats.get("total_patients_processed", 0)
            skipped = stats.get("patients_skipped_has_recent", 0)
            errors = stats.get("errors", 0)
            total_added += added
            total_processed += processed
            total_skipped += skipped
            total_errors += errors
            print(f"  [{label}] +{added} agendamentos, {processed} pacientes, {errors} erros")
        else:
            print(f"  [{label}] ERRO: {result.get('message')}")

    print(f"Histórico atualizado: {total_added} novos agendamentos, {total_processed} pacientes processados")
    if skip_if_has_recent_history:
        print(f"  Pacientes pulados (histórico recente): {total_skipped}")
    if total_errors:
        print(f"  Erros: {total_errors}")

    return {
        "status": "success",
        "stats": {
            "appointments_added": total_added,
            "total_patients_processed": total_processed,
            "patients_skipped_has_recent": total_skipped,
            "errors": total_errors,
        },
    }


if __name__ == "__main__":
    history_sync_flow(skip_if_has_recent_history=True, days_threshold=7)
