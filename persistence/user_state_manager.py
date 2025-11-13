"""
Manages user state and conversation history persistence.
This implementation uses ChromaDB for storing conversation history and
local JSON files for other user-specific data, without relying on langgraph.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import uuid
import time

from config import settings
from storage.chroma_store import ChromaStore
from storage.embeddings import AzureOpenAIEmbeddings

logger = logging.getLogger(__name__)

STATE_DIR = Path(__file__).parent / "user_states"
STATE_DIR.mkdir(exist_ok=True)

# Initialize ChromaDB for user history
try:
    history_store = ChromaStore(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.chroma_user_history_collection_name,
    )
    embedding_function = AzureOpenAIEmbeddings(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment_name=settings.azure_openai_embedding_deployment_name,
        api_version=settings.azure_openai_api_version,
        use_apim=settings.use_apim
    )
    logger.info("ChromaDB for user history initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB for user history: {e}")
    history_store = None

def get_state_filepath(user_id: str) -> Path:
    """Gets the file path for a user's state file."""
    return STATE_DIR / f"{user_id}_state.json"

def load_user_state(user_id: str) -> Dict[str, Any]:
    """
    Loads a user's state, fetching history from ChromaDB and other data from a JSON file.
    """
    filepath = get_state_filepath(user_id)
    if filepath.exists():
        with open(filepath, "r") as f:
            state = json.load(f)
    else:
        state = {"user_id": user_id}

    # Fetch history from ChromaDB
    history: List[Dict[str, Any]] = []
    if history_store:
        try:
            results = history_store.collection.get(
                where={"user_id": user_id},
                include=["documents", "metadatas"]
            )
            
            # Sort by timestamp
            sorted_items = sorted(zip(results['documents'], results['metadatas']), key=lambda item: item[1].get('timestamp', 0))

            for doc, meta in sorted_items:
                history.append(json.loads(doc))
        except Exception as e:
            logger.error(f"Error loading history for user {user_id} from ChromaDB: {e}")

    state["history"] = history
    return state

def save_user_state(user_id: str, state: Dict[str, Any]):
    """
    Saves a user's state, storing history in ChromaDB and other data in a JSON file.
    """
    # Save non-history state to JSON
    filepath = get_state_filepath(user_id)
    state_to_save = {k: v for k, v in state.items() if k != "history"}
    with open(filepath, "w") as f:
        json.dump(state_to_save, f, indent=2)

    # Save the latest interaction to ChromaDB
    if history_store and state.get("history"):
        try:
            latest_message = state["history"][-1]
            
            doc_id = f"{user_id}_{uuid.uuid4().hex}"
            document = json.dumps(latest_message)
            metadata = {
                "user_id": user_id,
                "timestamp": time.time(),
                "role": latest_message.get("role")
            }
            
            embedding = embedding_function.embed_documents([latest_message.get("content", "")])[0]

            history_store.collection.add(
                ids=[doc_id],
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.error(f"Error saving history for user {user_id} to ChromaDB: {e}")
