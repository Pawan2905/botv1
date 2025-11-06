"""Defines the tools available to the LangGraph agent."""

from typing import List, Optional
from langchain_core.tools import tool
from langchain_solution.services import (
    jira_fetcher,
    confluence_fetcher,
    retriever,
    llm_client
)

@tool
def get_issue_status(issue_key: str) -> dict:
    """Get the status of a specific Jira ticket."""
    issue = jira_fetcher.fetch_issue_by_key(issue_key)
    if issue and issue.get('status'):
        return {"response": f"The status of ticket {issue_key} is '{issue['status']}'.", "sources": [issue]}
    return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

@tool
def get_assignee(issue_key: str) -> dict:
    """Find out who is assigned to a specific Jira ticket."""
    issue = jira_fetcher.fetch_issue_by_key(issue_key)
    if issue and issue.get('assignee'):
        return {"response": f"The assignee of {issue_key} is {issue['assignee']}.", "sources": [issue]}
    elif issue:
        return {"response": f"{issue_key} is currently unassigned.", "sources": [issue]}
    return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

@tool
def summarize_issue(issue_key: str, length_constraint: Optional[str] = None, focus: Optional[str] = None) -> dict:
    """Summarize a Jira ticket with optional constraints."""
    issue = jira_fetcher.fetch_issue_by_key(issue_key)
    if not issue:
        return {"response": f"Sorry, I could not find the ticket {issue_key}.", "sources": []}

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

    response = llm_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )
    
    summary = response.choices[0].message.content
    return {"response": summary, "sources": [issue]}

@tool
def list_high_priority_tickets() -> dict:
    """List all high-priority tickets."""
    jql = "priority in (High, Highest) ORDER BY updated DESC"
    issues = jira_fetcher.fetch_all_issues(jql=jql, max_results=5)
    if issues:
        response_text = "Here are the top 5 high priority tickets:\n"
        for issue in issues:
            response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
        return {"response": response_text, "sources": issues}
    return {"response": "I couldn't find any high priority tickets.", "sources": []}

@tool
def list_open_bugs() -> dict:
    """List all open bugs."""
    jql = "issuetype = Bug AND status != Done ORDER BY updated DESC"
    issues = jira_fetcher.fetch_all_issues(jql=jql, max_results=10)
    if issues:
        response_text = "Here are the top 10 open bugs:\n"
        for issue in issues:
            response_text += f"- {issue['key']}: {issue['title']} (Status: {issue['status']})\n"
        return {"response": response_text, "sources": issues}
    return {"response": "I couldn't find any open bugs.", "sources": []}

@tool
def rag_search(query: str, top_k: int = 5) -> dict:
    """Perform a general search over the knowledge base (Confluence and Jira)."""
    results = retriever.retrieve(query=query, top_k=top_k, method="hybrid")
    context = "\n".join([f"[Source {i+1}]\n{r.get('content', '')}" for i, r in enumerate(results)])
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Use the provided context to answer questions accurately."},
        {"role": "user", "content": f"Context:\n\n{context}\n\nUser question: {query}"}
    ]
    
    response = llm_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )
    
    answer = response.choices[0].message.content
    sources = [{"title": r.get("metadata", {}).get("doc_title", "Unknown"), "url": r.get("metadata", {}).get("doc_url", ""), "type": r.get("metadata", {}).get("doc_type", "unknown"), "score": r.get("score", 0)} for r in results]
    
    return {"response": answer, "sources": sources}
