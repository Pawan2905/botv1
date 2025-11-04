import os
import aiohttp
from langgraph.graph import StateGraph, END
from langgraph_integration.state import AgentState

RAG_BOT_API_URL = os.environ.get("RagBotApiUrl", "http://localhost:8000/chat")

async def invoke_rag_bot(state: AgentState):
    """
    Invokes the RAG bot API to get a response, checking the cache first.
    """
    user_message = state['history'][-1]

    # Check cache first
    if user_message in state.get('cache', {}):
        bot_response = state['cache'][user_message]
        return {"history": state['history'] + [f"assistant: {bot_response} (cached)"]}

    payload = {"message": user_message, "use_jira_live": True}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(RAG_BOT_API_URL, json=payload) as resp:
            if resp.status == 200:
                response_data = await resp.json()
                bot_response = response_data.get("response", "I'm not sure how to answer that.")
            else:
                bot_response = f"Error: Could not reach the RAG bot. Status: {resp.status}"
    
    # Update cache
    new_cache = state.get('cache', {}).copy()
    new_cache[user_message] = bot_response
    
    return {"history": state['history'] + [f"assistant: {bot_response}"], "cache": new_cache}

def should_continue(state: AgentState):
    """
    Determines whether the conversation should continue.
    """
    if len(state['history']) > 10:  # Increased limit
        return "end"
    return "continue"

# Define the workflow
workflow = StateGraph(AgentState)

workflow.add_node("invoke_rag_bot", invoke_rag_bot)

workflow.set_entry_point("invoke_rag_bot")

workflow.add_conditional_edges(
    "invoke_rag_bot",
    should_continue,
    {
        "continue": END,  # For now, the graph ends after one turn
        "end": END
    }
)

app = workflow.compile()
