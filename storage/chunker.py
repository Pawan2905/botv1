"""Text chunking utilities using LangChain."""

import logging
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk text documents using LangChain's RecursiveCharacterTextSplitter."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize text chunker.

        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        logger.info(f"Initialized TextChunker with size={chunk_size}, overlap={chunk_overlap}")

    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk a single document into smaller pieces.

        Args:
            document: Document dictionary with 'content' field

        Returns:
            List of chunk dictionaries with metadata
        """
        content = document.get("content", "")
        if not content:
            return []

        chunks = self.splitter.split_text(content)
        
        chunk_list = []
        for i, chunk_content in enumerate(chunks):
            chunk = self._create_chunk(document, chunk_content, i)
            chunk_list.append(chunk)

        logger.info(f"Created {len(chunk_list)} chunks from document: {document.get('title', 'Unknown')}")
        return chunk_list

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.

        Args:
            documents: List of document dictionaries

        Returns:
            List of all chunks from all documents
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} total chunks from {len(documents)} documents")
        return all_chunks

    def _create_chunk(
        self,
        document: Dict[str, Any],
        content: str,
        chunk_index: int
    ) -> Dict[str, Any]:
        """Create a chunk dictionary with metadata."""
        chunk = {
            "content": content,
            "chunk_index": chunk_index,
            "doc_id": document.get("id"),
            "doc_title": document.get("title"),
            "doc_url": document.get("url"),
            "doc_type": document.get("type"),
            "source": document.get("source"),
        }

        # Copy over additional metadata
        for key in ["space", "project", "labels", "status", "priority"]:
            if key in document:
                chunk[key] = document[key]

        return chunk
