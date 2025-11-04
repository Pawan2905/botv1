"""
Core RAG (Retrieval-Augmented Generation) module.
This script orchestrates the RAG pipeline, including data fetching,
indexing, and retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from rag_module.confluence_processor import ConfluenceProcessor
from storage.chroma_store import ChromaStore
from storage.embeddings import get_embedding_function
from storage.chunker import ChunkingStrategy, UnstructuredChunker

logger = logging.getLogger(__name__)


class RAG:
    """Handles the end-to-end RAG pipeline."""

    def __init__(self, chroma_persist_dir: str, chroma_collection_name: str):
        """
        Initialize the RAG pipeline.

        Args:
            chroma_persist_dir: Directory to persist ChromaDB data.
            chroma_collection_name: Name of the ChromaDB collection.
        """
        self.embeddings = get_embedding_function()
        self.chroma_store = ChromaStore(
            persist_directory=chroma_persist_dir,
            collection_name=chroma_collection_name,
        )
        self.chunker = UnstructuredChunker(strategy=ChunkingStrategy.DEFAULT)
        logger.info("RAG pipeline initialized.")

    def index_confluence_space(
        self,
        confluence_url: str,
        confluence_user: str,
        confluence_token: str,
        space_key: str,
        label: Optional[str] = None,
    ) -> None:
        """
        Fetch, chunk, and index documents from a Confluence space.

        Args:
            confluence_url: The URL of the Confluence instance.
            confluence_user: The username for Confluence authentication.
            confluence_token: The API token for Confluence authentication.
            space_key: The key of the space to index.
            label: Optional label to filter pages within the space.
        """
        processor = ConfluenceProcessor(
            url=confluence_url,
            username=confluence_user,
            api_token=confluence_token,
        )

        logger.info(f"Fetching documents from Confluence space: {space_key}")
        documents = processor.fetch_pages(space_key=space_key, label=label)

        if not documents:
            logger.warning("No documents found to index.")
            return

        logger.info(f"Chunking {len(documents)} documents...")
        chunks = self.chunker.create_chunks(documents)

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        chunk_contents = [chunk["content"] for chunk in chunks]
        embeddings = self.embeddings.embed_documents(chunk_contents)

        logger.info("Adding documents to ChromaDB...")
        self.chroma_store.add_documents(chunks, embeddings)
        logger.info("Confluence space indexing complete.")

    def query(self, query_text: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the indexed documents.

        Args:
            query_text: The query to search for.
            top_k: The number of results to return.
            filters: Optional metadata filters for the search.

        Returns:
            A list of retrieved documents.
        """
        logger.info(f"Executing query: '{query_text}'")
        query_embedding = self.embeddings.embed_query(query_text)

        results = self.chroma_store.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=filters,
        )

        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1.0 - results["distances"][0][i],
                })
        
        logger.info(f"Query returned {len(formatted_results)} results.")
        return formatted_results
