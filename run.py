"""Main entry point to run the FastAPI application."""

import uvicorn
from config import settings

if __name__ == "__main__":
    print("=" * 80)
    print("Starting Confluence & Jira RAG Bot")
    print("=" * 80)
    print(f"Host: {settings.api_host}")
    print(f"Port: {settings.api_port}")
    print(f"API Documentation: http://{settings.api_host}:{settings.api_port}/docs")
    print("=" * 80)
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
