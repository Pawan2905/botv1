"""PostgreSQL storage with indexing and persistence."""

import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import uuid

logger = logging.getLogger(__name__)

class PostgresStore:
    """Manages PostgreSQL table for document storage and retrieval."""

    def __init__(
        self,
        connection_string: str,
        collection_name: str,
        embedding_function: Optional[Any] = None
    ):
        """
        Initialize PostgreSQL store.
        
        Args:
            connection_string: PostgreSQL connection string
            collection_name: Name of the table
            embedding_function: Optional custom embedding function (not used in this implementation)
        """
        self.connection_string = connection_string
        self.collection_name = collection_name
        self.conn = None
        self._connect()
        self._create_table()

    def _connect(self):
        """Establish connection to the database."""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            register_vector(self.conn)
            logger.info("Connected to PostgreSQL database")
        except psycopg2.OperationalError as e:
            logger.error(f"Could not connect to PostgreSQL database: {e}")
            raise

    def _create_table(self):
        """Create the table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id UUID PRIMARY KEY,
                doc_id VARCHAR(255),
                doc_title TEXT,
                doc_url TEXT,
                doc_type VARCHAR(50),
                source VARCHAR(50),
                chunk_index INTEGER,
                content TEXT,
                embedding VECTOR(1536),
                metadata JSONB
            );
            """)
            self.conn.commit()
            logger.info(f"Table '{self.collection_name}' is ready")

    def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add documents to the table.
        
        Args:
            chunks: List of document chunks with metadata
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings provided")
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        records = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = uuid.uuid4()
            metadata = {
                "space": chunk.get("space"),
                "project": chunk.get("project"),
                "status": chunk.get("status"),
                "labels": chunk.get("labels"),
            }
            records.append((
                chunk_id,
                chunk.get("doc_id", ""),
                chunk.get("doc_title", ""),
                chunk.get("doc_url", ""),
                chunk.get("doc_type", ""),
                chunk.get("source", ""),
                chunk.get("chunk_index", 0),
                chunk.get("content", ""),
                embedding,
                metadata
            ))
        
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO {self.collection_name} (
                    id, doc_id, doc_title, doc_url, doc_type, source, 
                    chunk_index, content, embedding, metadata
                ) VALUES %s
                """,
                records
            )
            self.conn.commit()
        logger.info(f"Successfully added {len(chunks)} documents to table")

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the table using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
            
        Returns:
            Query results with documents and metadata
        """
        # Basic implementation, can be extended with filters
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT content, metadata, 1 - (embedding <=> %s) AS distance FROM {self.collection_name} ORDER BY embedding <=> %s LIMIT %s",
                (query_embedding, query_embedding, n_results)
            )
            results = cur.fetchall()
        
        formatted_results = {
            "documents": [[row[0] for row in results]],
            "metadatas": [[row[1] for row in results]],
            "distances": [[row[2] for row in results]]
        }
        return formatted_results

    def delete_by_source(self, source: str) -> None:
        """
        Delete all documents from a specific source.
        
        Args:
            source: Source identifier (e.g., 'confluence', 'jira')
        """
        with self.conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.collection_name} WHERE source = %s", (source,))
            self.conn.commit()
        logger.info(f"Deleted all documents from source: {source}")

    def get_stats(self) -> Dict[str, Any]:
        """Get table statistics."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.collection_name}")
            count = cur.fetchone()[0]
        return {
            "collection_name": self.collection_name,
            "total_documents": count
        }

    def reset_collection(self) -> None:
        """Reset the table (delete all documents)."""
        with self.conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {self.collection_name}")
            self.conn.commit()
        logger.info(f"Reset table: {self.collection_name}")
