"""
Reusable RAG (Retrieval-Augmented Generation) module.
This script provides a simplified interface to the main BotService,
orchestrating the RAG pipeline for indexing and querying.
"""

import logging
from typing import List, Dict, Any, Optional

# Add the root directory to the Python path to ensure imports work correctly
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.bot_service import BotService

logger = logging.getLogger(__name__)


class RAG:
    """
    A simplified, reusable interface for the RAG pipeline.
    This class orchestrates the existing project components for a streamlined experience.
    """

    def __init__(self):
        """
        Initialize the RAG module by creating an instance of the BotService.
        """
        try:
            self.bot_service = BotService()
            logger.info("RAG module initialized successfully, using existing BotService.")
        except Exception as e:
            logger.error(f"Failed to initialize RAG module: {e}")
            raise

    def index_confluence_space(self, refresh: bool = False) -> Dict[str, Any]:
        """
        Index all documents from the configured Confluence space.

        Args:
            refresh: If True, the existing index will be cleared before indexing.

        Returns:
            A dictionary with the status of the indexing process.
        """
        logger.info("Starting Confluence indexing through the RAG module...")
        try:
            return self.bot_service.index_data(source="confluence", refresh=refresh)
        except Exception as e:
            logger.error(f"Confluence indexing failed: {e}")
            raise

    def query(self, query_text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Perform a RAG query. This includes retrieval from the indexed documents
        and generation of an answer by the LLM.

        Args:
            query_text: The user's query.
            conversation_history: Optional. A list of previous conversation turns.

        Returns:
            A dictionary containing the response and the sources.
        """
        logger.info(f"Performing RAG query: '{query_text}'")
        try:
            # We use the _tool_rag_search method directly to bypass the agentic routing
            # and go straight to the RAG implementation.
            return self.bot_service._tool_rag_search(query=query_text, conversation_history=conversation_history)
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise
