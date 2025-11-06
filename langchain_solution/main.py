"""FastAPI application for the LangGraph agent."""

from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from langgraph.graph import END

from langchain_solution.graph import app

# Create FastAPI app
fastapi_app = FastAPI(
    title="LangGraph RAG Bot",
    description="AI-powered bot using LangGraph for robust, dynamic agentic solutions",
    version="1.0.0",
)

@fastapi_app.post("/chat")
async def chat(message: str):
    """Chat with the LangGraph agent."""
    inputs = {"messages": [HumanMessage(content=message)]}
    response = app.invoke(inputs)
    return {"response": response["messages"][-1].content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
