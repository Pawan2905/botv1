"""Jira data fetcher with authentication and JQL support."""

import logging
from typing import List, Dict, Any, Optional
from jira import JIRA
from datetime import datetime

logger = logging.getLogger(__name__)


class JiraFetcher:
    """Fetches issues and data from Jira."""
    
    def __init__(
        self,
        url: str,
        username: str,
        api_token: str,
        project_key: Optional[str] = None
    ):
        """
        Initialize Jira fetcher.
        
        Args:
            url: Jira instance URL
            username: Jira username/email
            api_token: Jira API token
            project_key: Optional project key to filter issues
        """
        try:
            self.jira = JIRA(
                server=url,
                basic_auth=(username, api_token)  # For Jira Cloud, api_token is used as password
            )
            self.project_key = project_key
            self.url = url
            logger.info(f"Initialized Jira fetcher for {url}")
            
            # Test connection
            self.jira.current_user()
            logger.info("Jira connection test successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize Jira connection: {e}")
            raise
    
    def fetch_all_issues(self, jql: Optional[str] = None, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch all issues matching the JQL query.
        
        Args:
            jql: JQL query string (optional)
            max_results: Maximum number of results to fetch
            
        Returns:
            List of issue dictionaries with content and metadata
        """
        if jql is None:
            if self.project_key:
                jql = f"project = {self.project_key} ORDER BY updated DESC"
            else:
                jql = "ORDER BY updated DESC"
        
        try:
            issues = []
            start_at = 0
            batch_size = 100
            
            while start_at < max_results:
                batch = self.jira.search_issues(
                    jql,
                    startAt=start_at,
                    maxResults=batch_size,
                    expand="changelog,renderedFields"
                )
                
                if not batch:
                    break
                
                for issue in batch:
                    processed_issue = self._process_issue(issue)
                    if processed_issue:
                        issues.append(processed_issue)
                        logger.info(f"Fetched issue: {processed_issue['key']}")
                
                if len(batch) < batch_size:
                    break
                
                start_at += batch_size
            
            logger.info(f"Successfully fetched {len(issues)} issues from Jira")
            return issues
            
        except Exception as e:
            logger.error(f"Error fetching Jira issues: {e}")
            raise
    
    def fetch_issue_by_key(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific issue by key.
        
        Args:
            issue_key: Jira issue key (e.g., PROJ-123)
            
        Returns:
            Issue dictionary with content and metadata
        """
        try:
            issue = self.jira.issue(issue_key, expand="changelog,renderedFields")
            return self._process_issue(issue)
        except Exception as e:
            logger.error(f"Error fetching issue {issue_key}: {e}")
            return None
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Jira issue.
        
        Args:
            project_key: Project key
            summary: Issue summary
            description: Issue description
            issue_type: Issue type (Task, Bug, Story, etc.)
            **kwargs: Additional fields
            
        Returns:
            Created issue dictionary
        """
        try:
            issue_dict = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type}
            }
            
            # Add additional fields
            issue_dict.update(kwargs)
            
            new_issue = self.jira.create_issue(fields=issue_dict)
            logger.info(f"Created issue: {new_issue.key}")
            
            return self._process_issue(new_issue)
            
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None
    
    def update_issue(
        self,
        issue_key: str,
        **fields
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing Jira issue.
        
        Args:
            issue_key: Issue key to update
            **fields: Fields to update
            
        Returns:
            Updated issue dictionary
        """
        try:
            issue = self.jira.issue(issue_key)
            issue.update(fields=fields)
            logger.info(f"Updated issue: {issue_key}")
            
            # Fetch updated issue
            return self.fetch_issue_by_key(issue_key)
            
        except Exception as e:
            logger.error(f"Error updating issue {issue_key}: {e}")
            return None
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """
        Add a comment to an issue.
        
        Args:
            issue_key: Issue key
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.jira.add_comment(issue_key, comment)
            logger.info(f"Added comment to issue: {issue_key}")
            return True
        except Exception as e:
            logger.error(f"Error adding comment to {issue_key}: {e}")
            return False
    
    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """
        Transition an issue to a new status.
        
        Args:
            issue_key: Issue key
            transition_name: Name of the transition (e.g., "Done", "In Progress")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            transitions = self.jira.transitions(issue_key)
            transition_id = None
            
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break
            
            if transition_id:
                self.jira.transition_issue(issue_key, transition_id)
                logger.info(f"Transitioned issue {issue_key} to {transition_name}")
                return True
            else:
                logger.warning(f"Transition '{transition_name}' not found for {issue_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error transitioning issue {issue_key}: {e}")
            return False
    
    def _process_issue(self, issue: Any) -> Optional[Dict[str, Any]]:
        """
        Process and clean a Jira issue.
        
        Args:
            issue: Raw issue data from Jira API
            
        Returns:
            Processed issue dictionary
        """
        try:
            fields = issue.fields
            
            # Build comprehensive content for embedding
            content_parts = [
                f"Summary: {fields.summary}",
                f"Description: {fields.description or 'No description'}",
                f"Status: {fields.status.name}",
                f"Priority: {fields.priority.name if fields.priority else 'None'}",
                f"Issue Type: {fields.issuetype.name}",
            ]
            
            # Add comments
            if hasattr(fields, 'comment') and fields.comment.comments:
                comments_text = "\n".join([
                    f"Comment by {c.author.displayName}: {c.body}"
                    for c in fields.comment.comments
                ])
                content_parts.append(f"Comments:\n{comments_text}")
            
            content = "\n\n".join(content_parts)
            
            # Get linked Confluence pages
            linked_pages = self.get_issue_links(issue.key)

            return {
                "id": issue.id,
                "key": issue.key,
                "title": fields.summary,
                "content": content,
                "description": fields.description or "",
                "url": f"{self.url}/browse/{issue.key}",
                "project": fields.project.key,
                "issue_type": fields.issuetype.name,
                "status": fields.status.name,
                "priority": fields.priority.name if fields.priority else None,
                "assignee": fields.assignee.displayName if fields.assignee else None,
                "reporter": fields.reporter.displayName if fields.reporter else None,
                "created": fields.created,
                "updated": fields.updated,
                "labels": fields.labels or [],
                "components": [c.name for c in fields.components] if fields.components else [],
                "linked_pages": linked_pages,
                "type": "jira",
                "source": "jira"
            }
        except Exception as e:
            logger.error(f"Error processing issue: {e}")
            return None
    
    def search_issues(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search issues using text search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of matching issues
        """
        jql = f'text ~ "{query}" ORDER BY updated DESC'
        return self.fetch_all_issues(jql=jql, max_results=max_results)

    def get_sprint_by_name(self, sprint_name: str) -> Optional[Dict[str, Any]]:
        """
        Get sprint details by name.
        
        Args:
            sprint_name: The name of the sprint.
            
        Returns:
            Sprint details dictionary.
        """
        try:
            boards = self.jira.boards()
            for board in boards:
                sprints = self.jira.sprints(board.id)
                for sprint in sprints:
                    if sprint.name == sprint_name:
                        return {
                            "id": sprint.id,
                            "name": sprint.name,
                            "startDate": sprint.startDate,
                            "endDate": sprint.endDate,
                            "state": sprint.state,
                        }
            return None
        except Exception as e:
            logger.error(f"Error fetching sprint '{sprint_name}': {e}")
            return None

    def get_issues_for_sprint(self, sprint_id: int) -> List[Dict[str, Any]]:
        """
        Get all issues for a given sprint.
        
        Args:
            sprint_id: The ID of the sprint.
            
        Returns:
            List of issues in the sprint.
        """
        try:
            issues = self.jira.search_issues(f'sprint = {sprint_id}')
            return [self._process_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Error fetching issues for sprint {sprint_id}: {e}")
            return []

    def get_issue_links(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get all remote links for a given issue.
        
        Args:
            issue_key: The key of the issue.
            
        Returns:
            List of remote links.
        """
        try:
            issue = self.jira.issue(issue_key)
            remote_links = self.jira.remote_links(issue)
            
            links = []
            for link in remote_links:
                if 'confluence' in link.object.url:
                    links.append({
                        "id": link.id,
                        "url": link.object.url,
                        "title": link.object.title,
                    })
            return links
        except Exception as e:
            logger.error(f"Error fetching links for issue {issue_key}: {e}")
            return []
