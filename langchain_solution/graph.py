"""Defines the LangGraph agent and its workflow."""

import json
from typing import List, Dict, Any, TypedDict
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from langchain_solution.tools import (
    get_issue_status,
    get_assignee,
    summarize_issue,
    list_high_priority_tickets,
    list_open_bugs,
    rag_search,
)
from langchain_solution.services import llm_client

# Define the state for the graph
class AgentState(TypedDict):
    messages: List[BaseMessage]

# Define the tools for the agent
tools = [
    get_issue_status,
    get_assignee,
    summarize_issue,
    list_high_priority_tickets,
    list_open_bugs,
    rag_search,
]
tool_node = ToolNode(tools)

# Define the agent model
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. Use the provided tools to answer the user's questions.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
model = llm_client.bind_tools(tools)

# Define the nodes for the graph
def should_continue(state: AgentState) -> str:
    """Determines whether to continue with another tool call or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    return "continue"

def call_model(state: AgentState) -> Dict[str, Any]:
    """Calls the model to get the next action."""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

# Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.add_conditional_edge(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")
workflow.set_entry_point("agent")

# Compile the graph
app = workflow.compile()
