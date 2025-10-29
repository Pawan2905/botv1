"""
Microsoft Teams Adapter for the RAG Bot.

This script acts as a bridge between the Microsoft Bot Framework (used by Teams)
and the existing FastAPI-based RAG bot. It receives messages from Teams,
forwards them to the RAG bot's /chat endpoint, and sends the response back to the user.
"""

import os
import aiohttp
import json
from dotenv import load_dotenv
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# These settings are required for the Bot Framework to authenticate requests.
# You will get these values when you register your bot in the Azure portal.
APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

# The URL of your running RAG bot API.
RAG_BOT_API_URL = os.environ.get("RagBotApiUrl", "http://localhost:8000/chat")

# --- Bot Framework Adapter Setup ---
SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)


async def on_turn_error(context: TurnContext, error: Exception):
    """
    Error handler for the bot. Logs errors and sends a notification to the user.
    """
    print(f"\n [on_turn_error] unhandled error: {error}")
    await context.send_activity("Sorry, it looks like something went wrong.")

ADAPTER.on_turn_error = on_turn_error


async def handle_message(context: TurnContext):
    """
    Main message handler. Called for every message received from the user.
    """
    if context.activity.type == ActivityTypes.message:
        user_message = context.activity.text
        
        # Prepare the request for the RAG bot's /chat endpoint
        payload = {
            "message": user_message,
            "use_jira_live": True  # Enable agentic features
        }
        
        try:
            # Call the RAG bot API
            async with aiohttp.ClientSession() as session:
                async with session.post(RAG_BOT_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        response_data = await resp.json()
                        bot_response = response_data.get("response", "I'm not sure how to answer that.")
                        
                        # Format sources for display in Teams
                        sources = response_data.get("sources", [])
                        if sources:
                            source_links = []
                            for i, source in enumerate(sources[:3]): # Show top 3 sources
                                title = source.get('title', 'Unknown Source')
                                url = source.get('url')
                                if url:
                                    source_links.append(f"{i+1}. [{title}]({url})")
                            
                            if source_links:
                                bot_response += "\n\n**Sources:**\n" + "\n".join(source_links)
                    else:
                        bot_response = f"Error: Could not reach the RAG bot. Status: {resp.status}"
        
        except Exception as e:
            print(f"Error calling RAG bot API: {e}")
            bot_response = "Sorry, I'm having trouble connecting to my knowledge base."

        # Send the final response back to the user in Teams
        await context.send_activity(bot_response)


async def messages(req: web.Request) -> web.Response:
    """
    The main endpoint that receives messages from the Bot Framework.
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
app = web.Application()
app.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        # Get host and port from environment variables for App Service compatibility
        host = os.environ.get("HOST", "localhost")
        port = int(os.environ.get("PORT", 3978))
        print(f"Teams Adapter is running on http://{host}:{port}")
        web.run_app(app, host=host, port=port)
    except Exception as error:
        raise error
