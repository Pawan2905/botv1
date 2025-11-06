"""ChromaDB storage with indexing and persistence."""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
import uuid

logger = logging.getLogger(__name__)


class ChromaStore(VectorStore):
    """Manages ChromaDB collection for document storage and retrieval."""
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_function: Embeddings
    ):
        """
        Initialize ChromaDB store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_function: LangChain embedding function
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        
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
    
    def add_documents(self, documents: List[Document], **kwargs: Any) -> List[str]:
        """
        Add documents to the collection.
        
        Args:
            documents: List of LangChain Documents
        """
        if not documents:
            logger.warning("No documents provided")
            return []
        
        # Prepare data for ChromaDB
        ids = []
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        for doc in documents:
            # Generate unique ID for each chunk
            chunk_id = f"{doc.metadata.get('doc_id', 'unknown')}_{doc.metadata.get('chunk_index', 0)}_{uuid.uuid4().hex[:8]}"
            ids.append(chunk_id)
        
        embeddings = self.embedding_function.embed_documents(texts)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = texts[i:i + batch_size]
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
        
        logger.info(f"Successfully added {len(documents)} documents to collection")
        return ids

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """
        Query the collection using vector similarity.
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of matching documents
        """
        query_embedding = self.embedding_function.embed_query(query)
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    formatted_results.append(
                        Document(
                            page_content=results["documents"][0][i],
                            metadata=results["metadatas"][0][i]
                        )
                    )
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            return []
    
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

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding: Embeddings,
        **kwargs: Any,
    ) -> "ChromaStore":
        """Create a ChromaStore from a list of documents."""
        # This is a simplified implementation. A more robust version would handle
        # the persist_directory and collection_name more gracefully.
        store = cls(
            persist_directory=kwargs.get("persist_directory", "./chroma_db"),
            collection_name=kwargs.get("collection_name", "langchain"),
            embedding_function=embedding,
        )
        store.add_documents(documents)
        return store
