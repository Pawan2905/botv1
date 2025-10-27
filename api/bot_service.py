"""Bot service integrating all components with an agentic architecture."""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI

from config import settings
from data_fetchers import ConfluenceFetcher, JiraFetcher
from storage import ChromaStore, AzureOpenAIEmbeddings, TextChunker
from retrieval import HybridRetriever

logger = logging.getLogger(__name__)


class BotService:
    """
    Main service class integrating all components.
    Re-architected to use an agentic approach for routing and handling queries.
    """
    
    def __init__(self):
        """Initialize the bot service and its components."""
        logger.info("Initializing BotService...")
        
        self.llm_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
        self.embeddings = AzureOpenAIEmbeddings(
            endpoint=settings.azure_embedding_endpoint,
            api_key=settings.azure_embedding_key,
            deployment_name=settings.azure_embedding_deployment,
            api_version=settings.azure_embedding_api_version,
            use_apim=settings.use_apim_for_embeddings
        )
        self.chroma_store = ChromaStore(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.chroma_collection_name
        )
        self.chunker = TextChunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        self.retriever = HybridRetriever(chroma_store=self.chroma_store, embeddings=self.embeddings, alpha=settings.hybrid_alpha)
        self.confluence_fetcher = ConfluenceFetcher(
            url=settings.confluence_url,
            username=settings.confluence_username,
            api_token=settings.confluence_api_token,
            space_key=settings.confluence_space_key
        )
        self.jira_fetcher = JiraFetcher(
            url=settings.jira_url,
            username=settings.jira_username,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key
        )
        
        logger.info("BotService initialized successfully")

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        use_jira_live: bool = False
    ) -> Dict[str, Any]:
        """
        Main chat entry point. Routes user query to the appropriate agent/tool.
        """
        try:
            tool_call = self._get_tool_call(message)
            
            if tool_call and tool_call.get("tool_name"):
                tool_name = tool_call["tool_name"]
                args = tool_call["args"]
                
                # Execute the selected tool
                if hasattr(self, f"_tool_{tool_name}"):
                    tool_method = getattr(self, f"_tool_{tool_name}")
                    return tool_method(**args)
            
            # Fallback to general RAG query if no specific tool is chosen
            return self._tool_rag_search(query=message, conversation_history=conversation_history, top_k=top_k)

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {"response": "Sorry, I encountered an error while processing your request.", "sources": []}

    def _get_tool_call(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Uses an LLM to determine which tool to call based on the user's message.
        """
        tools_json = json.dumps(self._get_available_tools(), indent=2)
        system_prompt = f"""
You are an intelligent routing agent. Your job is to analyze the user's query and determine which tool is best suited to handle it.
You must respond in JSON format with the tool name and the arguments required by that tool.

Available tools:
{tools_json}

If no specific tool seems appropriate, respond with an empty JSON object: {{}}.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            tool_call_str = response.choices[0].message.content
            return json.loads(tool_call_str)
        except Exception as e:
            logger.error(f"Failed to get tool call from LLM: {e}")
            return None

    # --- Agentic Tools ---

    def _tool_get_issue_status(self, issue_key: str) -> Dict[str, Any]:
        """Tool to get the status of a specific Jira ticket."""
        issue = self.get_jira_issue(issue_key)
        if issue and issue.get('status'):
            return {"response": f"The status of ticket {issue_key} is '{issue['status']}'.", "sources": [issue]}
        return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

    def _tool_get_assignee(self, issue_key: str) -> Dict[str, Any]:
        """Tool to get the assignee of a specific Jira ticket."""
        issue = self.get_jira_issue(issue_key)
        if issue and issue.get('assignee'):
            return {"response": f"The assignee of {issue_key} is {issue['assignee']}.", "sources": [issue]}
        elif issue:
            return {"response": f"{issue_key} is currently unassigned.", "sources": [issue]}
        return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

    def _tool_summarize_issue(self, issue_key: str, length_constraint: Optional[str] = None, focus: Optional[str] = None) -> Dict[str, Any]:
        """Tool to summarize a Jira ticket with optional constraints."""
        summary = self.summarize_jira_issue(issue_key, length_constraint, focus)
        if summary:
            return {"response": summary, "sources": [self.get_jira_issue(issue_key)]}
        return {"response": f"Sorry, I could not generate a summary for {issue_key}.", "sources": []}

    def _tool_list_high_priority_tickets(self) -> Dict[str, Any]:
        """Tool to list high priority tickets."""
        jql = "priority in (High, Highest) ORDER BY updated DESC"
        issues = self.search_jira_issues(jql=jql, max_results=5)
        if issues:
            response_text = "Here are the top 5 high priority tickets:\n"
            for issue in issues:
                response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
            return {"response": response_text, "sources": issues}
        return {"response": "I couldn't find any high priority tickets.", "sources": []}

    def _tool_rag_search(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None, top_k: int = 5) -> Dict[str, Any]:
        """Tool for general RAG search over Confluence and Jira."""
        results = self.query(query, top_k=top_k, method="hybrid")
        context = self._build_context(results)
        messages = self._build_messages(query, context, conversation_history)
        
        response = self.llm_client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        sources = [{"title": r.get("metadata", {}).get("doc_title", "Unknown"), "url": r.get("metadata", {}).get("doc_url", ""), "type": r.get("metadata", {}).get("doc_type", "unknown"), "score": r.get("score", 0)} for r in results]
        
        return {"response": answer, "sources": sources}

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Returns a list of available tools for the agentic router."""
        return [
            {
                "tool_name": "get_issue_status",
                "description": "Get the status of a specific Jira ticket.",
                "args": {"issue_key": "The Jira ticket key (e.g., 'PROJ-123')."}
            },
            {
                "tool_name": "get_assignee",
                "description": "Find out who is assigned to a specific Jira ticket.",
                "args": {"issue_key": "The Jira ticket key."}
            },
            {
                "tool_name": "summarize_issue",
                "description": "Summarize a Jira ticket. Can also focus on blockers or deliverables.",
                "args": {
                    "issue_key": "The Jira ticket key.",
                    "length_constraint": "Optional. A constraint for the summary length (e.g., 'two lines').",
                    "focus": "Optional. The specific focus of the summary (e.g., 'blockers', 'deliverables')."
                }
            },
            {
                "tool_name": "list_high_priority_tickets",
                "description": "List all high-priority tickets.",
                "args": {}
            },
            {
                "tool_name": "rag_search",
                "description": "Perform a general search over the knowledge base (Confluence and Jira). Use this for how-to questions, documentation lookups, and general queries.",
                "args": {"query": "The user's search query."}
            }
        ]

    # --- Helper and Existing Methods ---

    def summarize_jira_issue(self, issue_key: str, length_constraint: Optional[str] = None, focus: Optional[str] = None) -> Optional[str]:
        """
        Generate a summary for a Jira issue using the LLM, with optional constraints.
        """
        try:
            issue = self.get_jira_issue(issue_key)
            if not issue:
                return None

            prompt = "Please provide a concise summary of the following Jira ticket."
            if length_constraint:
                prompt += f" The summary should be about {length_constraint}."
            if focus:
                prompt += f" Focus specifically on any mentioned {focus}."
            else:
                prompt += " Focus on the main objective, the latest status, and any key comments."

            content_for_summary = f"""
            {prompt}

            Ticket Key: {issue.get('key')}
            Title: {issue.get('title')}
            Status: {issue.get('status')}
            Assignee: {issue.get('assignee', 'Unassigned')}
            Description: {issue.get('description', 'No description provided.')}
            Content: {issue.get('content')}
            """

            messages = [
                {"role": "system", "content": "You are an expert at summarizing Jira tickets accurately and concisely."},
                {"role": "user", "content": content_for_summary}
            ]

            response = self.llm_client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate summary for issue {issue_key}: {e}")
            raise
    
    def index_data(self, source: str = "both", refresh: bool = False) -> Dict[str, Any]:
        logger.info(f"Starting indexing from {source} (refresh={refresh})")
        if refresh:
            self.chroma_store.reset_collection()
        
        all_documents = []
        if source in ["confluence", "both"]:
            all_documents.extend(self.confluence_fetcher.fetch_all_pages())
        if source in ["jira", "both"]:
            all_documents.extend(self.jira_fetcher.fetch_all_issues())
        
        if not all_documents:
            return {"status": "completed", "documents_indexed": 0, "chunks_created": 0}
        
        chunks = self.chunker.chunk_documents(all_documents)
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = self.embeddings.embed_documents(chunk_texts)
        self.chroma_store.add_documents(chunks, embeddings)
        self.retriever.index_documents(chunks)
        
        return {"status": "completed", "documents_indexed": len(all_documents), "chunks_created": len(chunks)}
    
    def query(self, query: str, top_k: int = 5, method: str = "hybrid", filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(query=query, top_k=top_k, filters=filters, method=method)
    
    def create_jira_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task", priority: Optional[str] = None, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        kwargs = {}
        if priority: kwargs["priority"] = {"name": priority}
        if labels: kwargs["labels"] = labels
        return self.jira_fetcher.create_issue(project_key=project_key, summary=summary, description=description, issue_type=issue_type, **kwargs)
    
    def update_jira_issue(self, issue_key: str, **fields) -> Optional[Dict[str, Any]]:
        return self.jira_fetcher.update_issue(issue_key, **fields)
    
    def transition_jira_issue(self, issue_key: str, status: str) -> bool:
        return self.jira_fetcher.transition_issue(issue_key, status)
    
    def add_jira_comment(self, issue_key: str, comment: str) -> bool:
        return self.jira_fetcher.add_comment(issue_key, comment)
    
    def get_jira_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        return self.jira_fetcher.fetch_issue_by_key(issue_key)
    
    def search_jira_issues(self, query: Optional[str] = None, jql: Optional[str] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        if jql:
            return self.jira_fetcher.fetch_all_issues(jql=jql, max_results=max_results)
        elif query:
            return self.jira_fetcher.search_issues(query, max_results)
        return self.jira_fetcher.fetch_all_issues(max_results=max_results)

    def update_confluence_page(self, page_id: str, title: str, content: str) -> bool:
        return self.confluence_fetcher.update_page(page_id, title, content)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "chroma": self.chroma_store.get_stats(),
            "retrieval": self.retriever.get_retrieval_stats()
        }
    
    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        context_parts = [f"[Source {i+1} - {r.get('metadata', {}).get('doc_type', 'unknown')}: {r.get('metadata', {}).get('doc_title', 'Unknown')}]\n{r.get('content', '')}\n" for i, r in enumerate(results)]
        return "\n".join(context_parts) if context_parts else "No relevant information found."
    
    def _build_messages(self, message: str, context: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": "You are a helpful AI assistant. Use the provided context to answer questions accurately. If the context is insufficient, say so."
        }
        messages = [system_message]
        if conversation_history:
            messages.extend(conversation_history[-5:])
        messages.append({"role": "user", "content": f"Context:\n\n{context}\n\nUser question: {message}"})
        return messages
