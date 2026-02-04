import asyncio
from app.flows.daily_sync_flow import daily_sync_flow
from app.flows.next_appointments_flow import next_appointments_sync_flow
from datetime import timedelta
from prefect import aserve

async def main():
    # Sequential Daily Sync at 8:00 AM (Patient -> History)
    daily_dep = await daily_sync_flow.to_deployment(  # type: ignore
        name="Daily Sequential Sync",
        cron="0 8 * * *",
        description="Sync patients and then history daily at 8:00 AM",
    )
    
    # Frequent Next Appointments Sync every 15 minutes
    frequent_dep = await next_appointments_sync_flow.to_deployment(  # type: ignore
        name="Frequent Next Appointments Sync",
        interval=timedelta(minutes=15),
        description="Sync next appointments every 15 minutes",
    )

    await aserve(daily_dep, frequent_dep)

if __name__ == "__main__":
    asyncio.run(main())