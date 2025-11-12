"""Script to index data from Confluence and Jira into ChromaDB using MCP."""

import sys
import os
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from data_fetchers import ConfluenceFetcher, JiraFetcher
from storage import ChromaStore, PostgresStore, AzureOpenAIEmbeddings, TextChunker
from retrieval import HybridRetriever
from mcp_server import MCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main indexing function using MCP."""
    parser = argparse.ArgumentParser(description="Index Confluence and Jira data using MCP")
    parser.add_argument(
        "--source",
        choices=["confluence", "jira", "both"],
        default="both",
        help="Data source to index"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Delete existing data before indexing"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Starting data indexing process via MCP")
    logger.info(f"Source: {args.source}, Refresh: {args.refresh}")
    if settings.confluence_space_key:
        logger.info(f"Confluence Space Key: {settings.confluence_space_key}")
    if settings.confluence_required_label:
        logger.info(f"Confluence Label: {settings.confluence_required_label}")
    if settings.loader.confluence.enable:
        logger.info(f"Confluence sources from YAML: {settings.loader.confluence.sources}")
    if settings.loader.jira.enable:
        logger.info(f"Jira sources from YAML: {settings.loader.jira.sources}")
    logger.info("=" * 80)
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        embeddings = AzureOpenAIEmbeddings(
            endpoint=settings.azure_embedding_endpoint,
            api_key=settings.azure_embedding_key,
            deployment_name=settings.azure_embedding_deployment,
            api_version=settings.azure_embedding_api_version,
            use_apim=settings.use_apim_for_embeddings
        )
        
        if settings.storage.provider == "postgres":
            if not settings.postgres_connection_string:
                raise ValueError("POSTGRES_CONNECTION_STRING is not set")
            vector_store = PostgresStore(
                connection_string=settings.postgres_connection_string,
                collection_name=settings.postgres_collection_name
            )
        else:
            vector_store = ChromaStore(
                persist_directory=settings.chroma_persist_directory,
                collection_name=settings.chroma_collection_name
            )
        
        chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        retriever = HybridRetriever(
            chroma_store=vector_store,
            embeddings=embeddings,
            alpha=settings.hybrid_alpha
        )
        
        # Use MCP server for multi-source integration
        logger.info("Using MCP Server for multi-source integration")
        mcp_server = MCPServer()
        
        # Register data sources
        if args.source in ["confluence", "both"]:
            confluence_fetcher = ConfluenceFetcher(
                url=settings.confluence_url,
                username=settings.confluence_username,
                api_token=settings.confluence_api_token,
                space_key=settings.confluence_space_key,
                required_label=settings.confluence_required_label
            )
            mcp_server.register_data_source(
                name="confluence",
                source_type="confluence",
                fetcher=confluence_fetcher,
                config={"sources": [s.dict() for s in settings.loader.confluence.sources] if settings.loader.confluence.enable else None}
            )
        
        if args.source in ["jira", "both"]:
            jira_fetcher = JiraFetcher(
                url=settings.jira_url,
                username=settings.jira_username,
                api_token=settings.jira_api_token,
                project_key=settings.jira_project_key
            )
            mcp_server.register_data_source(
                name="jira",
                source_type="jira",
                fetcher=jira_fetcher
            )
        
        # Health check
        logger.info("Performing MCP health check...")
        health = mcp_server.health_check()
        logger.info(f"MCP Health Status: {health['overall_status']}")
        
        # Fetch from all sources
        logger.info("Fetching data via MCP Server...")
        results = mcp_server.fetch_from_all_sources()
        all_documents = mcp_server.aggregate_results(results, merge_strategy="deduplicate")
        
        if not all_documents:
            logger.warning("No documents fetched. Exiting.")
            return
        
        logger.info(f"Total documents fetched: {len(all_documents)}")
        
        # Refresh collection if requested
        if args.refresh:
            logger.info(f"Refreshing {settings.storage.provider} collection...")
            vector_store.reset_collection()
        
        # Chunk documents
        logger.info("Chunking documents...")
        chunks = chunker.chunk_documents(all_documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        logger.info("Generating embeddings (this may take a while)...")
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings_list = embeddings.embed_documents(chunk_texts)
        logger.info(f"Generated {len(embeddings_list)} embeddings")
        
        # Add to vector store
        logger.info(f"Adding documents to {settings.storage.provider}...")
        vector_store.add_documents(chunks, embeddings_list)
        
        # Index for BM25
        logger.info("Indexing for BM25 (sparse retrieval)...")
        retriever.index_documents(chunks)
        
        # Display statistics
        logger.info("=" * 80)
        logger.info("Indexing completed successfully!")
        logger.info("=" * 80)
        stats = vector_store.get_stats()
        logger.info(f"Collection: {stats['collection_name']}")
        logger.info(f"Total documents in {settings.storage.provider}: {stats['total_documents']}")
        if 'persist_directory' in stats:
            logger.info(f"Persist directory: {stats['persist_directory']}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        sys.exit(1)

# end of main()

if __name__ == "__main__":
    main()
