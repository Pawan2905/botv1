"""Azure OpenAI embeddings wrapper."""

import logging
from typing import List
from openai import AzureOpenAI
import time

logger = logging.getLogger(__name__)


class AzureOpenAIEmbeddings:
    """Generate embeddings using Azure OpenAI."""
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str = "2024-02-15-preview"
    ):
        """
        Initialize Azure OpenAI embeddings client.
        
        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            deployment_name: Deployment name for embeddings model
            api_version: API version
        """
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment_name = deployment_name
        logger.info(f"Initialized Azure OpenAI embeddings with deployment: {deployment_name}")
    
    def embed_documents(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.deployment_name
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated embeddings for batch {i//batch_size + 1}")
                
                # Rate limiting - adjust as needed
                if i + batch_size < len(texts):
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {e}")
                # Return zero vectors for failed batches
                embeddings.extend([[0.0] * 1536 for _ in batch])
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = self.client.embeddings.create(
                input=[text],
                model=self.deployment_name
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return [0.0] * 1536  # Return zero vector on error
