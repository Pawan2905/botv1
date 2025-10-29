import os
import sys
from typing import List, Dict, Any

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetchers.confluence_fetcher import ConfluenceFetcher
from config import settings

def test_fetch_by_label(label: str, limit: int = 5) -> None:
    """
    Tests fetching Confluence pages by a specific label.

    Args:
        label: The label to search for.
        limit: The maximum number of pages to fetch.
    """
    print(f"Attempting to fetch up to {limit} pages with the label '{label}'...")

    try:
        # Initialize the Confluence fetcher from settings
        fetcher = ConfluenceFetcher(
            url=settings.confluence_url,
            username=settings.confluence_username,
            api_token=settings.confluence_api_token,
            space_key=settings.confluence_space_key
        )

        # Fetch documents by the specified label
        pages: List[Dict[str, Any]] = fetcher.get_documents_by_label(label, limit=limit)

        if not pages:
            print(f"No pages found with the label '{label}'.")
            return

        print(f"Successfully fetched {len(pages)} pages:")
        for i, page in enumerate(pages, 1):
            page_id = page.get('id', 'N/A')
            title = page.get('title', 'No Title')
            print(f"  {i}. ID: {page_id}, Title: {title}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure your .env file is correctly configured with Confluence credentials.")

if __name__ == "__main__":
    # Example: Fetch pages with the label 'technical'
    # You can change this to any label you want to test.
    test_label = "technical"
    test_fetch_by_label(test_label)
