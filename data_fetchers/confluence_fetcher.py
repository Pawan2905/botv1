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
    
    def fetch_all_pages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all pages from Confluence. If no space_key is provided, it fetches pages from all available spaces.
        
        Args:
            limit: Maximum number of pages to fetch per request
            
        Returns:
            List of page dictionaries with content and metadata
        """
        pages = []
        start = 0
        
        try:
            if self.required_label:
                # If a label is specified, always use CQL to fetch pages.
                # This will search across all spaces if space_key is not provided.
                cql = f'label = "{self.required_label}"'
                if self.space_key:
                    cql += f' AND space = "{self.space_key}"'
                
                while True:
                    search_results = self.confluence.cql(cql, start=start, limit=limit, expand="body.storage,version,metadata.labels")
                    response = [item['content'] for item in search_results.get('results', []) if item.get('content')]

                    if not response:
                        break
                    
                    for page in response:
                        processed_page = self._process_page(page)
                        if processed_page:
                            pages.append(processed_page)
                            logger.info(f"Fetched page: {processed_page['title']}")
                    
                    if len(response) < limit:
                        break
                    
                    start += limit

            elif self.space_key:
                # If only a space key is provided, fetch all pages from that space.
                while True:
                    response = self.confluence.get_all_pages_from_space(
                        space=self.space_key,
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
                            logger.info(f"Fetched page: {processed_page['title']}")
                    
                    if len(response) < limit:
                        break
                    
                    start += limit
            else:
                # If neither a label nor a space key is provided, fetch from all spaces.
                logger.info("No space key or label specified. Fetching pages from all available spaces.")
                all_spaces_response = self.confluence.get_all_spaces(start=0, limit=50, expand='description.plain,homepage')
                all_spaces = all_spaces_response.get('results', [])
                
                for space in all_spaces:
                    space_key = space['key']
                    logger.info(f"Fetching pages from space: {space_key}")
                    
                    space_start = 0
                    while True:
                        space_pages = self.confluence.get_all_pages_from_space(
                            space=space_key,
                            start=space_start,
                            limit=limit,
                            expand="body.storage,version,metadata.labels"
                        )
                        if not space_pages:
                            break
                        
                        for page in space_pages:
                            processed_page = self._process_page(page)
                            if processed_page:
                                pages.append(processed_page)
                                logger.info(f"Fetched page: {processed_page['title']}")
                        
                        if len(space_pages) < limit:
                            break
                        
                        space_start += limit

            logger.info(f"Successfully fetched {len(pages)} pages from Confluence")
            return pages
            
        except Exception as e:
            logger.error(f"Error fetching Confluence pages: {e}")
            raise
    
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
                expand="body.storage,version,metadata.labels"
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
            # Extract HTML content
            html_content = page.get("body", {}).get("storage", {}).get("value", "")
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, "html.parser")
            text_content = soup.get_text(separator="\n", strip=True)
            
            # Extract metadata
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
    
    def get_page_children(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get all child pages of a specific page.
        
        Args:
            page_id: Parent page ID
            
        Returns:
            List of child pages
        """
        try:
            children = self.confluence.get_page_child_by_type(
                page_id=page_id,
                type="page",
                expand="body.storage,version,metadata.labels"
            )
            
            pages = []
            for child in children:
                processed_page = self._process_page(child)
                if processed_page:
                    pages.append(processed_page)
            
            return pages
            
        except Exception as e:
            logger.error(f"Error fetching children of page {page_id}: {e}")
            return []

    def update_page(self, page_id: str, title: str, content: str, parent_id: Optional[str] = None, version_comment: str = "Updated via API") -> bool:
        """
        Update a Confluence page.
        
        Args:
            page_id: The ID of the page to update.
            title: The new title of the page.
            content: The new content of the page in storage format.
            parent_id: The ID of the parent page.
            version_comment: A comment for the new version.
            
        Returns:
            True if the page was updated successfully, False otherwise.
        """
        try:
            # Get the current version of the page
            page = self.confluence.get_page_by_id(page_id, expand="version")
            if not page:
                logger.error(f"Page with ID {page_id} not found.")
                return False
            
            current_version = page['version']['number']
            
            status = self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=content,
                parent_id=parent_id,
                version_comment=version_comment,
                minor_edit=True
            )
            
            logger.info(f"Successfully updated page {page_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating page {page_id}: {e}")
            return False

    def get_documents_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents by topic or keyword.
        
        Args:
            keyword: The topic or keyword to search for.
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        cql = f'title ~ "{keyword}" OR text ~ "{keyword}"'
        if self.space_key:
            cql += f' AND space = "{self.space_key}"'
        return self.search_pages(cql, limit=limit)

    def get_documents_by_label(self, label: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents by a specific label.
        
        Args:
            label: The label to search for.
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        cql = f'label = "{label}"'
        if self.space_key:
            cql += f' AND space = "{self.space_key}"'
        return self.search_pages(cql, limit=limit)

    def get_how_to_guides(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get step-by-step guides or SOPs.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        return self.get_documents_by_label("how-to", limit=limit)

    def get_policy_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve company policies or processes.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        return self.get_documents_by_label("policy", limit=limit)

    def get_architecture_doc(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch architecture or design documentation.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        return self.get_documents_by_label("architecture", limit=limit)

    def get_team_page(self, team_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Access team pages or meeting notes.
        
        Args:
            team_name: The name of the team to search for.
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        cql = f'(label = "team" OR label = "meeting-notes") AND title ~ "{team_name}"'
        if self.space_key:
            cql += f' AND space = "{self.space_key}"'
        return self.search_pages(cql, limit=limit)

    def get_onboarding_docs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get onboarding or training pages.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            List of matching pages.
        """
        return self.get_documents_by_label("onboarding", limit=limit)

    def get_page_history(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve version/edit history of a page.
        
        Args:
            page_id: The ID of the page.
            
        Returns:
            List of page versions.
        """
        try:
            history = self.confluence.get_page_history(page_id)
            return history
        except Exception as e:
            logger.error(f"Error fetching history for page {page_id}: {e}")
            return []
