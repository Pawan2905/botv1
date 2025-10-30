import os
import sys
from typing import Dict, Any, Optional

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetchers.jira_fetcher import JiraFetcher
from config import settings

def get_jira_ticket_details(ticket_key: str) -> None:
    """
    Fetches and displays the details of a specific Jira ticket.

    Args:
        ticket_key: The key of the Jira ticket (e.g., "PROJ-133").
    """
    print(f"Attempting to fetch details for Jira ticket '{ticket_key}'...")

    try:
        # Initialize the Jira fetcher from settings
        fetcher = JiraFetcher(
            url=settings.jira_url,
            username=settings.jira_username,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key
        )

        # Fetch the ticket by its key
        ticket: Optional[Dict[str, Any]] = fetcher.fetch_issue_by_key(ticket_key)

        if not ticket:
            print(f"Could not find Jira ticket with key '{ticket_key}'.")
            return

        print("\n--- Jira Ticket Details ---")
        print(f"Key: {ticket.get('key')}")
        print(f"Title: {ticket.get('title')}")
        print("\nObjective/Description:")
        print(ticket.get('description', 'No description provided.'))
        print("\n--------------------------")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure your .env file is correctly configured with Jira credentials.")

if __name__ == "__main__":
    # The ticket key provided in the user's request
    jira_ticket_key = "PROJ-133"
    get_jira_ticket_details(jira_ticket_key)
