import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config_loading():
    """Tests if the config.yaml loader settings are being loaded correctly."""
    logger.info("=" * 50)
    logger.info("Testing config.yaml loading...")
    logger.info("=" * 50)

    confluence_enabled = settings.loader.confluence.enable
    confluence_sources = settings.loader.confluence.sources
    
    jira_enabled = settings.loader.jira.enable
    jira_sources = settings.loader.jira.sources

    logger.info(f"Confluence Loader Enabled: {confluence_enabled}")
    if confluence_enabled and confluence_sources:
        logger.info("Confluence Sources Found:")
        for i, source in enumerate(confluence_sources):
            logger.info(f"  Source {i+1}: Space='{source.space}', Labels={source.optional_labels}")
    else:
        logger.info("No Confluence sources found or loader is disabled.")

    logger.info("-" * 50)

    logger.info(f"Jira Loader Enabled: {jira_enabled}")
    if jira_enabled and jira_sources:
        logger.info("Jira Sources Found:")
        for i, source in enumerate(jira_sources):
            logger.info(f"  Source {i+1}: Labels={source.labels}")
    else:
        logger.info("No Jira sources found or loader is disabled.")
    
    logger.info("=" * 50)
    logger.info("Test finished. If you see the sources listed above, config.yaml is working.")
    logger.info("=" * 50)

if __name__ == "__main__":
    test_config_loading()
