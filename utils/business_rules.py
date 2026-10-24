"""
Business Rules & Validation Logic for GTM Outreach
Production-grade filters and scoring
"""
from typing import Dict, List, Any, Optional


# ====================================================================
# 1️⃣ COMPANY FILTER — HARD GATE
# ====================================================================

ALLOWED_COMPANY_TYPES = ["B2B SaaS", "SaaS", "Software", "Tech Company"]

DISALLOWED_KEYWORDS = [
    # VC/Investment
    "venture", "capital", "vc", "ventures", "investors",
    "investment", "fund", "equity",
    
    # Agencies
    "agency", "marketing agency", "consulting", "consultancy",
    
    # Media/Content
    "blog", "media", "publication", "publisher", "magazine",
    "news", "journal",
    
    # Communities/Networks
    "community", "newsletter", "network", "association",
    "conference", "event",
    
    # Other non-targets
    "university", "college", "school", "education",
    "government", "nonprofit", "charity"
]


def is_valid_company(company: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate if company is eligible for outreach
    Returns: (is_valid, reason)
    """
    name = company.get("name", "").lower()
    website = company.get("website", "").lower()
    company_type = company.get("company_type", "").lower()
    
    # Check disallowed keywords
    for keyword in DISALLOWED_KEYWORDS:
        if keyword in name or keyword in website:
            return False, f"Disallowed keyword: {keyword}"
    
    # Check company type (flexible matching)
    is_saas = any(allowed.lower() in company_type for allowed in ALLOWED_COMPANY_TYPES)
    if not is_saas and company_type:
        return False, f"Company type not B2B SaaS: {company_type}"
    
    # Basic validation
    if not name or len(name) < 2:
        return False, "Invalid company name"
    
    if not website or "." not in website:
        return False, "Invalid website"
    
    return True, "Valid"


# ====================================================================
# 2️⃣ SIGNAL SYSTEM — TIERED SCORING
# ====================================================================

SIGNAL_TIERS = {
    "TIER_1": {
        "weight": 5,
        "signals": [
            "hiring_head_of_support",
            "hiring_customer_success",
            "hiring_head_of_cx",
            "support_job_spike",
            "recent_funding_with_hiring",
            "job_board_spike",
            "multiple_support_roles",
            "expanding_support_team"
        ]
    },
    "TIER_2": {
        "weight": 3,
        "signals": [
            "pricing_change",
            "product_launch",
            "plg_push",
            "rapid_feature_release",
            "new_product_tier",
            "product_update_frequency",
            "github_activity_spike",
            "funding_announcement"
        ]
    },
    "TIER_3": {
        "weight": 1,
        "signals": [
            "blog_post",
            "thought_leadership",
            "values_page",
            "team_page_update",
            "social_media_activity"
        ]
    }
}


def calculate_signal_score(signal: str) -> int:
    """Calculate weight for a detected signal"""
    signal_lower = signal.lower()
    
    for tier_name, tier_data in SIGNAL_TIERS.items():
        for tier_signal in tier_data["signals"]:
            if tier_signal in signal_lower:
                return tier_data["weight"]
    
    return 0  # Unknown signal = 0 weight


def score_company_signals(company: Dict[str, Any]) -> tuple[int, List[str]]:
    """
    Score company based on signal quality
    Returns: (total_score, tier_breakdown)
    """
    signal = company.get("signal", "")
    
    # Calculate score
    score = calculate_signal_score(signal)
    
    # Determine tier
    tier_breakdown = []
    if score >= 5:
        tier_breakdown.append("TIER_1")
    elif score >= 3:
        tier_breakdown.append("TIER_2")
    elif score >= 1:
        tier_breakdown.append("TIER_3")
    else:
        tier_breakdown.append("NO_TIER")
    
    return score, tier_breakdown


# Minimum score threshold
MIN_SIGNAL_SCORE = 3  # At least TIER_2


# ====================================================================
# 3️⃣ INFERENCE VALIDATION — CAUSAL LOGIC
# ====================================================================

REQUIRED_INFERENCE_FIELDS = [
    "signal",
    "operational_change",
    "second_order_effect",
    "business_risk",
    "why_now"
]


def validate_inference(company: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate that inference has proper causal structure
    Returns: (is_valid, missing_fields)
    """
    inference_text = company.get("inference", "")
    
    # Check for banned fluff phrases
    banned_phrases = [
        "seems like",
        "might be",
        "could be",
        "perhaps",
        "possibly",
        "probably"
    ]
    
    missing = []
    
    if any(phrase in inference_text.lower() for phrase in banned_phrases):
        missing.append("Contains uncertain language")
    
    # Check minimum length (substance check)
    if len(inference_text) < 50:
        missing.append("Inference too short (min 50 chars)")
    
    # Check for cause-effect keywords
    required_keywords = ["because", "leads to", "indicates", "shows", "means"]
    if not any(kw in inference_text.lower() for kw in required_keywords):
        missing.append("Missing causal logic keywords")
    
    return len(missing) == 0, missing


# ====================================================================
# 4️⃣ PROBLEM OWNER MAPPING — STRICT LOGIC
# ====================================================================

PROBLEM_OWNER_MAP = {
    "support": [
        "head of support",
        "vp customer success",
        "vp support",
        "director of cx",
        "director of customer experience",
        "chief customer officer",
        "head of customer success",
        "director of support"
    ],
    "growth": [
        "vp growth",
        "head of growth",
        "growth lead",
        "product marketing lead",
        "director of growth",
        "chief growth officer"
    ],
    "infra_cost": [
        "cto",
        "vp engineering",
        "head of engineering",
        "vp infrastructure",
        "director of infrastructure",
        "head of devops"
    ],
    "hiring": [
        "head of talent",
        "vp hr",
        "director of hr",
        "head of people",
        "chief people officer",
        "talent acquisition lead"
    ]
}


def find_problem_owner(contacts: List[Dict], problem_type: str) -> Optional[Dict]:
    """
    Find the correct problem owner based on strict role matching
    Returns None if no match found (NO CEO escalation)
    """
    if problem_type not in PROBLEM_OWNER_MAP:
        return None
    
    allowed_titles = PROBLEM_OWNER_MAP[problem_type]
    
    for contact in contacts:
        title = contact.get("title", "").lower()
        
        # Exact match
        for allowed_title in allowed_titles:
            if allowed_title in title:
                return contact
    
    return None  # No match = don't use CEO fallback


# ====================================================================
# 5️⃣ CONTACT CONFIDENCE SCORE
# ====================================================================

def calculate_contact_confidence(contact: Dict, company: Dict) -> tuple[int, List[str]]:
    """
    Calculate contact confidence score (0-100)
    Returns: (score, reasons)
    """
    score = 0
    reasons = []
    
    email = contact.get("email", "")
    title = contact.get("title", "")
    company_website = company.get("website", "")
    is_inferred = contact.get("inferred", False)
    is_problem_owner = contact.get("is_problem_owner", False)
    
    # Email domain matches company (+40)
    if email and company_website:
        email_domain = email.split("@")[-1].lower()
        company_domain = company_website.replace("http://", "").replace("https://", "").split("/")[0].lower()
        
        if email_domain in company_domain or company_domain in email_domain:
            score += 40
            reasons.append("Email domain verified")
        else:
            reasons.append("Email domain mismatch")
    
    # LinkedIn title verified (+30)
    if not is_inferred and title:
        score += 30
        reasons.append("LinkedIn verified")
    else:
        reasons.append("Title inferred (not verified)")
    
    # Role matches problem (+20)
    if is_problem_owner:
        score += 20
        reasons.append("Problem owner match")
    else:
        reasons.append("Not primary problem owner")
    
    # Inferred contact penalty (-30)
    if is_inferred:
        score -= 30
        reasons.append("Email inferred (penalty)")
    
    # Ensure score is in 0-100 range
    score = max(0, min(100, score))
    
    return score, reasons


MIN_CONTACT_CONFIDENCE = 60


# ====================================================================
# 6️⃣ EMAIL VALIDATION — STRUCTURAL RULES
# ====================================================================

EMAIL_BANNED_PHRASES = [
    "hope you're doing well",
    "i hope this email finds you well",
    "i noticed your website",
    "would love to connect",
    "wanted to reach out",
    "just checking in",
    "circle back",
    "touch base"
]


def validate_email_structure(email_body: str) -> tuple[bool, List[str]]:
    """
    Validate email follows required structure
    Returns: (is_valid, issues)
    """
    issues = []
    
    # Check banned phrases
    email_lower = email_body.lower()
    for phrase in EMAIL_BANNED_PHRASES:
        if phrase in email_lower:
            issues.append(f"Contains banned phrase: '{phrase}'")
    
    # Check minimum length
    if len(email_body) < 100:
        issues.append("Email too short (min 100 chars)")
    
    # Check maximum length
    if len(email_body) > 1000:
        issues.append("Email too long (max 1000 chars)")
    
    # Check has CTA
    cta_indicators = ["?", "link", "meeting", "call", "demo", "book"]
    if not any(indicator in email_lower for indicator in cta_indicators):
        issues.append("Missing clear CTA")
    
    return len(issues) == 0, issues


# ====================================================================
# 7️⃣ FINAL CONFIDENCE SCORE — DETERMINISTIC
# ====================================================================

def calculate_final_confidence(
    company: Dict,
    contact: Dict,
    company_signal_score: int,
    contact_confidence: int,
    role_match: bool
) -> tuple[int, List[str]]:
    """
    Calculate final confidence score with transparent reasoning
    Returns: (score, explanation)
    """
    explanation = []
    
    # Company signal contribution (max 50 points)
    signal_points = min(50, company_signal_score * 10)
    explanation.append(f"Signal score: {company_signal_score} → {signal_points} pts")
    
    # Contact confidence contribution (max 30 points)
    contact_points = int(contact_confidence * 0.3)
    explanation.append(f"Contact confidence: {contact_confidence}% → {contact_points} pts")
    
    # Role match bonus (+20) or penalty (-10)
    role_points = 20 if role_match else -10
    explanation.append(f"Role match: {'Yes' if role_match else 'No'} → {role_points:+d} pts")
    
    # Calculate total
    final_score = signal_points + contact_points + role_points
    final_score = max(0, min(100, final_score))
    
    return final_score, explanation
