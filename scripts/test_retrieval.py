"""Script to test the retrieval system."""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from storage import ChromaStore, AzureOpenAIEmbeddings
from retrieval import HybridRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main test function."""
    logger.info("=" * 80)
    logger.info("Testing Retrieval System")
    logger.info("=" * 80)
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        embeddings = AzureOpenAIEmbeddings(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment_name=settings.azure_openai_embedding_deployment,
            api_version=settings.azure_openai_api_version
        )
        
        chroma_store = ChromaStore(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.chroma_collection_name
        )
        
        retriever = HybridRetriever(
            chroma_store=chroma_store,
            embeddings=embeddings,
            alpha=settings.hybrid_alpha
        )
        
        # Display statistics
        stats = retriever.get_retrieval_stats()
        logger.info(f"ChromaDB documents: {stats['chroma']['total_documents']}")
        logger.info(f"BM25 indexed: {stats['bm25']['indexed']}")
        
        # Test queries
        test_queries = [
            "How do I configure authentication?",
            "What are the latest bugs in the project?",
            "Show me documentation about API endpoints"
        ]
        
        for query in test_queries:
            logger.info("=" * 80)
            logger.info(f"Query: {query}")
            logger.info("-" * 80)
            
            # Test hybrid retrieval
            logger.info("Testing HYBRID retrieval:")
            results = retriever.retrieve(query, top_k=3, method="hybrid")
            for i, result in enumerate(results, 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"  Title: {result.get('metadata', {}).get('doc_title', 'N/A')}")
                logger.info(f"  Type: {result.get('metadata', {}).get('doc_type', 'N/A')}")
                logger.info(f"  Score: {result.get('score', 0):.4f}")
                logger.info(f"  Content preview: {result.get('content', '')[:150]}...")
            
            # Test dense retrieval
            logger.info("\nTesting DENSE retrieval:")
            results = retriever.retrieve(query, top_k=3, method="dense")
            for i, result in enumerate(results, 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"  Title: {result.get('metadata', {}).get('doc_title', 'N/A')}")
                logger.info(f"  Score: {result.get('score', 0):.4f}")
            
            # Test sparse retrieval
            logger.info("\nTesting SPARSE (BM25) retrieval:")
            results = retriever.retrieve(query, top_k=3, method="sparse")
            for i, result in enumerate(results, 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"  Title: {result.get('metadata', {}).get('doc_title', 'N/A')}")
                logger.info(f"  Score: {result.get('score', 0):.4f}")
        
        logger.info("=" * 80)
        logger.info("Testing completed successfully!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Testing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
