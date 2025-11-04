"""
Query handler for the RAG module.
This script is responsible for processing and validating input queries.
"""

import logging

logger = logging.getLogger(__name__)


class QueryHandler:
    """Handles input queries for the RAG pipeline."""

    def __init__(self, query: str):
        """
        Initialize the QueryHandler.

        Args:
            query: The input query string.
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string.")

        self.original_query = query
        self.processed_query = self._process_query(query)
        logger.info(f"Initialized QueryHandler with query: '{query}'")

    def _process_query(self, query: str) -> str:
        """
        Process the input query.
        For now, this just strips leading/trailing whitespace.
        """
        return query.strip()

    def get_processed_query(self) -> str:
        """
        Returns the processed query.
        """
        return self.processed_query
