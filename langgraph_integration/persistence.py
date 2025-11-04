import json
import logging
from pathlib import Path
from typing import List
from langgraph.schema import BaseMessage
from langgraph_integration.state import AgentState
from storage.chroma_store import ChromaStore
from storage.embeddings import get_embedding_function
from config import settings
import uuid

logger = logging.getLogger(__name__)

STATE_DIR = Path(__file__).parent / "user_states"
STATE_DIR.mkdir(exist_ok=True)

# Initialize ChromaDB for user history
try:
    embedding_function = get_embedding_function()
    history_store = ChromaStore(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.chroma_user_history_collection_name,
        embedding_function=embedding_function
    )
    logger.info("ChromaDB for user history initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB for user history: {e}")
    history_store = None

def get_state_filepath(user_id: str) -> Path:
    """Gets the file path for a user's state (excluding history)."""
    return STATE_DIR / f"{user_id}_state.json"

def load_user_state(user_id: str, team_id: str) -> AgentState:
    """
    Loads a user's state, fetching history from ChromaDB and the rest from a JSON file.
    """
    # Load non-history state from JSON
    filepath = get_state_filepath(user_id)
    if filepath.exists():
        with open(filepath, "r") as f:
            data = json.load(f)
    else:
        data = {}

    # Fetch history from ChromaDB
    history: List[BaseMessage] = []
    if history_store:
        try:
            # Query ChromaDB for the user's history, sorted by timestamp
            results = history_store.collection.get(
                where={"user_id": user_id},
                include=["documents", "metadatas"]
            )
            
            # Sort by timestamp
            sorted_items = sorted(zip(results['documents'], results['metadatas']), key=lambda item: item[1].get('timestamp', 0))

            # Deserialize history
            for doc, meta in sorted_items:
                history.append(BaseMessage(**json.loads(doc)))

        except Exception as e:
            logger.error(f"Error loading history for user {user_id} from ChromaDB: {e}")

    return AgentState(
        history=history,
        context=data.get("context", ""),
        user_id=data.get("user_id", user_id),
        team_id=data.get("team_id", team_id),
        cache=data.get("cache", {}),
    )

def save_user_state(user_id: str, state: AgentState):
    """
    Saves a user's state, storing history in ChromaDB and the rest in a JSON file.
    """
    # Save non-history state to JSON
    filepath = get_state_filepath(user_id)
    state_to_save = {
        "context": state.get("context", ""),
        "user_id": user_id,
        "team_id": state.get("team_id", ""),
        "cache": state.get("cache", {}),
    }
    with open(filepath, "w") as f:
        json.dump(state_to_save, f, indent=2)

    # Save the latest interaction to ChromaDB
    if history_store and state.get("history"):
        try:
            latest_message = state["history"][-1]
            
            # Create a document to store
            doc_id = f"{user_id}_{uuid.uuid4().hex}"
            document = latest_message.json()
            metadata = {
                "user_id": user_id,
                "team_id": state.get("team_id", ""),
                "timestamp": latest_message.additional_kwargs.get("timestamp", 0),
                "type": latest_message.type
            }
            
            # Generate embedding for the message content
            embedding = embedding_function([latest_message.content])[0]

            history_store.collection.add(
                ids=[doc_id],
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.error(f"Error saving history for user {user_id} to ChromaDB: {e}")
            pass # Fix for expected indented block
