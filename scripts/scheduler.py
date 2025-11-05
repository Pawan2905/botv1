import logging
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from data_fetchers.confluence_fetcher import ConfluenceFetcher
from config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_confluence_data():
    """Fetches data from Confluence and logs the result."""
    logger.info("Scheduler starting Confluence data fetch...")
    try:
        config = load_config()
        
        confluence_config = next((p for p in config.get('data_sources', []) if p['type'] == 'confluence'), None)
        if not confluence_config:
            logger.error("Confluence configuration not found in config.yaml.")
            return

        fetcher = ConfluenceFetcher(
            url=confluence_config['url'],
            username=os.getenv("CONFLUENCE_USERNAME"),
            api_token=os.getenv("CONFLUENCE_API_TOKEN")
        )
        
        pages = fetcher.fetch_all_pages(sources=confluence_config.get('sources'))
        logger.info(f"Successfully fetched {len(pages)} pages from Confluence.")
        
    except Exception as e:
        logger.error(f"Error during scheduled Confluence fetch: {e}", exc_info=True)

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # Schedule to run every day at 8:00 AM
    scheduler.add_job(fetch_confluence_data, 'cron', hour=8)
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
