"""Bot service integrating all components."""

import logging
import re
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI

from config import settings
from data_fetchers import ConfluenceFetcher, JiraFetcher
from storage import ChromaStore, AzureOpenAIEmbeddings, TextChunker
from retrieval import HybridRetriever

logger = logging.getLogger(__name__)


class BotService:
    """Main service class integrating all components."""
    
    def __init__(self):
        """Initialize the bot service."""
        logger.info("Initializing BotService...")
        
        # Initialize Azure OpenAI client
        self.llm_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
        
        # Initialize embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            endpoint=settings.azure_embedding_endpoint,
            api_key=settings.azure_embedding_key,
            deployment_name=settings.azure_embedding_deployment,
            api_version=settings.azure_embedding_api_version,
            use_apim=settings.use_apim_for_embeddings
        )
        
        # Initialize ChromaDB store
        self.chroma_store = ChromaStore(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.chroma_collection_name
        )
        
        # Initialize chunker
        self.chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Initialize hybrid retriever
        self.retriever = HybridRetriever(
            chroma_store=self.chroma_store,
            embeddings=self.embeddings,
            alpha=settings.hybrid_alpha
        )
        
        # Initialize data fetchers
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
        Chat with the bot using an agentic approach.
        The bot will route the query to the appropriate tool (Jira, Confluence, or General RAG).
        """
        try:
            # Route the query to the appropriate agent
            agent_decision = self._route_query(message)

            # Execute the chosen agent's logic
            if agent_decision["agent"] == "jira":
                return self._execute_jira_agent(agent_decision["task"], agent_decision["params"])
            else:  # Default to general RAG for Confluence or general queries
                return self._execute_rag_query(message, conversation_history, top_k, use_jira_live)

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise

    def _route_query(self, message: str) -> Dict[str, Any]:
        """
        Intelligently routes the user's query to the correct agent (Jira or General).
        """
        # Regex to find Jira ticket keys (e.g., PROJ-123)
        jira_ticket_match = re.search(r"([A-Z]+-\d+)", message, re.IGNORECASE)
        
        # Keywords that strongly suggest a Jira-related query
        jira_keywords = ["jira", "ticket", "issue", "assignee", "priority", "blockers", "deliverables"]

        # --- Jira Agent Routing ---
        if jira_ticket_match or any(keyword in message.lower() for keyword in jira_keywords):
            issue_key = jira_ticket_match.group(1).upper() if jira_ticket_match else None
            
            # Task: Summarization
            if "summarize" in message.lower() and issue_key:
                lines_match = re.search(r"in (\w+|\d+) lines", message, re.IGNORECASE)
                length_constraint = lines_match.group(1) if lines_match else None
                return {"agent": "jira", "task": "summarize", "params": {"issue_key": issue_key, "length_constraint": length_constraint}}

            # Task: Get Assignee
            if "assignee of" in message.lower() and issue_key:
                return {"agent": "jira", "task": "get_assignee", "params": {"issue_key": issue_key}}

            # Task: Get Blockers or Deliverables (routes to a detailed summary)
            if ("blockers" in message.lower() or "deliverables" in message.lower()) and issue_key:
                return {"agent": "jira", "task": "summarize_details", "params": {"issue_key": issue_key, "focus": "blockers/deliverables"}}

            # Task: High Priority Tickets
            if "high priority tickets" in message.lower():
                return {"agent": "jira", "task": "high_priority_tickets", "params": {}}

        # --- Default to General Agent ---
        return {"agent": "general", "task": "rag_query", "params": {"query": message}}

    def _execute_jira_agent(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a specific Jira-related task."""
        
        if task == "summarize":
            issue_key = params["issue_key"]
            summary = self.summarize_jira_issue(issue_key, length_constraint=params.get("length_constraint"))
            if summary:
                return {"response": summary, "sources": [self.get_jira_issue(issue_key)]}
            else:
                return {"response": f"Sorry, I could not generate a summary for {issue_key}.", "sources": []}

        if task == "get_assignee":
            issue_key = params["issue_key"]
            issue = self.get_jira_issue(issue_key)
            if issue and issue.get('assignee'):
                return {"response": f"The assignee of {issue_key} is {issue['assignee']}.", "sources": [issue]}
            elif issue:
                return {"response": f"{issue_key} is currently unassigned.", "sources": [issue]}
            else:
                return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

        if task == "summarize_details":
            issue_key = params["issue_key"]
            summary = self.summarize_jira_issue(issue_key, focus=params.get("focus"))
            if summary:
                return {"response": summary, "sources": [self.get_jira_issue(issue_key)]}
            else:
                return {"response": f"Sorry, I could not find details on blockers or deliverables for {issue_key}.", "sources": []}

        if task == "high_priority_tickets":
            jql = "priority in (High, Highest) ORDER BY updated DESC"
            issues = self.search_jira_issues(jql=jql, max_results=5)
            if issues:
                response_text = "Here are the top 5 high priority tickets:\n"
                for issue in issues:
                    response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
                return {"response": response_text, "sources": issues}
            else:
                return {"response": "I couldn't find any high priority tickets.", "sources": []}

        return {"response": "Sorry, I'm not sure how to handle that Jira request.", "sources": []}

    def _execute_rag_query(self, message: str, conversation_history: Optional[List[Dict[str, str]]], top_k: int, use_jira_live: bool) -> Dict[str, Any]:
        """Executes the general RAG query for Confluence or general questions."""
        
        live_jira_context = ""
        if use_jira_live:
            logger.info("Fetching live Jira data for context...")
            jira_issues = self.jira_fetcher.search_issues(message, max_results=3)
            if jira_issues:
                live_jira_context = "\n\n=== Live Jira Issues for Context ===\n"
                for issue in jira_issues:
                    live_jira_context += f"\n{issue['key']}: {issue['title']} (Status: {issue['status']})\n"
        
        results = self.query(message, top_k=top_k, method="hybrid")
        context = self._build_context(results)
        
        if live_jira_context:
            context += live_jira_context
            
        messages = self._build_messages(message, context, conversation_history)
        
        response = self.llm_client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        sources = [{"title": r.get("metadata", {}).get("doc_title", "Unknown"), "url": r.get("metadata", {}).get("doc_url", ""), "type": r.get("metadata", {}).get("doc_type", "unknown"), "score": r.get("score", 0)} for r in results]
        
        return {"response": answer, "sources": sources}

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
                prompt += f" The summary should be about {length_constraint} lines long."
            if focus == "blockers/deliverables":
                prompt += " Focus specifically on any mentioned blockers, dependencies, or deliverables. Analyze the description and comments to identify these."
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
    
    # --- Other existing methods ---
    
    def index_data(self, source: str = "both", refresh: bool = False) -> Dict[str, Any]:
        """
        Index data from Confluence and/or Jira.
        """
        logger.info(f"Starting indexing from {source} (refresh={refresh})")
        
        try:
            if refresh:
                logger.info("Refreshing collection...")
                self.chroma_store.reset_collection()
            
            all_documents = []
            
            if source in ["confluence", "both"]:
                logger.info("Fetching Confluence pages...")
                confluence_pages = self.confluence_fetcher.fetch_all_pages()
                all_documents.extend(confluence_pages)
                logger.info(f"Fetched {len(confluence_pages)} Confluence pages")
            
            if source in ["jira", "both"]:
                logger.info("Fetching Jira issues...")
                jira_issues = self.jira_fetcher.fetch_all_issues()
                all_documents.extend(jira_issues)
                logger.info(f"Fetched {len(jira_issues)} Jira issues")
            
            if not all_documents:
                logger.warning("No documents fetched")
                return {"status": "completed", "documents_indexed": 0, "chunks_created": 0}
            
            logger.info("Chunking documents...")
            chunks = self.chunker.chunk_documents(all_documents)
            logger.info(f"Created {len(chunks)} chunks")
            
            logger.info("Generating embeddings...")
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = self.embeddings.embed_documents(chunk_texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            logger.info("Adding to ChromaDB...")
            self.chroma_store.add_documents(chunks, embeddings)
            
            logger.info("Indexing for BM25...")
            self.retriever.index_documents(chunks)
            
            logger.info("Indexing completed successfully")
            
            return {"status": "completed", "documents_indexed": len(all_documents), "chunks_created": len(chunks)}
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        method: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the knowledge base.
        """
        try:
            results = self.retriever.retrieve(query=query, top_k=top_k, filters=filters, method=method)
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def create_jira_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new Jira issue."""
        try:
            kwargs = {}
            if priority:
                kwargs["priority"] = {"name": priority}
            if labels:
                kwargs["labels"] = labels
            
            issue = self.jira_fetcher.create_issue(project_key=project_key, summary=summary, description=description, issue_type=issue_type, **kwargs)
            return issue
        except Exception as e:
            logger.error(f"Failed to create Jira issue: {e}")
            raise
    
    def update_jira_issue(self, issue_key: str, **fields) -> Optional[Dict[str, Any]]:
        """Update a Jira issue."""
        try:
            return self.jira_fetcher.update_issue(issue_key, **fields)
        except Exception as e:
            logger.error(f"Failed to update Jira issue: {e}")
            raise
    
    def transition_jira_issue(self, issue_key: str, status: str) -> bool:
        """Transition a Jira issue to a new status."""
        try:
            return self.jira_fetcher.transition_issue(issue_key, status)
        except Exception as e:
            logger.error(f"Failed to transition Jira issue: {e}")
            raise
    
    def add_jira_comment(self, issue_key: str, comment: str) -> bool:
        """Add a comment to a Jira issue."""
        try:
            return self.jira_fetcher.add_comment(issue_key, comment)
        except Exception as e:
            logger.error(f"Failed to add Jira comment: {e}")
            raise
    
    def get_jira_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get a Jira issue by key."""
        try:
            return self.jira_fetcher.fetch_issue_by_key(issue_key)
        except Exception as e:
            logger.error(f"Failed to get Jira issue: {e}")
            raise
    
    def search_jira_issues(self, query: Optional[str] = None, jql: Optional[str] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Jira issues using either a text query or a JQL query."""
        try:
            if jql:
                return self.jira_fetcher.fetch_all_issues(jql=jql, max_results=max_results)
            elif query:
                return self.jira_fetcher.search_issues(query, max_results)
            else:
                return self.jira_fetcher.fetch_all_issues(max_results=max_results)
        except Exception as e:
            logger.error(f"Failed to search Jira issues: {e}")
            raise

    def update_confluence_page(self, page_id: str, title: str, content: str) -> bool:
        """Update a Confluence page."""
        try:
            return self.confluence_fetcher.update_page(page_id, title, content)
        except Exception as e:
            logger.error(f"Failed to update Confluence page: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "chroma": self.chroma_store.get_stats(),
            "retrieval": self.retriever.get_retrieval_stats()
        }
    
    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents."""
        if not results:
            return "No relevant information found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            
            title = metadata.get("doc_title", "Unknown")
            doc_type = metadata.get("doc_type", "unknown")
            
            context_parts.append(f"[Source {i} - {doc_type}: {title}]\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _build_messages(
        self,
        message: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Build messages for LLM."""
        system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant with access to Confluence and Jira data.
Your role is to answer questions based on the provided context from these sources.

Guidelines:
- Use the context provided to answer questions accurately
- If the context doesn't contain enough information, say so
- Cite sources when possible
- For Jira-related questions, provide actionable insights
- Be concise and professional
- If asked to create or update Jira issues, acknowledge the request and provide clear guidance"""
        }
        
        messages = [system_message]
        
        if conversation_history:
            messages.extend(conversation_history[-5:])
        
        user_message = {
            "role": "user",
            "content": f"""Context from knowledge base:\n\n{context}\n\nUser question: {message}\n\nPlease answer the question based on the context provided above."""
        }
        
        messages.append(user_message)
        
        return messages
