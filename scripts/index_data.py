"""Script to index data from Confluence and Jira into ChromaDB."""

import sys
import os
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from data_fetchers import ConfluenceFetcher, JiraFetcher
from storage import ChromaStore, AzureOpenAIEmbeddings, TextChunker
from retrieval import HybridRetriever
from mcp_server import MCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main indexing function."""
    parser = argparse.ArgumentParser(description="Index Confluence and Jira data")
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
    parser.add_argument(
        "--use-mcp",
        action="store_true",
        help="Use MCP server for multi-source integration"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Starting data indexing process")
    logger.info(f"Source: {args.source}, Refresh: {args.refresh}, Use MCP: {args.use_mcp}")
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
        
        chroma_store = ChromaStore(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.chroma_collection_name
        )
        
        chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        retriever = HybridRetriever(
            chroma_store=chroma_store,
            embeddings=embeddings,
            alpha=settings.hybrid_alpha
        )
        
        # Optionally use MCP server
        if args.use_mcp:
            logger.info("Using MCP Server for multi-source integration")
            mcp_server = MCPServer()
            
            # Register data sources
            if args.source in ["confluence", "both"]:
                confluence_fetcher = ConfluenceFetcher(
                    url=settings.confluence_url,
                    username=settings.confluence_username,
                    api_token=settings.confluence_api_token,
                    space_key=settings.confluence_space_key
                )
                mcp_server.register_data_source(
                    name="confluence",
                    source_type="confluence",
                    fetcher=confluence_fetcher
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
            
        else:
            # Direct fetch without MCP
            all_documents = []
            
            if args.source in ["confluence", "both"]:
                logger.info("Fetching Confluence pages...")
                confluence_fetcher = ConfluenceFetcher(
                    url=settings.confluence_url,
                    username=settings.confluence_username,
                    api_token=settings.confluence_api_token,
                    space_key=settings.confluence_space_key
                )
                confluence_pages = confluence_fetcher.fetch_all_pages()
                all_documents.extend(confluence_pages)
                logger.info(f"Fetched {len(confluence_pages)} Confluence pages")
            
            if args.source in ["jira", "both"]:
                logger.info("Fetching Jira issues...")
                jira_fetcher = JiraFetcher(
                    url=settings.jira_url,
                    username=settings.jira_username,
                    api_token=settings.jira_api_token,
                    project_key=settings.jira_project_key
                )
                jira_issues = jira_fetcher.fetch_all_issues()
                all_documents.extend(jira_issues)
                logger.info(f"Fetched {len(jira_issues)} Jira issues")
        
        if not all_documents:
            logger.warning("No documents fetched. Exiting.")
            return
        
        logger.info(f"Total documents fetched: {len(all_documents)}")
        
        # Refresh collection if requested
        if args.refresh:
            logger.info("Refreshing ChromaDB collection...")
            chroma_store.reset_collection()
        
        # Chunk documents
        logger.info("Chunking documents...")
        chunks = chunker.chunk_documents(all_documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        logger.info("Generating embeddings (this may take a while)...")
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings_list = embeddings.embed_documents(chunk_texts)
        logger.info(f"Generated {len(embeddings_list)} embeddings")
        
        # Add to ChromaDB
        logger.info("Adding documents to ChromaDB...")
        chroma_store.add_documents(chunks, embeddings_list)
        
        # Index for BM25
        logger.info("Indexing for BM25 (sparse retrieval)...")
        retriever.index_documents(chunks)
        
        # Display statistics
        logger.info("=" * 80)
        logger.info("Indexing completed successfully!")
        logger.info("=" * 80)
        stats = chroma_store.get_stats()
        logger.info(f"Collection: {stats['collection_name']}")
        logger.info(f"Total documents in ChromaDB: {stats['total_documents']}")
        logger.info(f"Persist directory: {stats['persist_directory']}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
