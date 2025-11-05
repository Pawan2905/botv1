"""
Test script for the new persistence layer.
This script verifies that the user state can be saved and loaded correctly
using the new user_state_manager.
"""

import logging
import os
import sys
import time

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence.user_state_manager import save_user_state, load_user_state

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_persistence():
    """
    Tests the new persistence layer by saving and loading a user state.
    """
    logging.info("Starting persistence layer test...")

    user_id = "test_user_123"
    sample_state = {
        "user_id": user_id,
        "some_data": "some_value",
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    }

    # 1. Save the user state
    try:
        logging.info(f"Saving state for user: {user_id}")
        save_user_state(user_id, sample_state)
        logging.info("User state saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save user state: {e}")
        return

    # 2. Load the user state
    try:
        logging.info(f"Loading state for user: {user_id}")
        loaded_state = load_user_state(user_id)
        logging.info("User state loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load user state: {e}")
        return

    # 3. Verify the loaded state
    assert loaded_state["user_id"] == user_id
    assert loaded_state["some_data"] == "some_value"
    assert len(loaded_state["history"]) == 2
    assert loaded_state["history"][0]["content"] == "Hello"

    logging.info("State verification successful.")
    logging.info("Persistence layer test completed successfully.")


if __name__ == "__main__":
    test_persistence()
