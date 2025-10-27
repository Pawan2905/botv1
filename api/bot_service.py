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

    def _tool_list_open_bugs(self) -> Dict[str, Any]:
        """Tool to list open bugs."""
        jql = "issuetype = Bug AND status != Done ORDER BY updated DESC"
        issues = self.search_jira_issues(jql=jql, max_results=10)
        if issues:
            response_text = "Here are the top 10 open bugs:\n"
            for issue in issues:
                response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
            return {"response": response_text, "sources": issues}
        return {"response": "I couldn't find any open bugs.", "sources": []}

    def _tool_filter_issues(self, assignee: Optional[str] = None, project: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
        """Tool to filter issues by assignee, project, or priority."""
        jql_parts = []
        if assignee:
            jql_parts.append(f'assignee = "{assignee}"')
        if project:
            jql_parts.append(f'project = "{project}"')
        if priority:
            jql_parts.append(f'priority = "{priority}"')
        
        if not jql_parts:
            return {"response": "Please provide at least one filter (assignee, project, or priority).", "sources": []}
            
        jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"
        issues = self.search_jira_issues(jql=jql, max_results=10)
        
        if issues:
            response_text = "Here are the matching issues:\n"
            for issue in issues:
                response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
            return {"response": response_text, "sources": issues}
        return {"response": "No issues found matching your criteria.", "sources": []}

    def _tool_get_sprint_details(self, sprint_name: str) -> Dict[str, Any]:
        """Tool to get details for a specific sprint."""
        sprint = self.jira_fetcher.get_sprint_by_name(sprint_name)
        if sprint:
            issues = self.jira_fetcher.get_issues_for_sprint(sprint['id'])
            response_text = f"Details for sprint '{sprint_name}':\n"
            response_text += f"- Start Date: {sprint['startDate']}\n"
            response_text += f"- End Date: {sprint['endDate']}\n"
            response_text += f"- State: {sprint['state']}\n"
            response_text += f"- Issues ({len(issues)}):\n"
            for issue in issues:
                response_text += f"  - {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
            return {"response": response_text, "sources": issues}
        return {"response": f"Sprint '{sprint_name}' not found.", "sources": []}

    def _tool_get_blocked_issues(self) -> Dict[str, Any]:
        """Tool to find blocked or high-priority tickets."""
        jql = 'status = "Blocked" or priority in (Highest, High)'
        issues = self.search_jira_issues(jql=jql, max_results=10)
        if issues:
            response_text = "Here are the top 10 blocked or high-priority issues:\n"
            for issue in issues:
                response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']}, Priority: {issue['priority']})\n"
            return {"response": response_text, "sources": issues}
        return {"response": "No blocked or high-priority issues found.", "sources": []}

    def _tool_create_ticket(self, project_key: str, summary: str, description: str, issue_type: str = "Task", priority: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Tool to create a new Jira ticket."""
        issue = self.create_jira_issue(project_key, summary, description, issue_type, priority, labels)
        if issue:
            return {"response": f"Successfully created ticket {issue['key']}.", "sources": [issue]}
        return {"response": "Failed to create ticket.", "sources": []}

    def _tool_update_ticket(self, issue_key: str, summary: Optional[str] = None, description: Optional[str] = None, assignee: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Tool to update an existing Jira ticket."""
        fields = {}
        if summary:
            fields["summary"] = summary
        if description:
            fields["description"] = description
        if assignee:
            fields["assignee"] = {"name": assignee}
        
        if status:
            self.transition_jira_issue(issue_key, status)

        if fields:
            issue = self.update_jira_issue(issue_key, **fields)
            if issue:
                return {"response": f"Successfully updated ticket {issue_key}.", "sources": [issue]}
        
        return {"response": f"Successfully updated ticket {issue_key}.", "sources": []}

    def _tool_add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Tool to add a comment to a Jira issue."""
        success = self.add_jira_comment(issue_key, comment)
        if success:
            return {"response": f"Successfully added comment to ticket {issue_key}.", "sources": []}
        return {"response": "Failed to add comment.", "sources": []}

    def _tool_get_confluence_page(self, keyword: str) -> Dict[str, Any]:
        """Tool to retrieve Confluence documents by topic or keyword."""
        pages = self.confluence_fetcher.get_documents_by_keyword(keyword)
        if pages:
            response_text = f"Here are the Confluence pages I found for '{keyword}':\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": f"I couldn't find any Confluence pages matching '{keyword}'.", "sources": []}

    def _tool_get_how_to_guides(self) -> Dict[str, Any]:
        """Tool to retrieve step-by-step guides or SOPs."""
        pages = self.confluence_fetcher.get_how_to_guides()
        if pages:
            response_text = "Here are the how-to guides I found:\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": "I couldn't find any how-to guides.", "sources": []}

    def _tool_get_policy_info(self) -> Dict[str, Any]:
        """Tool to retrieve company policies or processes."""
        pages = self.confluence_fetcher.get_policy_info()
        if pages:
            response_text = "Here are the policy documents I found:\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": "I couldn't find any policy documents.", "sources": []}

    def _tool_get_architecture_doc(self) -> Dict[str, Any]:
        """Tool to fetch architecture or design documentation."""
        pages = self.confluence_fetcher.get_architecture_doc()
        if pages:
            response_text = "Here are the architecture documents I found:\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": "I couldn't find any architecture documents.", "sources": []}

    def _tool_get_team_page(self, team_name: str) -> Dict[str, Any]:
        """Tool to access team pages or meeting notes."""
        pages = self.confluence_fetcher.get_team_page(team_name)
        if pages:
            response_text = f"Here are the team pages and meeting notes I found for '{team_name}':\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": f"I couldn't find any team pages or meeting notes for '{team_name}'.", "sources": []}

    def _tool_get_onboarding_docs(self) -> Dict[str, Any]:
        """Tool to get onboarding or training pages."""
        pages = self.confluence_fetcher.get_onboarding_docs()
        if pages:
            response_text = "Here are the onboarding documents I found:\n"
            for page in pages:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": pages}
        return {"response": "I couldn't find any onboarding documents.", "sources": []}

    def _tool_get_page_history(self, page_id: str) -> Dict[str, Any]:
        """Tool to retrieve version/edit history of a page."""
        history = self.confluence_fetcher.get_page_history(page_id)
        if history:
            response_text = f"Here is the history for page {page_id}:\n"
            for version in history:
                when = version.get('when', 'N/A')
                author = version.get('by', {}).get('displayName', 'Unknown')
                response_text += f"- Version {version.get('number')}: updated on {when} by {author}\n"
            return {"response": response_text, "sources": history}
        return {"response": f"Could not retrieve history for page {page_id}.", "sources": []}

    def _tool_link_docs_to_ticket(self, issue_key: str) -> Dict[str, Any]:
        """Tool to find Confluence pages linked to a specific Jira ticket."""
        issue = self.get_jira_issue(issue_key)
        if issue and issue.get('linked_pages'):
            response_text = f"Here are the Confluence pages linked to ticket {issue_key}:\n"
            for page in issue['linked_pages']:
                response_text += f"- {page['title']}: {page['url']}\n"
            return {"response": response_text, "sources": issue['linked_pages']}
        return {"response": f"No Confluence pages are linked to ticket {issue_key}.", "sources": []}

    def _tool_release_summary(self, release_name: str) -> Dict[str, Any]:
        """Tool to list Jira issues in a release and link to release notes."""
        jql = f'fixVersion = "{release_name}"'
        issues = self.search_jira_issues(jql=jql)
        release_notes = self.confluence_fetcher.get_documents_by_keyword(f"Release Notes {release_name}", limit=1)
        
        response_text = f"Summary for release '{release_name}':\n"
        if release_notes:
            response_text += f"Release Notes: {release_notes[0]['url']}\n"
        
        if issues:
            response_text += "Issues in this release:\n"
            for issue in issues:
                response_text += f"- {issue['key']}: {issue['title']}\n"
        
        return {"response": response_text, "sources": issues + release_notes}

    def _tool_incident_summary(self, incident_key: str) -> Dict[str, Any]:
        """Tool to summarize incidents with corresponding postmortems."""
        incident = self.get_jira_issue(incident_key)
        postmortems = self.confluence_fetcher.get_documents_by_keyword(f"Postmortem {incident_key}", limit=1)
        
        response_text = f"Summary for incident '{incident_key}':\n"
        if incident:
            response_text += f"Title: {incident['title']}\n"
            response_text += f"Status: {incident['status']}\n"
        
        if postmortems:
            response_text += f"Postmortem: {postmortems[0]['url']}\n"
            
        return {"response": response_text, "sources": [incident] + postmortems}

    def _tool_sprint_docs_summary(self, sprint_name: str) -> Dict[str, Any]:
        """Tool to combine sprint metrics with documentation references."""
        sprint = self.jira_fetcher.get_sprint_by_name(sprint_name)
        if not sprint:
            return {"response": f"Sprint '{sprint_name}' not found.", "sources": []}
            
        issues = self.jira_fetcher.get_issues_for_sprint(sprint['id'])
        docs = self.confluence_fetcher.get_documents_by_keyword(sprint_name)
        
        response_text = f"Summary for sprint '{sprint_name}':\n"
        response_text += f"Issues: {len(issues)}\n"
        
        if docs:
            response_text += "Related Documents:\n"
            for doc in docs:
                response_text += f"- {doc['title']}: {doc['url']}\n"
                
        return {"response": response_text, "sources": issues + docs}

    def _tool_auto_doc_creation(self, project_key: str, doc_type: str, name: str) -> Dict[str, Any]:
        """Tool to auto-create Confluence release or meeting pages using Jira data."""
        if doc_type == "release":
            jql = f'project = "{project_key}" AND fixVersion = "{name}"'
            issues = self.search_jira_issues(jql=jql)
            content = "<h1>Release Notes</h1>\n<ul>"
            for issue in issues:
                content += f"<li>{issue['key']}: {issue['title']}</li>"
            content += "</ul>"
            
            page = self.confluence_fetcher.update_page(title=f"Release Notes: {name}", content=content)
            if page:
                return {"response": f"Created release notes page for {name}.", "sources": [page]}
                
        elif doc_type == "meeting":
            content = "<h1>Meeting Notes</h1>\n<h2>Attendees</h2>\n<p></p>\n<h2>Agenda</h2>\n<p></p>\n<h2>Notes</h2>\n<p></p>"
            page = self.confluence_fetcher.update_page(title=f"Meeting Notes: {name}", content=content)
            if page:
                return {"response": f"Created meeting notes page for {name}.", "sources": [page]}

        return {"response": "Failed to create document.", "sources": []}

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
                "tool_name": "list_open_bugs",
                "description": "List all open bugs.",
                "args": {}
            },
            {
                "tool_name": "filter_issues",
                "description": "Filter issues by assignee, project, or priority.",
                "args": {
                    "assignee": "Optional. The assignee's name.",
                    "project": "Optional. The project key.",
                    "priority": "Optional. The issue priority."
                }
            },
            {
                "tool_name": "get_sprint_details",
                "description": "Get details for a specific sprint.",
                "args": {
                    "sprint_name": "The name of the sprint."
                }
            },
            {
                "tool_name": "get_blocked_issues",
                "description": "Find blocked or high-priority tickets.",
                "args": {}
            },
            {
                "tool_name": "create_ticket",
                "description": "Create a new Jira ticket.",
                "args": {
                    "project_key": "The project key (e.g., 'PROJ').",
                    "summary": "The summary of the ticket.",
                    "description": "The description of the ticket.",
                    "issue_type": "Optional. The type of the issue (e.g., 'Task', 'Bug').",
                    "priority": "Optional. The priority of the issue.",
                    "labels": "Optional. A list of labels."
                }
            },
            {
                "tool_name": "update_ticket",
                "description": "Update an existing Jira ticket.",
                "args": {
                    "issue_key": "The Jira ticket key.",
                    "summary": "Optional. The new summary.",
                    "description": "Optional. The new description.",
                    "assignee": "Optional. The new assignee.",
                    "status": "Optional. The new status."
                }
            },
            {
                "tool_name": "add_comment",
                "description": "Add a comment to a Jira issue.",
                "args": {
                    "issue_key": "The Jira ticket key.",
                    "comment": "The comment to add."
                }
            },
            {
                "tool_name": "get_confluence_page",
                "description": "Retrieve Confluence documents by topic or keyword.",
                "args": {
                    "keyword": "The topic or keyword to search for."
                }
            },
            {
                "tool_name": "get_how_to_guides",
                "description": "Get step-by-step guides or SOPs.",
                "args": {}
            },
            {
                "tool_name": "get_policy_info",
                "description": "Retrieve company policies or processes.",
                "args": {}
            },
            {
                "tool_name": "get_architecture_doc",
                "description": "Fetch architecture or design documentation.",
                "args": {}
            },
            {
                "tool_name": "get_team_page",
                "description": "Access team pages or meeting notes.",
                "args": {
                    "team_name": "The name of the team to search for."
                }
            },
            {
                "tool_name": "get_onboarding_docs",
                "description": "Get onboarding or training pages.",
                "args": {}
            },
            {
                "tool_name": "get_page_history",
                "description": "Retrieve version/edit history of a Confluence page.",
                "args": {
                    "page_id": "The ID of the page."
                }
            },
            {
                "tool_name": "link_docs_to_ticket",
                "description": "Find Confluence pages linked to a specific Jira ticket.",
                "args": {
                    "issue_key": "The Jira ticket key."
                }
            },
            {
                "tool_name": "release_summary",
                "description": "List Jira issues in a release and link to release notes.",
                "args": {
                    "release_name": "The name of the release."
                }
            },
            {
                "tool_name": "incident_summary",
                "description": "Summarize incidents with corresponding postmortems.",
                "args": {
                    "incident_key": "The Jira ticket key of the incident."
                }
            },
            {
                "tool_name": "sprint_docs_summary",
                "description": "Combine sprint metrics with documentation references.",
                "args": {
                    "sprint_name": "The name of the sprint."
                }
            },
            {
                "tool_name": "auto_doc_creation",
                "description": "Auto-create Confluence release or meeting pages using Jira data.",
                "args": {
                    "project_key": "The Jira project key.",
                    "doc_type": "The type of document to create ('release' or 'meeting').",
                    "name": "The name of the release or meeting."
                }
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

    def get_confluence_documents_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve Confluence documents by topic or keyword."""
        return self.confluence_fetcher.get_documents_by_keyword(keyword, limit=limit)

    def get_confluence_how_to_guides(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get step-by-step guides or SOPs from Confluence."""
        return self.confluence_fetcher.get_how_to_guides(limit=limit)

    def get_confluence_policy_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve company policies or processes from Confluence."""
        return self.confluence_fetcher.get_policy_info(limit=limit)

    def get_confluence_architecture_docs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch architecture or design documentation from Confluence."""
        return self.confluence_fetcher.get_architecture_doc(limit=limit)

    def get_confluence_team_page(self, team_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Access team pages or meeting notes from Confluence."""
        return self.confluence_fetcher.get_team_page(team_name, limit=limit)

    def get_confluence_onboarding_docs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get onboarding or training pages from Confluence."""
        return self.confluence_fetcher.get_onboarding_docs(limit=limit)

    def get_confluence_page_history(self, page_id: str) -> List[Dict[str, Any]]:
        """Retrieve version/edit history of a Confluence page."""
        return self.confluence_fetcher.get_page_history(page_id)

    def link_docs_to_ticket(self, issue_key: str) -> List[Dict[str, Any]]:
        """Find Confluence pages linked to a specific Jira ticket."""
        issue = self.get_jira_issue(issue_key)
        return issue.get('linked_pages', []) if issue else []

    def release_summary(self, release_name: str) -> Dict[str, Any]:
        """List Jira issues in a release and link to release notes."""
        jql = f'fixVersion = "{release_name}"'
        issues = self.search_jira_issues(jql=jql)
        release_notes = self.confluence_fetcher.get_documents_by_keyword(f"Release Notes {release_name}", limit=1)
        return {"issues": issues, "release_notes": release_notes}

    def incident_summary(self, incident_key: str) -> Dict[str, Any]:
        """Summarize incidents with corresponding postmortems."""
        incident = self.get_jira_issue(incident_key)
        postmortems = self.confluence_fetcher.get_documents_by_keyword(f"Postmortem {incident_key}", limit=1)
        return {"incident": incident, "postmortems": postmortems}

    def sprint_docs_summary(self, sprint_name: str) -> Dict[str, Any]:
        """Combine sprint metrics with documentation references."""
        sprint = self.jira_fetcher.get_sprint_by_name(sprint_name)
        if not sprint:
            return {"sprint": None, "issues": [], "docs": []}
        issues = self.jira_fetcher.get_issues_for_sprint(sprint['id'])
        docs = self.confluence_fetcher.get_documents_by_keyword(sprint_name)
        return {"sprint": sprint, "issues": issues, "docs": docs}

    def auto_doc_creation(self, project_key: str, doc_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Auto-create Confluence release or meeting pages using Jira data."""
        if doc_type == "release":
            jql = f'project = "{project_key}" AND fixVersion = "{name}"'
            issues = self.search_jira_issues(jql=jql)
            content = "<h1>Release Notes</h1>\n<ul>"
            for issue in issues:
                content += f"<li>{issue['key']}: {issue['title']}</li>"
            content += "</ul>"
            
            # Here we'd ideally create a new page, but Confluence API lib doesn't support it well.
            # We'll simulate by updating a placeholder page. A real implementation would need `create_page`.
            # For now, let's just return the content that would be created.
            return {"title": f"Release Notes: {name}", "content": content}

        elif doc_type == "meeting":
            content = "<h1>Meeting Notes</h1>\n<h2>Attendees</h2>\n<p></p>\n<h2>Agenda</h2>\n<p></p>\n<h2>Notes</h2>\n<p></p>"
            return {"title": f"Meeting Notes: {name}", "content": content}

        return None

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
