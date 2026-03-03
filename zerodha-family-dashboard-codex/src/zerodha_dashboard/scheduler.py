from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from .sync_service import PortfolioSyncService


def start_scheduler(sync_service: PortfolioSyncService, hours: int) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_service.sync_all_accounts, "interval", hours=hours, id="portfolio_sync", replace_existing=True)
    scheduler.start()
    return scheduler
