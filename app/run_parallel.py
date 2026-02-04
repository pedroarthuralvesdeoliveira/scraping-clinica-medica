"""
Parallel History Sync Runner

Automatically divides patients into chunks and runs multiple workers in parallel.

Usage:
    uv run -m app.run_parallel --workers 4 --sistema ouro
    uv run -m app.run_parallel --workers 8 --sistema of
    uv run -m app.run_parallel --workers 4  # Both systems
"""

import sys
import os
import argparse
import math
from multiprocessing import Process, Queue
from datetime import datetime

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.models.enums import SistemaOrigem
from app.services.history_seed import AppointmentHistoryService


def get_patient_count(sistema: str | None = None) -> dict[str, int]:
    """Count patients per system from the database."""
    session = get_session()
    try:
        counts = {}
        
        systems = []
        if sistema:
            if sistema.lower() == 'ouro':
                systems = [SistemaOrigem.OURO]
            elif sistema.lower() == 'of':
                systems = [SistemaOrigem.OF]
        else:
            systems = [SistemaOrigem.OURO, SistemaOrigem.OF]
        
        for sistema_enum in systems:
            count = session.query(DadosCliente).filter(
                DadosCliente.sistema_origem == sistema_enum,
                DadosCliente.codigo.isnot(None)
            ).count()
            counts[sistema_enum.value] = count
        
        return counts
    finally:
        session.close()


def worker_process(worker_id: int, sistema: str, offset: int, limit: int, result_queue: Queue):
    """
    Worker process that handles a chunk of patients.
    Each worker has its own Selenium instance and database connection.
    """
    print(f"[Worker {worker_id}] Starting - Sistema: {sistema.upper()}, Offset: {offset}, Limit: {limit}")
    
    try:
        service = AppointmentHistoryService()
        result = service.seed_history(
            offset=offset,
            limit=limit,
            sistema_filter=sistema
        )
        
        result_queue.put({
            "worker_id": worker_id,
            "sistema": sistema,
            "offset": offset,
            "limit": limit,
            "result": result
        })
        
        print(f"[Worker {worker_id}] Completed - Stats: {result.get('stats', {})}")
        
    except Exception as e:
        print(f"[Worker {worker_id}] ERROR: {e}")
        result_queue.put({
            "worker_id": worker_id,
            "sistema": sistema,
            "offset": offset,
            "limit": limit,
            "error": str(e)
        })


def run_parallel_sync(workers: int, sistema: str | None = None):
    """
    Main function to run parallel sync.
    Divides patients into chunks and spawns worker processes.
    """
    print("=" * 60)
    print("PARALLEL HISTORY SYNC")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Workers: {workers}")
    print(f"Sistema: {sistema or 'all'}")
    print("=" * 60)
    
    # Get patient counts
    counts = get_patient_count(sistema)
    print(f"\nPatient counts: {counts}")
    
    if not counts:
        print("No patients found to process.")
        return
    
    # Create work chunks
    work_chunks = []
    
    for sys_name, total in counts.items():
        if total == 0:
            continue
            
        # Divide patients among workers for this system
        chunk_size = math.ceil(total / workers)
        
        print(f"\n{sys_name.upper()}: {total} patients, {chunk_size} per worker")
        
        for i in range(workers):
            offset = i * chunk_size
            if offset >= total:
                break  # No more patients to process
            
            # Last chunk might be smaller
            limit = min(chunk_size, total - offset)
            
            work_chunks.append({
                "sistema": sys_name,
                "offset": offset,
                "limit": limit
            })
            print(f"  Chunk {i+1}: offset={offset}, limit={limit}")
    
    if not work_chunks:
        print("No work chunks created.")
        return
    
    # Create result queue
    result_queue = Queue()
    
    # Spawn worker processes
    processes = []
    print(f"\nSpawning {len(work_chunks)} worker processes...")
    
    for idx, chunk in enumerate(work_chunks):
        p = Process(
            target=worker_process,
            args=(idx + 1, chunk["sistema"], chunk["offset"], chunk["limit"], result_queue)
        )
        processes.append(p)
        p.start()
        print(f"  Started worker {idx + 1} (PID: {p.pid})")
    
    # Wait for all processes to complete
    print("\nWaiting for workers to complete...")
    for p in processes:
        p.join()
    
    # Collect results
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    total_stats = {
        "total_patients_processed": 0,
        "appointments_added": 0,
        "appointments_skipped_existing": 0,
        "errors": 0
    }
    
    while not result_queue.empty():
        result = result_queue.get()
        worker_id = result.get("worker_id")
        
        if "error" in result:
            print(f"Worker {worker_id}: ERROR - {result['error']}")
            total_stats["errors"] += 1
        else:
            stats = result.get("result", {}).get("stats", {})
            print(f"Worker {worker_id}: {stats}")
            
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
    
    print("\n" + "-" * 40)
    print("TOTAL:")
    for key, value in total_stats.items():
        print(f"  {key}: {value}")
    
    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Run parallel history sync with multiple workers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run -m app.run_parallel --workers 4 --sistema ouro
  uv run -m app.run_parallel --workers 8 --sistema of
  uv run -m app.run_parallel --workers 4  # Both systems
        """
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--sistema", "-s",
        type=str,
        default=None,
        choices=["ouro", "of"],
        help="Filter by system (ouro or of). If not specified, processes both."
    )
    
    args = parser.parse_args()
    
    if args.workers < 1:
        print("Error: workers must be at least 1")
        sys.exit(1)
    
    if args.workers > 16:
        print("Warning: Using more than 16 workers may cause resource issues.")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    run_parallel_sync(workers=args.workers, sistema=args.sistema)


if __name__ == "__main__":
    main()
