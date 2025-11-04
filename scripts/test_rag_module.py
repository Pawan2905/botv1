"""
Test script for the refactored RAG module.
This script demonstrates how to use the reusable RAG module to index a
Confluence space and perform a query, leveraging the existing BotService.
"""

import logging
import os
import sys

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_module.rag import RAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_rag_module():
    """
    Tests the refactored RAG module by indexing a Confluence space and
    performing a query to get a generated answer.
    """
    logging.info("Starting refactored RAG module test...")

    # 1. Initialize the RAG module
    try:
        rag_pipeline = RAG()
        logging.info("RAG module initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize RAG module: {e}")
        return

    # 2. Index the configured Confluence space
    try:
        logging.info("Indexing Confluence space...")
        # Set refresh=True to ensure we are testing with a clean index
        index_status = rag_pipeline.index_confluence_space(refresh=True)
        logging.info(f"Confluence space indexing completed: {index_status}")
    except Exception as e:
        logging.error(f"Failed to index Confluence space: {e}")
        return

    # 3. Perform a query to get a generated answer
    try:
        query = "What is the status of the project?"
        logging.info(f"Performing query: '{query}'")
        result = rag_pipeline.query(query_text=query)

        if result and result.get("response"):
            logging.info("Query successful. Generated response:")
            logging.info(f"  Response: {result['response']}")
            if result.get("sources"):
                logging.info("  Sources:")
                for i, source in enumerate(result["sources"]):
                    logging.info(f"    Source {i+1}: {source.get('title', 'Unknown')} - {source.get('url', 'No URL')}")
        else:
            logging.warning("Query did not return a response.")

    except Exception as e:
        logging.error(f"Failed to perform query: {e}")
        return

    logging.info("Refactored RAG module test completed successfully.")


if __name__ == "__main__":
    test_rag_module()
