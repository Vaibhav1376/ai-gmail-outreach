"""
Follow-up intelligence engine
TIER B-7,8: Smart follow-up sequences based on response type
"""
from typing import Dict, Any


def generate_followup_draft(
    lead: Dict[str, Any],
    reply_type: str,
    research: Dict[str, Any],
) -> str:
    """
    Generate next follow-up based on reply type
    TIER B-8: Response-based adaptation
    """
    angles = lead.get("followup_angles", [])
    
    templates = {
        "no_reply": f"Follow-up using: {angles[0] if angles else 'product angle'}",
        "not_now": f"Timing-based follow-up (no pitch). Reference: {research.get('growth_narrative', '')}",
        "interested": f"Case study angle: {angles[1] if len(angles) > 1 else 'social proof'}",
        "objection": f"Insight share (curiosity): {angles[2] if len(angles) > 2 else 'value insight'}",
    }
    
    return templates.get(reply_type, templates["no_reply"])
