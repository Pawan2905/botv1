"""Text chunking utilities with overlap support."""

import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk text documents with overlap for better context preservation."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
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
        
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = self._split_by_paragraphs(content)
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(self._create_chunk(document, current_chunk, chunk_index))
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + paragraph
                else:
                    # Paragraph is larger than chunk_size, split it
                    para_chunks = self._split_large_text(paragraph)
                    for i, para_chunk in enumerate(para_chunks):
                        if i == 0:
                            current_chunk = para_chunk
                        else:
                            chunks.append(self._create_chunk(document, current_chunk, chunk_index))
                            chunk_index += 1
                            overlap_text = self._get_overlap_text(current_chunk)
                            current_chunk = overlap_text + para_chunk
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(self._create_chunk(document, current_chunk, chunk_index))
        
        logger.info(f"Created {len(chunks)} chunks from document: {document.get('title', 'Unknown')}")
        return chunks
    
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
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines or single newlines followed by bullet points
        paragraphs = re.split(r'\n\n+|\n(?=[•\-\*])', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_large_text(self, text: str) -> List[str]:
        """Split large text that exceeds chunk_size."""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Extract overlap text from the end of a chunk."""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Try to find a sentence boundary for cleaner overlap
        overlap_start = len(text) - self.chunk_overlap
        sentence_boundaries = [m.end() for m in re.finditer(r'[.!?]\s+', text)]
        
        # Find the closest sentence boundary to the overlap start
        for boundary in reversed(sentence_boundaries):
            if boundary >= overlap_start:
                return text[boundary:]
        
        # If no sentence boundary found, just take the last chunk_overlap characters
        return text[-self.chunk_overlap:]
    
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
