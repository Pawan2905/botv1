import json
from pathlib import Path
from langgraph_integration.state import AgentState

STATE_DIR = Path(__file__).parent / "user_states"
STATE_DIR.mkdir(exist_ok=True)

def get_state_filepath(user_id: str) -> Path:
    """Gets the file path for a user's state."""
    return STATE_DIR / f"{user_id}.json"

def load_user_state(user_id: str, team_id: str) -> AgentState:
    """Loads a user's state from a JSON file."""
    filepath = get_state_filepath(user_id)
    if filepath.exists():
        with open(filepath, "r") as f:
            data = json.load(f)
            return AgentState(
                history=data.get("history", []),
                context=data.get("context", ""),
                user_id=data.get("user_id", user_id),
                team_id=data.get("team_id", team_id),
            )
    return AgentState(history=[], context="", user_id=user_id, team_id=team_id)

def save_user_state(user_id: str, state: AgentState):
    """Saves a user's state to a JSON file."""
    filepath = get_state_filepath(user_id)
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2)
