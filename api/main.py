"""FastAPI application for the RAG bot."""

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn

from config import settings
from api.models import (
    QueryRequest, QueryResponse, ChatRequest, ChatResponse,
    JiraIssueCreate, JiraIssueUpdate, JiraCommentAdd,
    IndexRequest, IndexResponse, HealthResponse, ConfluencePageUpdate
)
from api.bot_service import BotService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot service instance
bot_service: Optional[BotService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global bot_service
    
    # Startup
    logger.info("Starting up the application...")
    try:
        bot_service = BotService()
        logger.info("BotService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize BotService: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down the application...")


# Create FastAPI app
app = FastAPI(
    title="Confluence & Jira RAG Bot",
    description="AI-powered bot for querying Confluence and Jira data with hybrid retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Confluence & Jira RAG Bot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        stats = bot_service.get_stats()
        return HealthResponse(
            status="healthy",
            chroma_stats=stats.get("chroma", {}),
            retrieval_stats=stats.get("retrieval", {})
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/index", response_model=IndexResponse, tags=["Indexing"])
async def index_data(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Index data from Confluence and/or Jira.
    
    This operation runs in the background and may take some time.
    """
    try:
        if request.source.lower() not in ["confluence", "jira", "both"]:
            raise HTTPException(
                status_code=400,
                detail="Source must be 'confluence', 'jira', or 'both'"
            )
        
        # Start indexing in background
        background_tasks.add_task(
            bot_service.index_data,
            source=request.source.lower(),
            refresh=request.refresh
        )
        
        return IndexResponse(
            status="started",
            documents_indexed=0,
            chunks_created=0,
            message=f"Indexing {request.source} data started in background"
        )
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base using hybrid retrieval.
    
    Supports dense (vector), sparse (BM25), and hybrid search methods.
    """
    try:
        results = bot_service.query(
            query=request.query,
            top_k=request.top_k,
            method=request.method,
            filters=request.filters
        )
        
        return QueryResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            method=request.method
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_bot(request: ChatRequest):
    """
    Chat with the bot using RAG.
    
    The bot retrieves relevant context and generates a response using Azure OpenAI.
    Optionally fetches live Jira data if use_jira_live is True.
    """
    try:
        response = bot_service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            top_k=request.top_k,
            use_jira_live=request.use_jira_live
        )
        
        return response
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jira/issue", tags=["Jira"])
async def create_jira_issue(request: JiraIssueCreate):
    """Create a new Jira issue."""
    try:
        issue = bot_service.create_jira_issue(
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            issue_type=request.issue_type,
            priority=request.priority,
            labels=request.labels
        )
        
        if not issue:
            raise HTTPException(status_code=500, detail="Failed to create issue")
        
        return issue
    except Exception as e:
        logger.error(f"Failed to create Jira issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/jira/issue/{issue_key}", tags=["Jira"])
async def update_jira_issue(issue_key: str, request: JiraIssueUpdate):
    """Update an existing Jira issue."""
    try:
        fields = request.model_dump(exclude_none=True)
        
        # Handle status transition separately
        if "status" in fields:
            status = fields.pop("status")
            bot_service.transition_jira_issue(issue_key, status)
        
        # Update other fields
        if fields:
            issue = bot_service.update_jira_issue(issue_key, **fields)
            if not issue:
                raise HTTPException(status_code=404, detail="Issue not found or update failed")
            return issue
        
        return {"message": "Issue updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update Jira issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jira/issue/{issue_key}/comment", tags=["Jira"])
async def add_jira_comment(issue_key: str, request: JiraCommentAdd):
    """Add a comment to a Jira issue."""
    try:
        success = bot_service.add_jira_comment(issue_key, request.comment)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add comment")
        
        return {"message": "Comment added successfully", "issue_key": issue_key}
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jira/issue/{issue_key}", tags=["Jira"])
async def get_jira_issue(issue_key: str):
    """Get a specific Jira issue by key."""
    try:
        issue = bot_service.get_jira_issue(issue_key)
        
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        return issue
    except Exception as e:
        logger.error(f"Failed to get Jira issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jira/issue/{issue_key}/summary", tags=["Jira"])
async def summarize_jira_issue(issue_key: str):
    """Summarize a Jira issue."""
    try:
        summary = bot_service.summarize_jira_issue(issue_key)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Issue not found or could not be summarized.")
            
        return {"issue_key": issue_key, "summary": summary}
    except Exception as e:
        logger.error(f"Failed to summarize Jira issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from typing import Optional

@app.get("/jira/search", tags=["Jira"])
async def search_jira_issues(query: Optional[str] = None, jql: Optional[str] = None, max_results: int = 20):
    """Search Jira issues using a text query or a JQL query."""
    try:
        if not query and not jql:
            raise HTTPException(status_code=400, detail="Either 'query' or 'jql' must be provided.")
        
        issues = bot_service.search_jira_issues(query=query, jql=jql, max_results=max_results)
        
        search_param = {"query": query} if query else {"jql": jql}
        return {**search_param, "results": issues, "total": len(issues)}
    except Exception as e:
        logger.error(f"Failed to search Jira issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/confluence/page/{page_id}", tags=["Confluence"])
async def update_confluence_page(page_id: str, request: ConfluencePageUpdate):
    """Update a Confluence page."""
    try:
        success = bot_service.update_confluence_page(
            page_id=page_id,
            title=request.title,
            content=request.content
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update page")
        
        return {"message": "Page updated successfully", "page_id": page_id}
    except Exception as e:
        logger.error(f"Failed to update Confluence page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/search", tags=["Confluence"])
async def search_confluence_documents(keyword: str, limit: int = 10):
    """Retrieve Confluence documents by topic or keyword."""
    try:
        pages = bot_service.get_confluence_documents_by_keyword(keyword, limit)
        return {"keyword": keyword, "results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to search Confluence documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/how-to-guides", tags=["Confluence"])
async def get_confluence_how_to_guides(limit: int = 10):
    """Get step-by-step guides or SOPs from Confluence."""
    try:
        pages = bot_service.get_confluence_how_to_guides(limit)
        return {"results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to get how-to guides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/policy-info", tags=["Confluence"])
async def get_confluence_policy_info(limit: int = 10):
    """Retrieve company policies or processes from Confluence."""
    try:
        pages = bot_service.get_confluence_policy_info(limit)
        return {"results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to get policy info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/architecture-docs", tags=["Confluence"])
async def get_confluence_architecture_docs(limit: int = 10):
    """Fetch architecture or design documentation from Confluence."""
    try:
        pages = bot_service.get_confluence_architecture_docs(limit)
        return {"results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to get architecture docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/team-page", tags=["Confluence"])
async def get_confluence_team_page(team_name: str, limit: int = 10):
    """Access team pages or meeting notes from Confluence."""
    try:
        pages = bot_service.get_confluence_team_page(team_name, limit)
        return {"team_name": team_name, "results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to get team page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/onboarding-docs", tags=["Confluence"])
async def get_confluence_onboarding_docs(limit: int = 10):
    """Get onboarding or training pages from Confluence."""
    try:
        pages = bot_service.get_confluence_onboarding_docs(limit)
        return {"results": pages, "total": len(pages)}
    except Exception as e:
        logger.error(f"Failed to get onboarding docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/confluence/page/{page_id}/history", tags=["Confluence"])
async def get_confluence_page_history(page_id: str):
    """Retrieve version/edit history of a Confluence page."""
    try:
        history = bot_service.get_confluence_page_history(page_id)
        return {"page_id": page_id, "history": history}
    except Exception as e:
        logger.error(f"Failed to get page history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cross-system/linked-docs/{issue_key}", tags=["Cross-System"])
async def get_linked_docs(issue_key: str):
    """Find Confluence pages linked to a specific Jira ticket."""
    try:
        pages = bot_service.link_docs_to_ticket(issue_key)
        return {"issue_key": issue_key, "linked_pages": pages}
    except Exception as e:
        logger.error(f"Failed to get linked documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cross-system/release-summary/{release_name}", tags=["Cross-System"])
async def get_release_summary(release_name: str):
    """List Jira issues in a release and link to release notes."""
    try:
        summary = bot_service.release_summary(release_name)
        return {"release_name": release_name, **summary}
    except Exception as e:
        logger.error(f"Failed to get release summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cross-system/incident-summary/{incident_key}", tags=["Cross-System"])
async def get_incident_summary(incident_key: str):
    """Summarize an incident with corresponding postmortems."""
    try:
        summary = bot_service.incident_summary(incident_key)
        return {"incident_key": incident_key, **summary}
    except Exception as e:
        logger.error(f"Failed to get incident summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cross-system/sprint-summary/{sprint_name}", tags=["Cross-System"])
async def get_sprint_summary(sprint_name: str):
    """Combine sprint metrics with documentation references."""
    try:
        summary = bot_service.sprint_docs_summary(sprint_name)
        return {"sprint_name": sprint_name, **summary}
    except Exception as e:
        logger.error(f"Failed to get sprint summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cross-system/auto-doc", tags=["Cross-System"])
async def create_auto_doc(project_key: str, doc_type: str, name: str):
    """Auto-create Confluence release or meeting pages using Jira data."""
    try:
        doc = bot_service.auto_doc_creation(project_key, doc_type, name)
        if not doc:
            raise HTTPException(status_code=400, detail="Invalid document type or failed to generate document.")
        return doc
    except Exception as e:
        logger.error(f"Failed to auto-create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
