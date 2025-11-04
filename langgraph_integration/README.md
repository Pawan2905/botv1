# LangGraph Integration for Microsoft Teams

This directory contains the implementation of a Microsoft Teams bot that uses LangGraph to manage conversations.

## Overview

The integration is composed of three main files:

- `state.py`: Defines the `AgentState` TypedDict, which represents the state of the conversation.
- `graph.py`: Defines the LangGraph workflow, including the nodes and edges that control the conversation flow.
- `teams_integration.py`: The Microsoft Teams adapter, which connects to the Bot Framework and uses the LangGraph app to handle messages.

## How it Works

1. The `teams_integration.py` script receives a message from a user in Microsoft Teams.
2. It loads the user's current state from a JSON file in the `langgraph_integration/user_states` directory. If no state file exists, a new one is created.
3. The user's message is added to the state's history.
4. The `app.ainvoke()` method from `graph.py` is called with the current state.
5. The LangGraph workflow processes the input and generates a response.
6. The updated state is saved back to the user's JSON file, and the response is sent to the user in Teams.

## Chat History Persistence

The chat history is stored on the local filesystem in the `langgraph_integration/user_states` directory. Each user has their own JSON file, named with their user ID. This ensures that conversation history is preserved between sessions.

## Running the Integration

To run the LangGraph-based Teams bot, you need to have both the main RAG bot and the LangGraph Teams adapter running.

1. **Start the RAG bot:**
   ```bash
   python run.py
   ```

2. **Start the LangGraph Teams adapter:**
   ```bash
   python -m langgraph_integration.teams_integration
   ```

Make sure you have the required environment variables set up in your `.env` file. `MicrosoftAppId` and `RagBotApiUrl` are required. `MicrosoftAppPassword` is optional for local testing but required for production deployment.

### Port Configuration

The Teams adapter runs on the port specified by the `PORT` environment variable, defaulting to `3978`. If your service is running on a different port (e.g., 3687), ensure that you update your bot's messaging endpoint in the Azure Bot registration or your Bot Framework Emulator settings to match. The endpoint will be `http://localhost:<PORT>/api/messages`.
