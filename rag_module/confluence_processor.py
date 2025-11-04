"""
Confluence data processor for the RAG module.
This script handles fetching and processing of data from Confluence.
"""

import logging
from typing import List, Dict, Any, Optional
from atlassian import Confluence
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ConfluenceProcessor:
    """Fetches and processes documents from Confluence."""

    def __init__(self, url: str, username: str, api_token: str):
        """
        Initialize Confluence processor.

        Args:
            url: Confluence instance URL.
            username: Confluence username/email.
            api_token: Confluence API token.
        """
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token,
            cloud=True
        )
        logger.info(f"Initialized Confluence processor for {url}")

    def _process_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process and clean a Confluence page.

        Args:
            page: Raw page data from Confluence API.

        Returns:
            Processed page dictionary with clean text content.
        """
        try:
            html_content = page.get("body", {}).get("storage", {}).get("value", "")
            soup = BeautifulSoup(html_content, "html.parser")
            text_content = soup.get_text(separator="\\n", strip=True)
            version = page.get("version", {})
            labels = [label.get("name") for label in page.get("metadata", {}).get("labels", {}).get("results", [])]

            return {
                "id": page.get("id"),
                "title": page.get("title"),
                "content": text_content,
                "url": self.confluence.url + page.get("_links", {}).get("webui", ""),
                "space": page.get("space", {}).get("key"),
                "version": version.get("number"),
                "last_updated": version.get("when"),
                "labels": labels,
            }
        except Exception as e:
            logger.error(f"Error processing page: {e}")
            return None

    def fetch_pages(self, space_key: str, label: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch pages from a specific Confluence space, with an optional label filter.

        Args:
            space_key: The key of the space to fetch pages from.
            label: Optional label to filter pages.
            limit: Maximum number of pages to fetch per request.

        Returns:
            List of processed page dictionaries.
        """
        pages = []
        start = 0
        logger.info(f"Fetching pages from space: {space_key}")

        while True:
            try:
                if label:
                    cql = f'space = "{space_key}" AND label = "{label}"'
                    response = self.confluence.cql(cql, start=start, limit=limit, expand="body.storage,version,metadata.labels")
                    results = response.get('results', [])
                else:
                    results = self.confluence.get_all_pages_from_space(
                        space=space_key,
                        start=start,
                        limit=limit,
                        expand="body.storage,version,metadata.labels"
                    )

                if not results:
                    break

                for page_data in results:
                    # The structure of the response from CQL is different
                    page = page_data.get('content', page_data)
                    processed_page = self._process_page(page)
                    if processed_page:
                        pages.append(processed_page)

                if len(results) < limit:
                    break
                start += len(results)

            except Exception as e:
                logger.error(f"Error fetching pages from space {space_key}: {e}")
                break

        logger.info(f"Fetched {len(pages)} pages from space {space_key}.")
        return pages
