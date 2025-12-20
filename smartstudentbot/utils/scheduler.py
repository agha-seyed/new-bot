import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from smartstudentbot.utils.logger import logger
from smartstudentbot.config import settings

# Initialize Scheduler
scheduler = AsyncIOScheduler()

async def example_job():
    """
    Example background job (e.g., check for deadlines, clean temp files)
    """
    logger.info("Running background maintenance job...")
    # Logic to check deadlines or clean up old files would go here.

def start_scheduler():
    """
    Starts the scheduler loop.
    """
    logger.info("Starting Scheduler Worker...")

    # Add jobs here
    scheduler.add_job(example_job, 'interval', minutes=60)

    scheduler.start()

    try:
        # Keep the main thread alive
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()
