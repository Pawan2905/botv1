"""
Test script for the RAG module.
This script demonstrates how to use the RAG module to index a Confluence space
and perform a query.
"""

import logging
import os
import sys

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_module.rag import RAG
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_rag_module():
    """
    Tests the RAG module by indexing a Confluence space and performing a query.
    """
    logging.info("Starting RAG module test...")

    # 1. Initialize the RAG pipeline
    try:
        rag_pipeline = RAG(
            chroma_persist_dir=settings.chroma_persist_directory,
            chroma_collection_name="rag_module_test_collection"
        )
        logging.info("RAG pipeline initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize RAG pipeline: {e}")
        return

    # 2. Index a Confluence space
    try:
        logging.info(f"Indexing Confluence space: {settings.confluence_space_key}")
        rag_pipeline.index_confluence_space(
            confluence_url=settings.confluence_url,
            confluence_user=settings.confluence_username,
            confluence_token=settings.confluence_api_token,
            space_key=settings.confluence_space_key,
            label=settings.confluence_required_label
        )
        logging.info("Confluence space indexing complete.")
    except Exception as e:
        logging.error(f"Failed to index Confluence space: {e}")
        return

    # 3. Perform a query
    try:
        query = "What is the status of the project?"
        logging.info(f"Performing query: '{query}'")
        results = rag_pipeline.query(
            query_text=query,
            top_k=5
        )

        if results:
            logging.info("Query results:")
            for i, result in enumerate(results):
                logging.info(f"  Result {i+1}:")
                logging.info(f"    Score: {result['score']:.4f}")
                logging.info(f"    Content: {result['content'][:200]}...")
        else:
            logging.warning("Query returned no results.")

    except Exception as e:
        logging.error(f"Failed to perform query: {e}")
        return

    logging.info("RAG module test completed successfully.")


if __name__ == "__main__":
    test_rag_module()
