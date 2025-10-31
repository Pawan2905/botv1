"""Confluence data fetcher with authentication and pagination support."""

import logging
from typing import List, Dict, Any, Optional
from atlassian import Confluence
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfluenceFetcher:
    """Fetches documents from Confluence."""
    
    def __init__(
        self,
        url: str,
        username: str,
        api_token: str,
        space_key: Optional[str] = None,
        required_label: Optional[str] = None
    ):
        """
        Initialize Confluence fetcher.
        
        Args:
            url: Confluence instance URL
            username: Confluence username/email
            api_token: Confluence API token
            space_key: Optional space key to filter pages
            required_label: Optional label to filter pages
        """
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token,
            cloud=True
        )
        self.space_key = space_key
        self.required_label = required_label
        logger.info(f"Initialized Confluence fetcher for {url}")

    def get_all_spaces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch all spaces from Confluence.
        
        Args:
            limit: Maximum number of spaces to fetch per request.
        
        Returns:
            List of space dictionaries.
        """
        all_spaces = []
        start = 0
        while True:
            try:
                spaces_batch = self.confluence.get_all_spaces(
                    start=start, 
                    limit=limit, 
                    expand='description.plain,homepage'
                )
                results = spaces_batch.get('results', [])
                if not results:
                    break
                all_spaces.extend(results)
                start += len(results)
                if len(results) < limit:
                    break
            except Exception as e:
                logger.error(f"Error fetching spaces from Confluence: {e}")
                break
        logger.info(f"Found {len(all_spaces)} spaces.")
        return all_spaces

    def fetch_pages_from_space(self, space_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all pages from a specific Confluence space.
        
        Args:
            space_key: The key of the space to fetch pages from.
            limit: Maximum number of pages to fetch per request.
            
        Returns:
            List of page dictionaries with content and metadata.
        """
        pages = []
        start = 0
        logger.info(f"Fetching pages from space: {space_key}")
        while True:
            try:
                response = self.confluence.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand="body.storage,version,metadata.labels"
                )
                if not response:
                    break
                
                for page in response:
                    processed_page = self._process_page(page)
                    if processed_page:
                        pages.append(processed_page)
                
                if len(response) < limit:
                    break
                start += limit
            except Exception as e:
                logger.error(f"Error fetching pages from space {space_key}: {e}")
                break
        logger.info(f"Fetched {len(pages)} pages from space {space_key}.")
        return pages

    def fetch_all_pages_from_all_spaces(self, page_limit_per_space: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all pages from all available spaces in Confluence.
        
        Args:
            page_limit_per_space: Maximum number of pages to fetch per space in each request.
        
        Returns:
            A list of all pages from all spaces.
        """
        all_pages = []
        spaces = self.get_all_spaces()
        for space in spaces:
            space_key = space['key']
            pages_from_space = self.fetch_pages_from_space(space_key, limit=page_limit_per_space)
            all_pages.extend(pages_from_space)
        logger.info(f"Successfully fetched a total of {len(all_pages)} pages from {len(spaces)} spaces.")
        return all_pages

    def fetch_all_pages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch pages from Confluence based on the configuration provided during initialization.
        - If a `required_label` is set, it fetches pages with that label (optionally filtered by `space_key`).
        - If only a `space_key` is set, it fetches all pages from that space.
        - If neither is set, it fetches all pages from all available spaces.
        
        Args:
            limit: Maximum number of pages to fetch per request.
            
        Returns:
            List of page dictionaries with content and metadata.
        """
        if self.required_label:
            logger.info(f"Fetching pages with label '{self.required_label}'...")
            return self.get_documents_by_label(self.required_label, self.space_key, limit=limit)

        if self.space_key:
            logger.info(f"Fetching all pages from space '{self.space_key}'...")
            return self.fetch_pages_from_space(self.space_key, limit=limit)

        logger.info("Fetching all pages from all spaces...")
        return self.fetch_all_pages_from_all_spaces(page_limit_per_space=limit)

    def fetch_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific page by ID.
        
        Args:
            page_id: Confluence page ID
            
        Returns:
            Page dictionary with content and metadata
        """
        try:
            page = self.confluence.get_page_by_id(
                page_id=page_id,
                expand="body.storage,version,metadata.labels"
            )
            return self._process_page(page)
        except Exception as e:
            logger.error(f"Error fetching page {page_id}: {e}")
            return None
    
    def search_pages(self, cql: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search pages using CQL (Confluence Query Language).
        
        Args:
            cql: CQL query string
            limit: Maximum number of results
            
        Returns:
            List of matching pages
        """
        try:
            results = self.confluence.cql(
                cql=cql, 
                limit=limit,
                expand="content.body.storage,content.version,content.metadata.labels"
            )
            pages = []
            
            for result in results.get("results", []):
                page_data = result.get("content")
                if page_data:
                    processed_page = self._process_page(page_data)
                    if processed_page:
                        pages.append(processed_page)

            logger.info(f"Found {len(pages)} pages matching CQL query")
            return pages
            
        except Exception as e:
            logger.error(f"Error searching Confluence: {e}")
            return []
    
    def _process_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process and clean a Confluence page.
        
        Args:
            page: Raw page data from Confluence API
             
        Returns:
            Processed page dictionary
        """
        try:
            html_content = page.get("body", {}).get("storage", {}).get("value", "")
            soup = BeautifulSoup(html_content, "html.parser")
            text_content = soup.get_text(separator="\n", strip=True)
            version = page.get("version", {})
            labels = [label.get("name") for label in page.get("metadata", {}).get("labels", {}).get("results", [])]
            
            return {
                "id": page.get("id"),
                "title": page.get("title"),
                "content": text_content,
                "html_content": html_content,
                "url": self.confluence.url + page.get("_links", {}).get("webui", ""),
                "space": page.get("space", {}).get("key"),
                "version": version.get("number"),
                "last_updated": version.get("when"),
                "last_updated_by": version.get("by", {}).get("displayName"),
                "labels": labels,
                "type": "confluence",
                "source": "confluence"
            }
        except Exception as e:
            logger.error(f"Error processing page: {e}")
            return None
    
    def get_documents_by_label(self, label: str, space_key: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents by a specific label.
        
        Args:
            label: The label to search for.
            space_key: Optional space key to filter pages.
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        cql = f'label = "{label}"'
        
        # Use the provided space_key, but fall back to the instance's space_key if not provided
        effective_space_key = space_key if space_key is not None else self.space_key
        
        if effective_space_key:
            cql += f' AND space = "{effective_space_key}"'
        
        logger.info(f"Executing CQL query: {cql}")
        return self.search_pages(cql, limit=limit)

    def get_documents_by_user(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents created or contributed to by a specific user.
        
        Args:
            username: The username or account ID to search for.
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        # Note: Confluence CQL user fields (`creator`, `contributor`) often require the user's account ID.
        cql = f'creator = "{username}" OR contributor = "{username}"'
        if self.space_key:
            cql += f' AND space = "{self.space_key}"'
        
        logger.info(f"Executing CQL query for user: {cql}")
        return self.search_pages(cql, limit=limit)
