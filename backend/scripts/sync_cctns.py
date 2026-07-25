"""
PAC — Standalone CCTNS ETL Ingestion Daemon Script

Can be invoked directly via CLI or scheduled as a cron job:
  python scripts/sync_cctns.py [--seed]
"""

import asyncio
import argparse
import logging
from app.database import AsyncSessionLocal
from app.services.cctns_service import CCTNSEtlService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cctns_daemon")


async def main(seed: bool = False):
    logger.info("Starting CCTNS Data Ingestion ETL Daemon...")
    async with AsyncSessionLocal() as session:
        service = CCTNSEtlService(session)
        if seed:
            logger.info("Seeding mock staging FIR batch...")
            await service.seed_staging_records(batch_size=5)

        log = await service.run_etl_sync()
        logger.info(
            f"ETL Sync finished | Status={log.status.value} "
            f"Extracted={log.records_extracted} Imported={log.records_imported} "
            f"Duplicates={log.duplicates_skipped} Failed={log.failed_count}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAC CCTNS ETL Ingestion Daemon")
    parser.add_argument("--seed", action="store_true", help="Seed mock CCTNS staging records before running sync")
    args = parser.parse_args()

    asyncio.run(main(seed=args.seed))
