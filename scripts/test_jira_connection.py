"""Script to test Jira connection and data fetching."""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from data_fetchers import JiraFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_jira_connection():
    """Test Jira connection and basic functionality."""
    logger.info("=" * 80)
    logger.info("Testing Jira Connection and Data Fetching")
    logger.info("=" * 80)
    
    try:
        # Initialize Jira fetcher
        logger.info("Initializing Jira fetcher...")
        logger.info(f"Jira URL: {settings.jira_url}")
        logger.info(f"Username: {settings.jira_username}")
        logger.info(f"Project Key: {settings.jira_project_key}")
        
        jira_fetcher = JiraFetcher(
            url=settings.jira_url,
            username=settings.jira_username,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key
        )
        
        # Test 1: Fetch a few issues
        logger.info("\n" + "-" * 60)
        logger.info("Test 1: Fetching recent issues...")
        logger.info("-" * 60)
        
        issues = jira_fetcher.fetch_all_issues(max_results=5)
        logger.info(f"✓ Successfully fetched {len(issues)} issues")
        
        if issues:
            for i, issue in enumerate(issues[:3], 1):
                logger.info(f"\nIssue {i}:")
                logger.info(f"  Key: {issue['key']}")
                logger.info(f"  Title: {issue['title']}")
                logger.info(f"  Status: {issue['status']}")
                logger.info(f"  Type: {issue['issue_type']}")
                logger.info(f"  Priority: {issue.get('priority', 'None')}")
                logger.info(f"  URL: {issue['url']}")
        
        # Test 2: Search issues
        logger.info("\n" + "-" * 60)
        logger.info("Test 2: Searching issues...")
        logger.info("-" * 60)
        
        search_results = jira_fetcher.search_issues("bug", max_results=3)
        logger.info(f"✓ Found {len(search_results)} issues matching 'bug'")
        
        if search_results:
            for issue in search_results:
                logger.info(f"  - {issue['key']}: {issue['title'][:50]}...")
        
        # Test 3: Get specific issue (if we have any)
        if issues:
            logger.info("\n" + "-" * 60)
            logger.info("Test 3: Fetching specific issue...")
            logger.info("-" * 60)
            
            first_issue_key = issues[0]['key']
            specific_issue = jira_fetcher.fetch_issue_by_key(first_issue_key)
            
            if specific_issue:
                logger.info(f"✓ Successfully fetched issue {first_issue_key}")
                logger.info(f"  Title: {specific_issue['title']}")
                logger.info(f"  Description: {specific_issue['description'][:100]}...")
            else:
                logger.warning(f"✗ Failed to fetch specific issue {first_issue_key}")
        
        # Test 4: Test JQL query
        logger.info("\n" + "-" * 60)
        logger.info("Test 4: Testing custom JQL query...")
        logger.info("-" * 60)
        
        custom_jql = "ORDER BY created DESC"
        custom_results = jira_fetcher.fetch_all_issues(jql=custom_jql, max_results=3)
        logger.info(f"✓ Custom JQL returned {len(custom_results)} issues")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ All Jira tests completed successfully!")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Jira connection test failed: {e}", exc_info=True)
        logger.error("\nTroubleshooting tips:")
        logger.error("1. Check your Jira URL, username, and API token")
        logger.error("2. Ensure your API token has proper permissions")
        logger.error("3. Verify the project key exists (if specified)")
        logger.error("4. Check if your Jira instance is accessible")
        return False


def main():
    """Main function."""
    success = test_jira_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
