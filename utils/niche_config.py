"""
Niche-specific brain configurations
"""
from typing import Dict, Any


NICHE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "SaaS Sales Brain": {
        "signals": ["hiring support/CS roles", "funding", "new pricing page", "blog spike", "feature launches"],
        "tone": "professional but approachable",
        "cta": "15-min demo or quick Loom",
        "priorities": "speed, scale, cost per ticket, retention",
    },
    "Agency Lead Brain": {
        "signals": ["new service pages", "case study additions", "team expansion", "rebrand"],
        "tone": "consultative and insight-led",
        "cta": "share a quick case study or intro call",
        "priorities": "client results, efficiency, white-label, throughput",
    },
    "Investor Outreach Brain": {
        "signals": ["funding announcements", "board changes", "new verticals", "exits"],
        "tone": "executive, brief, strategic",
        "cta": "send 1-pager or schedule 20-min chat",
        "priorities": "ROI, market position, differentiation, traction",
    },
    "Hiring Brain": {
        "signals": ["new job postings", "careers page launch", "team page updates"],
        "tone": "casual but professional",
        "cta": "quick chat about hiring needs",
        "priorities": "speed to hire, quality, cost per hire, retention",
    },
}


def get_niche_config(niche_mode: str) -> Dict[str, Any]:
    """Get configuration for specific niche mode"""
    return NICHE_CONFIGS.get(niche_mode, NICHE_CONFIGS["SaaS Sales Brain"])
