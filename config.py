"""Configuration management for the RAG application."""

import os
from typing import Optional, List, Dict, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

def load_yaml_config(file_path: str) -> dict:
    """Load configuration from a YAML file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    return {}

yaml_config = load_yaml_config("config.yaml")

class ConfluenceSource(BaseModel):
    space: str
    optional_labels: Optional[List[str]] = None

class JiraSource(BaseModel):
    labels: List[str]

class ConfluenceLoader(BaseModel):
    enable: bool = False
    sources: List[ConfluenceSource] = []

class JiraLoader(BaseModel):
    enable: bool = False
    sources: List[JiraSource] = []

class LoaderSettings(BaseModel):
    confluence: ConfluenceLoader = ConfluenceLoader()
    jira: JiraLoader = JiraLoader()

class StorageSettings(BaseModel):
    provider: str = Field(default="chroma", description="Storage provider: 'chroma' or 'postgres'")

class Settings(BaseSettings):
    """Application settings loaded from environment variables and config.yaml."""
    
    # Storage Configuration from YAML
    storage: StorageSettings = Field(default_factory=lambda: StorageSettings.model_validate(yaml_config.get("storage", {})))
    
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
    confluence_space_key: Optional[str] = Field(default=None, env="CONFLUENCE_SPACE_KEY")
    confluence_required_label: Optional[str] = Field(default=None, env="CONFLUENCE_REQUIRED_LABEL")

    # Jira Configuration
    jira_url: str = Field(..., env="JIRA_URL")
    jira_username: str = Field(..., env="JIRA_USERNAME")
    jira_api_token: str = Field(..., env="JIRA_API_TOKEN")
    jira_project_key: Optional[str] = Field(default=None, env="JIRA_PROJECT_KEY")
    
    # Loader Configuration from YAML
    loader: LoaderSettings = Field(default_factory=lambda: LoaderSettings.model_validate(yaml_config.get("loader", {})))
    
    # ChromaDB Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="confluence_jira_docs", env="CHROMA_COLLECTION_NAME")
    
    # PostgreSQL Configuration
    postgres_connection_string: Optional[str] = Field(default=None, env="POSTGRES_CONNECTION_STRING")
    postgres_collection_name: str = Field(default="confluence_jira_docs", env="POSTGRES_COLLECTION_NAME")
    
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
