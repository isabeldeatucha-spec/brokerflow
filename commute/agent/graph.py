import os
from datetime import datetime, timezone
from typing import Annotated, TypedDict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from commute.agent.prompts import SYSTEM_PROMPT
from commute.agent.tools import ALL_TOOLS
from commute.data import google_maps as gm_module
from commute.data import outlook as outlook_module


class CommuteState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    home_address: str
    origin_lat: float
    origin_lon: float
    buffer_minutes: int
    user_email: str
    next_event: Optional[dict]
    recommendation: Optional[str]


def _build_llm():
    model = os.getenv("COMMUTE_LLM_MODEL", "claude-sonnet-4-6")
    return ChatAnthropic(model=model, temperature=0).bind_tools(ALL_TOOLS)


llm = _build_llm()


def geocode_node(state: CommuteState) -> dict:
    address = state["home_address"]
    coords = gm_module.geocode_address(address)
    if coords:
        lat, lon = coords
    else:
        lat, lon = 42.3601, -71.0942

    return {"origin_lat": lat, "origin_lon": lon}


def fetch_outlook_node(state: CommuteState) -> dict:
    try:
        event = outlook_module.get_next_mit_event(state.get("user_email") or None)
        return {"next_event": event}
    except Exception:
        return {"next_event": None}


def agent_node(state: CommuteState) -> dict:
    now = datetime.now().strftime("%A, %B %d %Y at %I:%M %p")
    origin = state["home_address"]
    lat = state.get("origin_lat", 0.0)
    lon = state.get("origin_lon", 0.0)
    buffer = state.get("buffer_minutes", 15)
    event = state.get("next_event")

    event_context = ""
    if event:
        event_context = (
            f"\nNext MIT Sloan event: '{event['subject']}' at {event['start_str']}"
            f"\nLocation: {event.get('location', 'MIT Sloan')}"
            f"\nYou need to arrive {buffer} minutes early → by {event.get('arrival_needed_str', 'TBD')}."
        )
    else:
        event_context = f"\nNo Outlook event found. Plan to arrive at MIT Sloan with {buffer}min buffer."

    user_message = (
        f"Current time: {now}\n"
        f"Home address: {origin} (coordinates: {lat:.4f}, {lon:.4f})\n"
        f"Buffer time: {buffer} minutes{event_context}\n\n"
        "Please gather real-time data from all available sources (MBTA, Bluebike, MIT Shuttle, "
        "Google Maps, Apple Maps) and recommend the best way to get to MIT Sloan right now."
    )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]
    response = llm.invoke(messages + state.get("messages", []))
    return {"messages": [response]}


def tools_node_handler(state: CommuteState) -> dict:
    tool_node = ToolNode(ALL_TOOLS)
    return tool_node.invoke(state)


def should_continue(state: CommuteState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "finalize"


def finalize_node(state: CommuteState) -> dict:
    last = state["messages"][-1]
    recommendation = last.content if isinstance(last.content, str) else str(last.content)
    return {"recommendation": recommendation}


def build_graph() -> StateGraph:
    g = StateGraph(CommuteState)

    g.add_node("geocode", geocode_node)
    g.add_node("fetch_outlook", fetch_outlook_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(ALL_TOOLS))
    g.add_node("finalize", finalize_node)

    g.set_entry_point("geocode")
    g.add_edge("geocode", "fetch_outlook")
    g.add_edge("fetch_outlook", "agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", "finalize": "finalize"})
    g.add_edge("tools", "agent")
    g.add_edge("finalize", END)

    return g.compile()


commute_graph = build_graph()


def plan_commute(
    home_address: str,
    buffer_minutes: int = 15,
    user_email: str = "",
) -> dict:
    initial_state: CommuteState = {
        "messages": [],
        "home_address": home_address,
        "origin_lat": 0.0,
        "origin_lon": 0.0,
        "buffer_minutes": buffer_minutes,
        "user_email": user_email,
        "next_event": None,
        "recommendation": None,
    }
    result = commute_graph.invoke(initial_state)
    return result
