"""Configuration management for the RAG application."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration (for LLM)
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_deployment_name: str = Field(default="gpt-4", env="AZURE_OPENAI_DEPLOYMENT_NAME")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", env="AZURE_OPENAI_API_VERSION")
    
    # Azure OpenAI Embeddings Configuration (APIM or Direct)
    azure_embedding_endpoint: str = Field(..., env="AZURE_EMBEDDING_ENDPOINT")
    azure_embedding_key: str = Field(..., env="AZURE_EMBEDDING_KEY")  # Can be API key or subscription key
    azure_embedding_deployment: str = Field(default="text-embedding-ada-002", env="AZURE_EMBEDDING_DEPLOYMENT")
    azure_embedding_api_version: str = Field(default="2024-02-15-preview", env="AZURE_EMBEDDING_API_VERSION")
    use_apim_for_embeddings: bool = Field(default=True, env="USE_APIM_FOR_EMBEDDINGS")  # True if using APIM
    
    # Confluence Configuration
    confluence_url: str = Field(..., env="CONFLUENCE_URL")
    confluence_username: str = Field(..., env="CONFLUENCE_USERNAME")
    confluence_api_token: str = Field(..., env="CONFLUENCE_API_TOKEN")
    confluence_space_key: Optional[str] = Field(default=None, env="CONFLUENCE_SPACE_KEY")  # If None, fetches from all spaces
    confluence_required_label: Optional[str] = Field(default=None, env="CONFLUENCE_REQUIRED_LABEL") # If set, only fetches pages with this label
    
    # Jira Configuration
    jira_url: str = Field(..., env="JIRA_URL")
    jira_username: str = Field(..., env="JIRA_USERNAME")
    jira_api_token: str = Field(..., env="JIRA_API_TOKEN")
    jira_project_key: Optional[str] = Field(default=None, env="JIRA_PROJECT_KEY")  # If None, fetches from all projects
    
    # ChromaDB Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="confluence_jira_docs", env="CHROMA_COLLECTION_NAME")
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Retrieval Configuration
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")
    hybrid_alpha: float = Field(default=0.5, env="HYBRID_ALPHA")
    
    # FastAPI Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
