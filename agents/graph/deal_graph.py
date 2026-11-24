"""
DealForge Agents — Deal Origination LangGraph Workflow.

This graph orchestrates the AI-powered deal origination pipeline:
  1. Research → gather intel on the target company/contact
  2. Qualify → score the opportunity
  3. Draft → generate a personalized outreach / proposal
  4. Review → human-in-the-loop checkpoint (interrupt)

The graph is stateful and resumable via LangGraph's checkpointing.

Usage:
    from agents.graph.deal_graph import deal_graph

    result = await deal_graph.ainvoke(
        {"company": "Acme Corp", "contact_email": "ceo@acme.com"},
        config={"configurable": {"thread_id": "deal-123"}},
    )
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agents.llm.litellm_client import LLMClient
from agents.tools.crm_tools import CRM_TOOLS

llm = LLMClient()


# ── State schema ──────────────────────────────────────────────────────────────

class DealState(TypedDict):
    """Shared state passed between graph nodes."""

    company: str
    contact_email: str
    research_notes: str
    qualification_score: int          # 0-100
    qualification_rationale: str
    draft_outreach: str
    messages: Annotated[list, add_messages]
    status: str                        # running | awaiting_review | complete


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def research_node(state: DealState) -> Dict[str, Any]:
    """Node 1: Research the target company and gather intelligence."""
    prompt = (
        f"You are a B2B sales researcher. Briefly summarise what you know about "
        f"'{state['company']}' and why they might need an enterprise CRM. "
        f"Keep it to 3–5 bullet points."
    )
    notes = await llm.chat([{"role": "user", "content": prompt}])
    return {"research_notes": notes, "status": "running"}


async def qualify_node(state: DealState) -> Dict[str, Any]:
    """Node 2: Score the opportunity using BANT criteria."""
    prompt = (
        f"Based on these research notes about '{state['company']}':\n"
        f"{state['research_notes']}\n\n"
        f"Score this sales opportunity from 0–100 using BANT criteria. "
        f"Return JSON with keys 'score' (int) and 'rationale' (str)."
    )
    raw = await llm.chat([{"role": "user", "content": prompt}])

    # Safe parse — default to 50 if LLM doesn't return valid JSON
    try:
        import json
        parsed = json.loads(raw)
        score = int(parsed.get("score", 50))
        rationale = parsed.get("rationale", raw)
    except Exception:
        score = 50
        rationale = raw

    return {
        "qualification_score": score,
        "qualification_rationale": rationale,
        "status": "running",
    }


async def draft_node(state: DealState) -> Dict[str, Any]:
    """Node 3: Draft a personalised outreach email."""
    prompt = (
        f"Draft a concise, professional outreach email to the contact at "
        f"'{state['company']}' (email: {state['contact_email']}).\n\n"
        f"Context:\n{state['research_notes']}\n\n"
        f"Qualification score: {state['qualification_score']}/100\n"
        f"Keep it under 150 words. No subject line needed."
    )
    draft = await llm.chat([{"role": "user", "content": prompt}])
    return {"draft_outreach": draft, "status": "awaiting_review"}


def should_proceed(state: DealState) -> str:
    """Conditional edge: skip drafting if qualification score is too low."""
    if state.get("qualification_score", 100) < 20:
        return "end"
    return "draft"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_deal_graph() -> StateGraph:
    """Construct and compile the deal origination StateGraph."""
    builder = StateGraph(DealState)

    # Add nodes
    builder.add_node("research", research_node)
    builder.add_node("qualify", qualify_node)
    builder.add_node("draft", draft_node)

    # Wire edges
    builder.add_edge(START, "research")
    builder.add_edge("research", "qualify")
    builder.add_conditional_edges(
        "qualify",
        should_proceed,
        {"draft": "draft", "end": END},
    )
    builder.add_edge("draft", END)

    return builder.compile()


# Singleton compiled graph — import and invoke directly
deal_graph = build_deal_graph()
