"""ChromaDB storage with indexing and persistence."""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import uuid

logger = logging.getLogger(__name__)


class ChromaStore:
    """Manages ChromaDB collection for document storage and retrieval."""
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_function: Optional[Any] = None
    ):
        """
        Initialize ChromaDB store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_function: Optional custom embedding function
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Initialized ChromaDB store at {persist_directory}")
        logger.info(f"Collection '{collection_name}' has {self.collection.count()} documents")
    
    def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add documents to the collection.
        
        Args:
            chunks: List of document chunks with metadata
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings provided")
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            # Generate unique ID for each chunk
            chunk_id = f"{chunk.get('doc_id', 'unknown')}_{chunk.get('chunk_index', 0)}_{uuid.uuid4().hex[:8]}"
            ids.append(chunk_id)
            
            # Extract content
            documents.append(chunk.get("content", ""))
            
            # Prepare metadata (ChromaDB only supports string, int, float, bool)
            metadata = {
                "doc_id": str(chunk.get("doc_id", "")),
                "doc_title": str(chunk.get("doc_title", "")),
                "doc_url": str(chunk.get("doc_url", "")),
                "doc_type": str(chunk.get("doc_type", "")),
                "source": str(chunk.get("source", "")),
                "chunk_index": int(chunk.get("chunk_index", 0)),
            }
            
            # Add optional fields
            if "space" in chunk:
                metadata["space"] = str(chunk["space"])
            if "project" in chunk:
                metadata["project"] = str(chunk["project"])
            if "status" in chunk:
                metadata["status"] = str(chunk["status"])
            if "labels" in chunk and chunk["labels"]:
                metadata["labels"] = ",".join([str(l) for l in chunk["labels"]])
            
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas
                )
                logger.info(f"Added batch {i//batch_size + 1} ({len(batch_ids)} documents)")
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {e}")
        
        logger.info(f"Successfully added {len(chunks)} documents to collection")
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
            
        Returns:
            Query results with documents and metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    def query_by_text(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query using text search (full-text search on documents).
        
        Args:
            query_text: Query text
            n_results: Number of results
            where: Metadata filter
            
        Returns:
            List of matching documents
        """
        try:
            # Use ChromaDB's text search
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error in text query: {e}")
            return []
    
    def delete_by_source(self, source: str) -> None:
        """
        Delete all documents from a specific source.
        
        Args:
            source: Source identifier (e.g., 'confluence', 'jira')
        """
        try:
            self.collection.delete(where={"source": source})
            logger.info(f"Deleted all documents from source: {source}")
        except Exception as e:
            logger.error(f"Error deleting documents from {source}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def reset_collection(self) -> None:
        """Reset the collection (delete all documents)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Reset collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
