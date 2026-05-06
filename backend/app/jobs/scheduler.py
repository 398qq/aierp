"""Background AI jobs — scheduled RFM scoring, churn prediction, alerts."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_rfm_batch():
    """Run RFM analysis on all active customers nightly."""
    from app.config import settings

    logger.info("Starting nightly RFM batch analysis")
    # TODO: iterate active customers, run CustomerAgent.rfm_analysis, store results
    logger.info("RFM batch analysis complete")


async def run_churn_prediction():
    """Run churn prediction on at-risk customers."""
    logger.info("Starting churn risk prediction")
    # TODO: identify at-risk customers, run churn_risk, store scores
    logger.info("Churn prediction complete")


def start_scheduler():
    scheduler.add_job(run_rfm_batch, "cron", hour=2, minute=0, id="rfm_batch")
    scheduler.add_job(run_churn_prediction, "cron", hour=3, minute=0, id="churn_prediction")
    scheduler.start()
    logger.info("AI job scheduler started")


def stop_scheduler():
    scheduler.shutdown()
