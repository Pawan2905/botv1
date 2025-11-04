from typing import List, TypedDict

class AgentState(TypedDict):
    """
    Represents the state of the LangGraph agent.
    """
    history: List[str]
    context: str
    user_id: str
    team_id: str
