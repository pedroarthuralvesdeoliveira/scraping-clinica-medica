import asyncio
from datetime import timedelta

from prefect import aserve

from app.flows.daily_sync_flow import daily_sync_flow
from app.flows.next_appointments_flow import next_appointments_sync_flow


async def main():
    # Sequential Daily Sync at 8:00 AM (Patient -> History)
    daily_dep = await daily_sync_flow.to_deployment(  # type: ignore
        name="Daily Incremental Sync",
        cron="0 8 * * *",
        description="Sync patients and then history daily at 8:00 AM",
    )

    # Frequent Next Appointments Sync every hour
    frequent_dep = await next_appointments_sync_flow.to_deployment(  # type: ignore
        name="Frequent Next Appointments Sync",
        interval=timedelta(hours=1),
        description="Sync next appointments every hour",
    )

    await aserve(daily_dep, frequent_dep)


if __name__ == "__main__":
    asyncio.run(main())
