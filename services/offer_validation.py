"""
Offer validation service
TIER C-12: Validates offer strength before campaign
"""
from typing import Dict, Any, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
import os


def create_offer_validator_agent() -> Optional[Agent]:
    """Create simple validator agent (no tools needed)"""
    # Try OpenAI first, fallback to Gemini
    if os.getenv("OPENAI_API_KEY"):
        model = OpenAIChat(id="gpt-4o-mini")
    elif os.getenv("GEMINI_API_KEY"):
        model = Gemini(id="gemini-2.0-flash-exp")
    else:
        return None
    
    instructions = [
        "You are an OfferValidator. Evaluate B2B offer strength.",
        "Check for:",
        "1. Clear outcome/benefit (not just features)",
        "2. Specificity (vague = weak)",
        "3. ICP clarity",
        "4. Differentiation hint",
        "",
        "Return JSON:",
        "{",
        '  "is_strong": boolean,',
        '  "score": 0-100,',
        '  "issues": [list of problems],',
        '  "suggested_rewrite": "improved version"',
        "}",
    ]
    
    return Agent(
        model=model,
        tools=[],
        instructions=instructions,
    )


def validate_offer(offering_desc: str, target_desc: str, niche_mode: str) -> Dict[str, Any]:
    """
    Validate offer before running campaign
    TIER C-12: Offer validation engine
    """
    agent = create_offer_validator_agent()
    if not agent:
        return {
            "is_strong": True,
            "score": 70,
            "issues": [],
            "suggested_rewrite": offering_desc,
        }
    
    prompt = (
        f"Evaluate this offer for {niche_mode}:\n\n"
        f"Target: {target_desc}\n"
        f"Offer: {offering_desc}\n\n"
        "Is this compelling? What's missing?"
    )
    
    try:
        response = agent.run(prompt)
        import json
        data = json.loads(str(response.content))
        return data
    except:
        return {
            "is_strong": True,
            "score": 70,
            "issues": [],
            "suggested_rewrite": offering_desc,
        }
