"""Initializes and provides access to external services."""

import logging
from functools import lru_cache
from openai import AzureOpenAI

from config import settings
from data_fetchers import ConfluenceFetcher, JiraFetcher
from storage import ChromaStore, AzureOpenAIEmbeddings
from retrieval import HybridRetriever

logger = logging.getLogger(__name__)

@lru_cache(maxsize=None)
def get_llm_client() -> AzureOpenAI:
    """Initializes and returns the Azure OpenAI client."""
    logger.info("Initializing AzureOpenAI client...")
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )

@lru_cache(maxsize=None)
def get_embeddings_client() -> AzureOpenAIEmbeddings:
    """Initializes and returns the Azure OpenAI Embeddings client."""
    logger.info("Initializing AzureOpenAIEmbeddings client...")
    return AzureOpenAIEmbeddings(
        endpoint=settings.azure_embedding_endpoint,
        api_key=settings.azure_embedding_key,
        deployment_name=settings.azure_embedding_deployment,
        api_version=settings.azure_embedding_api_version,
        use_apim=settings.use_apim_for_embeddings
    )

@lru_cache(maxsize=None)
def get_chroma_store() -> ChromaStore:
    """Initializes and returns the ChromaStore instance."""
    logger.info("Initializing ChromaStore...")
    return ChromaStore(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.chroma_collection_name
    )

@lru_cache(maxsize=None)
def get_retriever() -> HybridRetriever:
    """Initializes and returns the HybridRetriever instance."""
    logger.info("Initializing HybridRetriever...")
    return HybridRetriever(
        chroma_store=get_chroma_store(),
        embeddings=get_embeddings_client(),
        alpha=settings.hybrid_alpha
    )

@lru_cache(maxsize=None)
def get_confluence_fetcher() -> ConfluenceFetcher:
    """Initializes and returns the ConfluenceFetcher instance."""
    logger.info("Initializing ConfluenceFetcher...")
    return ConfluenceFetcher(
        url=settings.confluence_url,
        username=settings.confluence_username,
        api_token=settings.confluence_api_token,
        space_key=settings.confluence_space_key,
        required_label=settings.confluence_required_label
    )

@lru_cache(maxsize=None)
def get_jira_fetcher() -> JiraFetcher:
    """Initializes and returns the JiraFetcher instance."""
    logger.info("Initializing JiraFetcher...")
    return JiraFetcher(
        url=settings.jira_url,
        username=settings.jira_username,
        api_token=settings.jira_api_token,
        project_key=settings.jira_project_key
    )

# Pre-initialize all services on startup
llm_client = get_llm_client()
embeddings_client = get_embeddings_client()
chroma_store = get_chroma_store()
retriever = get_retriever()
confluence_fetcher = get_confluence_fetcher()
jira_fetcher = get_jira_fetcher()

logger.info("All services initialized.")
