"""Hybrid retriever combining dense (vector) and sparse (BM25) search."""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from .bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retriever combining dense vector search and sparse BM25 search.
    
    Uses Reciprocal Rank Fusion (RRF) to combine results from both methods.
    """
    
    def __init__(
        self,
        chroma_store,
        embeddings,
        alpha: float = 0.5,
        rrf_k: int = 60
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            chroma_store: ChromaStore instance for dense retrieval
            embeddings: Embedding function for query encoding
            alpha: Weight for combining scores (0.0 = full BM25, 1.0 = full dense)
            rrf_k: RRF parameter (typically 60)
        """
        self.chroma_store = chroma_store
        self.embeddings = embeddings
        self.alpha = alpha
        self.rrf_k = rrf_k
        self.bm25_retriever = BM25Retriever()
        
        logger.info(f"Initialized HybridRetriever with alpha={alpha}, rrf_k={rrf_k}")
    
    def index_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 search.
        Note: Dense vectors are already in ChromaDB.
        
        Args:
            chunks: List of document chunks
        """
        self.bm25_retriever.index_documents(chunks)
        logger.info(f"Indexed {len(chunks)} documents for hybrid search")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        method: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters for ChromaDB
            method: Retrieval method ('hybrid', 'dense', 'sparse')
            
        Returns:
            List of retrieved documents with scores
        """
        if method == "dense":
            return self._dense_retrieve(query, top_k, filters)
        elif method == "sparse":
            return self._sparse_retrieve(query, top_k)
        else:
            return self._hybrid_retrieve(query, top_k, filters)
    
    def _dense_retrieve(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Dense retrieval using vector similarity."""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Query ChromaDB
        results = self.chroma_store.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=filters
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "dense_score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "method": "dense"
                })
        
        logger.info(f"Dense retrieval returned {len(formatted_results)} results")
        return formatted_results
    
    def _sparse_retrieve(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Sparse retrieval using BM25."""
        results = self.bm25_retriever.search(query, top_k=top_k)
        
        # Normalize scores
        if results:
            max_score = max(r.get("bm25_score", 0) for r in results)
            if max_score > 0:
                for r in results:
                    r["sparse_score"] = r.get("bm25_score", 0) / max_score
                    r["score"] = r["sparse_score"]
                    r["method"] = "sparse"
        
        logger.info(f"Sparse retrieval returned {len(results)} results")
        return results
    
    def _hybrid_retrieve(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval using Reciprocal Rank Fusion (RRF).
        
        RRF formula: RRF_score = sum(1 / (k + rank_i))
        where rank_i is the rank of the document in the i-th retrieval method.
        """
        # Get results from both methods (fetch more for better fusion)
        fetch_k = min(top_k * 3, 50)
        
        dense_results = self._dense_retrieve(query, fetch_k, filters)
        sparse_results = self._sparse_retrieve(query, fetch_k)
        
        # Create document ID to results mapping
        doc_map = {}
        
        # Add dense results with ranks
        for rank, result in enumerate(dense_results):
            doc_id = self._get_doc_identifier(result)
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "content": result["content"],
                    "metadata": result.get("metadata", {}),
                    "dense_score": result.get("dense_score", 0),
                    "sparse_score": 0,
                    "dense_rank": rank + 1,
                    "sparse_rank": None,
                    "rrf_score": 0
                }
            else:
                doc_map[doc_id]["dense_rank"] = rank + 1
                doc_map[doc_id]["dense_score"] = result.get("dense_score", 0)
        
        # Add sparse results with ranks
        for rank, result in enumerate(sparse_results):
            doc_id = self._get_doc_identifier(result)
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "content": result["content"],
                    "metadata": result.get("metadata", {}),
                    "dense_score": 0,
                    "sparse_score": result.get("sparse_score", 0),
                    "dense_rank": None,
                    "sparse_rank": rank + 1,
                    "rrf_score": 0
                }
            else:
                doc_map[doc_id]["sparse_rank"] = rank + 1
                doc_map[doc_id]["sparse_score"] = result.get("sparse_score", 0)
        
        # Calculate RRF scores
        for doc_id, doc_data in doc_map.items():
            rrf_score = 0
            
            if doc_data["dense_rank"] is not None:
                rrf_score += self.alpha * (1.0 / (self.rrf_k + doc_data["dense_rank"]))
            
            if doc_data["sparse_rank"] is not None:
                rrf_score += (1.0 - self.alpha) * (1.0 / (self.rrf_k + doc_data["sparse_rank"]))
            
            doc_data["rrf_score"] = rrf_score
            doc_data["score"] = rrf_score
            doc_data["method"] = "hybrid"
        
        # Sort by RRF score and return top k
        sorted_results = sorted(
            doc_map.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )[:top_k]
        
        logger.info(f"Hybrid retrieval returned {len(sorted_results)} results")
        logger.info(f"Top result scores - Dense: {sorted_results[0].get('dense_score', 0):.3f}, "
                   f"Sparse: {sorted_results[0].get('sparse_score', 0):.3f}, "
                   f"RRF: {sorted_results[0].get('rrf_score', 0):.3f}")
        
        return sorted_results
    
    def _get_doc_identifier(self, result: Dict[str, Any]) -> str:
        """Create a unique identifier for a document."""
        metadata = result.get("metadata", {})
        
        # Try to use doc_id and chunk_index
        doc_id = metadata.get("doc_id") or result.get("doc_id")
        chunk_index = metadata.get("chunk_index") or result.get("chunk_index", 0)
        
        if doc_id:
            return f"{doc_id}_{chunk_index}"
        
        # Fallback to content hash
        content = result.get("content", "")
        return str(hash(content[:100]))
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        chroma_stats = self.chroma_store.get_stats()
        bm25_stats = self.bm25_retriever.get_corpus_stats()
        
        return {
            "chroma": chroma_stats,
            "bm25": bm25_stats,
            "alpha": self.alpha,
            "rrf_k": self.rrf_k
        }
