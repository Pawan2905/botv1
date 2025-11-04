"""
Microsoft Teams Adapter for the LangGraph-based RAG Bot.
"""

import os
import aiohttp
from dotenv import load_dotenv
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from langgraph_integration.graph import app
from langgraph_integration.state import AgentState
from langgraph_integration.persistence import load_user_state, save_user_state

# Load environment variables
load_dotenv()

APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

# --- Bot Framework Adapter Setup ---
# The BotFrameworkAdapter can be initialized without a password for local testing.
SETTINGS = BotFrameworkAdapterSettings(app_id=APP_ID, app_password=APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

async def on_turn_error(context: TurnContext, error: Exception):
    """
    Error handler for the bot.
    """
    print(f"\n [on_turn_error] unhandled error: {error}")
    await context.send_activity("Sorry, it looks like something went wrong.")

ADAPTER.on_turn_error = on_turn_error

async def handle_message(context: TurnContext):
    """
    Main message handler for incoming messages.
    """
    if context.activity.type == ActivityTypes.message:
        user_id = context.activity.from_property.id
        team_id = context.activity.conversation.id
        user_message = context.activity.text

        # Load user state from file
        current_state = load_user_state(user_id, team_id)
        current_state['history'].append(f"user: {user_message}")

        # Invoke the LangGraph app
        final_state = await app.ainvoke(current_state)
        
        # Save the updated state to file
        save_user_state(user_id, final_state)

        bot_response = final_state['history'][-1]

        await context.send_activity(bot_response)

async def messages(req: web.Request) -> web.Response:
    """
    Endpoint for receiving messages from the Bot Framework.
    """
    if "application/json" not in req.headers.get("Content-Type", ""):
        return web.Response(status=415)

    body = await req.json()
    activity = Activity().deserialize(body)
    
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""
    
    try:
        response = await ADAPTER.process_activity(activity, auth_header, handle_message)
        if response:
            return web.json_response(response.body, status=response.status)
        return web.Response(status=201)
    except Exception as e:
        print(f"Error processing activity: {e}")
        return web.Response(status=500)

# --- Web Application Setup ---
app_web = web.Application()
app_web.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        host = os.environ.get("HOST", "localhost")
        port = int(os.environ.get("PORT", 3978))
        print(f"LangGraph Teams Adapter is running on http://{host}:{port}")
        web.run_app(app_web, host=host, port=port)
    except Exception as error:
        raise error
