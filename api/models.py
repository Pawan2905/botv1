"""Pydantic models for API requests and responses."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for querying the knowledge base."""
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, description="Number of results to return", ge=1, le=20)
    method: str = Field(default="hybrid", description="Retrieval method: 'hybrid', 'dense', or 'sparse'")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class QueryResponse(BaseModel):
    """Response model for query results."""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    method: str


class ChatRequest(BaseModel):
    """Request model for chat with the bot."""
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(default=None, description="Previous conversation messages")
    top_k: int = Field(default=5, description="Number of context documents to retrieve")
    use_jira_live: bool = Field(default=False, description="Fetch live Jira data for the query")


class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    sources: List[Dict[str, Any]]
    conversation_id: Optional[str] = None


class JiraIssueCreate(BaseModel):
    """Request model for creating a Jira issue."""
    project_key: str = Field(..., description="Jira project key")
    summary: str = Field(..., description="Issue summary")
    description: str = Field(..., description="Issue description")
    issue_type: str = Field(default="Task", description="Issue type (Task, Bug, Story, etc.)")
    priority: Optional[str] = Field(default=None, description="Issue priority")
    labels: Optional[List[str]] = Field(default=None, description="Issue labels")


class JiraIssueUpdate(BaseModel):
    """Request model for updating a Jira issue."""
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None


class JiraCommentAdd(BaseModel):
    """Request model for adding a comment to a Jira issue."""
    comment: str = Field(..., description="Comment text")


class IndexRequest(BaseModel):
    """Request model for indexing data."""
    source: str = Field(..., description="Data source: 'confluence', 'jira', or 'both'")
    refresh: bool = Field(default=False, description="Delete existing data before indexing")


class IndexResponse(BaseModel):
    """Response model for indexing operation."""
    status: str
    documents_indexed: int
    chunks_created: int
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    chroma_stats: Dict[str, Any]
    retrieval_stats: Dict[str, Any]
