"""BM25 sparse retriever for keyword-based search."""

import logging
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25-based sparse retriever for keyword matching."""
    
    def __init__(self):
        """Initialize BM25 retriever."""
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []
        logger.info("Initialized BM25Retriever")
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 search.
        
        Args:
            documents: List of document dictionaries with 'content' field
        """
        self.documents = documents
        
        # Tokenize documents
        self.tokenized_corpus = [
            self._tokenize(doc.get("content", ""))
            for doc in documents
        ]
        
        # Create BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"Indexed {len(documents)} documents for BM25 search")
        else:
            logger.warning("No documents to index")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents using BM25.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of top matching documents with scores
        """
        if not self.bm25:
            logger.warning("BM25 index not initialized")
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Format results
        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                result = self.documents[idx].copy()
                result["bm25_score"] = float(scores[idx])
                results.append(result)
        
        logger.info(f"BM25 search returned {len(results)} results for query: {query[:50]}...")
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Simple whitespace and punctuation-based tokenization
        # Convert to lowercase and split
        tokens = text.lower().split()
        
        # Remove punctuation
        tokens = [
            ''.join(c for c in token if c.isalnum() or c in ['-', '_'])
            for token in tokens
        ]
        
        # Filter empty tokens
        tokens = [t for t in tokens if t]
        
        return tokens
    
    def get_corpus_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed corpus."""
        if not self.bm25:
            return {"indexed": False}
        
        return {
            "indexed": True,
            "num_documents": len(self.documents),
            "avg_doc_length": np.mean([len(doc) for doc in self.tokenized_corpus]) if self.tokenized_corpus else 0
        }
