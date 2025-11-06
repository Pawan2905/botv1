"""Hybrid retriever combining dense (vector) and sparse (BM25) search."""

import logging
from typing import List, Dict, Any, Optional
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_core.documents import Document
from .bm25_retriever import BM25Retriever
from storage.chroma_store import ChromaStore
from storage.embeddings import AzureOpenAIEmbeddings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retriever combining dense vector search and sparse BM25 search.
    """

    def __init__(
        self,
        chroma_store: ChromaStore,
        embeddings: AzureOpenAIEmbeddings,
        alpha: float = 0.5,
    ):
        """
        Initialize hybrid retriever.

        Args:
            chroma_store: ChromaStore instance for dense retrieval
            embeddings: Embedding function for query encoding
            alpha: Weight for combining scores (0.0 = full BM25, 1.0 = full dense)
        """
        self.chroma_store = chroma_store
        self.embeddings = embeddings
        self.alpha = alpha
        self.bm25_retriever = BM25Retriever()
        self.ensemble_retriever = None
        
        logger.info(f"Initialized HybridRetriever with alpha={alpha}")

    def index_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 search.
        Note: Dense vectors are already in ChromaDB.

        Args:
            chunks: List of document chunks
        """
        self.bm25_retriever.index_documents(chunks)
        
        # Initialize EnsembleRetriever
        chroma_retriever = self.chroma_store.as_retriever()
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, chroma_retriever],
            weights=[1.0 - self.alpha, self.alpha]
        )
        logger.info(f"Indexed {len(chunks)} documents for hybrid search")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters for ChromaDB

        Returns:
            List of retrieved documents with scores
        """
        if not self.ensemble_retriever:
            logger.warning("Retriever not initialized. Call index_documents first.")
            return []

        # The EnsembleRetriever in LangChain does not directly support metadata filtering.
        # This is a known limitation. A possible workaround is to filter the results after retrieval.
        if filters:
            logger.warning("Metadata filters are not directly supported by EnsembleRetriever and will be ignored.")

        results = self.ensemble_retriever.invoke(query)
        
        # Format results
        formatted_results = []
        for doc in results[:top_k]:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get("relevance_score", 0.0),
                "method": "hybrid"
            })
        
        logger.info(f"Hybrid retrieval returned {len(formatted_results)} results")
        return formatted_results

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        chroma_stats = self.chroma_store.get_stats()
        bm25_stats = self.bm25_retriever.get_corpus_stats()

        return {
            "chroma": chroma_stats,
            "bm25": bm25_stats,
            "alpha": self.alpha,
        }
