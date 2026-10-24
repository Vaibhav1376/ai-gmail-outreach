"""
Signal Interpretation Layer - Your Core Differentiation
Converts raw signals into actionable outreach intelligence

Framework: Signal → What it implies → Who feels pain → Outreach angle
"""
from typing import Dict, List, Optional, Tuple, Any


# ============================================================================
# VALIDATION LAYER (Fix #3 - Mandatory Signal Validation)
# ============================================================================

def validate_signal_interpretation(interp: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    MANDATORY: Every signal must pass this test
    Can we explain who feels pain and why now?
    
    Returns: (is_valid, list_of_issues)
    """
    issues = []
    
    required_fields = [
        'signal',
        'operational_implication',
        'pain_owner_role',
        'outreach_angle'
    ]
    
    # Check all required fields present
    for field in required_fields:
        value = interp.get(field, '')
        if not value or value in ['Unknown', '', 'Multiple', 'Various']:
            issues.append(f"Missing or unclear: {field}")
    
    # Check for vague language (Fix #4 - Weak Signal Rejection)
    vague_words = ['might', 'could be', 'possibly', 'seems', 'appears', 'maybe', 'perhaps']
    implication = interp.get('operational_implication', '').lower()
    
    if any(vague in implication for vague in vague_words):
        issues.append("Implication uses vague language (might/could/seems)")
    
    # Check for generic pain owner
    pain_owner = interp.get('pain_owner_role', '')
    generic_owners = ['Unknown', 'Multiple', 'Various', 'Team', 'Department', 'Staff']
    
    if pain_owner in generic_owners:
        issues.append("Pain owner too generic - need specific role")
    
    # Check urgency exists
    urgency = interp.get('urgency_level', 'LOW')
    if urgency == 'LOW' or urgency == 'UNKNOWN':
        issues.append("No clear timing implication (urgency = LOW/UNKNOWN)")
    
    # Check confidence threshold
    confidence = interp.get('interpretation_confidence', 0)
    if confidence < 50:
        issues.append(f"Confidence too low ({confidence}%) - signal too weak")
    
    # PASS if no issues
    is_valid = len(issues) == 0
    
    return is_valid, issues


# ============================================================================
# CORE INTERPRETATION ENGINE (Mode-Aware)
# ============================================================================

def interpret_signal(
    signal: str,
    company_name: str,
    company_type: str,
    offering: str,
    mode: str = "FIND_CLIENTS_FOR_CUSTOMER"
) -> Dict[str, Any]:
    """
    Mode-aware signal interpretation
    Converts raw signals into actionable outreach intelligence
    
    Framework: Signal → What it implies → Who feels pain → Outreach angle
    
    Args:
        signal: The raw signal detected (e.g., "Hiring Support Engineer")
        company_name: Name of target company
        company_type: Type of company (e.g., "B2B SaaS", "Marketing Agency")
        offering: Your product/service offering
        mode: "FIND_MY_CLIENTS" or "FIND_CLIENTS_FOR_CUSTOMER"
    
    Returns:
        Dictionary with interpretation details and validation status
    """
    
    # Initialize interpretation structure
    interpretation = {
        'signal': signal.strip(),
        'operational_implication': '',
        'pain_owner_role': '',
        'pain_owner_department': '',
        'outreach_angle': '',
        'urgency_level': '',  # LOW, MEDIUM, HIGH, CRITICAL
        'interpretation_confidence': 0,  # 0-100
        'is_valid': False,
        'validation_issues': [],
        'mode': mode
    }
    
    # Empty signal check
    if not signal or signal.strip() == '':
        interpretation.update({
            'operational_implication': 'No signal detected',
            'pain_owner_role': 'Unknown',
            'outreach_angle': 'Generic outreach',
            'urgency_level': 'LOW',
            'interpretation_confidence': 0,
            'validation_issues': ['No signal provided']
        })
        return interpretation
    
    signal_lower = signal.lower()
    
    # ========================================================================
    # MODE: FIND_MY_CLIENTS (Agency-Finding Mode)
    # ========================================================================
    
    if mode == "FIND_MY_CLIENTS":
        return interpret_agency_signal(
            signal, signal_lower, company_name, company_type, offering, interpretation
        )
    
    # ========================================================================
    # MODE: FIND_CLIENTS_FOR_CUSTOMER (B2B Campaign Mode)
    # ========================================================================
    
    elif mode == "FIND_CLIENTS_FOR_CUSTOMER":
        return interpret_b2b_signal(
            signal, signal_lower, company_name, company_type, offering, interpretation
        )
    
    # Fallback
    return interpretation


# ============================================================================
# AGENCY MODE INTERPRETATION (Fix #2 - Mode-Specific Signals)
# ============================================================================

def interpret_agency_signal(
    signal: str,
    signal_lower: str,
    company_name: str,
    company_type: str,
    offering: str,
    interpretation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Interpret signals for agency-finding mode (YOUR clients)
    
    Focus on:
    - Referral dependency
    - Lead flow issues
    - Founder overwhelm
    - Sales team hiring
    """
    
    # ========================================================================
    # TIER 1: Referral Dependency Signals (Highest Value)
    # ========================================================================
    
    if any(kw in signal_lower for kw in ['referral', 'word of mouth', 'inbound', 'lead flow']):
        interpretation.update({
            'operational_implication': 'Agency dependent on unpredictable referral pipeline. Revenue inconsistency, can\'t plan hiring or growth.',
            'pain_owner_role': 'Founder / Owner',
            'pain_owner_department': 'Leadership',
            'outreach_angle': f'Noticed {company_name} mentions referral-driven growth. {offering} builds predictable outbound pipeline that complements referrals, reducing revenue volatility by 60%.',
            'urgency_level': 'HIGH',
            'interpretation_confidence': 95
        })
    
    # ========================================================================
    # TIER 1: Founder Doing Sales (High Pain)
    # ========================================================================
    
    elif any(kw in signal_lower for kw in ['founder', 'owner', 'ceo', 'managing partner']) and \
         any(kw in signal_lower for kw in ['sales', 'business development', 'outreach']):
        interpretation.update({
            'operational_implication': 'Founder spending 30-50% of time on sales. Bottleneck preventing service delivery focus and scaling.',
            'pain_owner_role': 'Founder / Owner',
            'pain_owner_department': 'Leadership',
            'outreach_angle': f'Saw you\'re still handling sales at {company_name}. {offering} takes prospecting off your plate so you can focus on delivery and team building.',
            'urgency_level': 'HIGH',
            'interpretation_confidence': 92
        })
    
    # ========================================================================
    # TIER 1: Hiring Sales/BD Roles
    # ========================================================================
    
    elif any(kw in signal_lower for kw in ['hiring', 'recruiting']) and \
         any(kw in signal_lower for kw in ['sales', 'business development', 'bd', 'account executive']):
        interpretation.update({
            'operational_implication': 'Agency trying to scale beyond founder-led sales. New hire needs pipeline to be productive.',
            'pain_owner_role': 'Founder / Owner',
            'pain_owner_department': 'Sales',
            'outreach_angle': f'You\'re hiring {signal}. New sales hires need consistent pipeline on day 1. {offering} ensures they have 15-20 qualified conversations/month from the start.',
            'urgency_level': 'HIGH',
            'interpretation_confidence': 88
        })
    
    # ========================================================================
    # TIER 2: Service Expansion
    # ========================================================================
    
    elif any(kw in signal_lower for kw in ['new service', 'expanding', 'adding']):
        interpretation.update({
            'operational_implication': 'Agency diversifying offerings. Need to find new audience segments or prove demand for new service.',
            'pain_owner_role': 'Founder / Partner',
            'pain_owner_department': 'Strategy',
            'outreach_angle': f'{company_name} is expanding services. {offering} helps you test demand and fill pipeline for new offerings without expensive experiments.',
            'urgency_level': 'MEDIUM',
            'interpretation_confidence': 75
        })
    
    # ========================================================================
    # TIER 2: Team Growth
    # ========================================================================
    
    elif any(kw in signal_lower for kw in ['hiring', 'team growth', 'expanding team']):
        interpretation.update({
            'operational_implication': 'Agency scaling team. Need more revenue to support new headcount, can\'t rely on referrals alone.',
            'pain_owner_role': 'Founder / Owner',
            'pain_owner_department': 'Operations',
            'outreach_angle': f'Growing team at {company_name} means you need consistent revenue. {offering} adds predictable pipeline so new hires don\'t sit idle.',
            'urgency_level': 'MEDIUM',
            'interpretation_confidence': 70
        })
    
    # ========================================================================
    # TIER 3: Weak Signals (Usually Reject)
    # ========================================================================
    
    else:
        interpretation.update({
            'operational_implication': 'Generic agency activity detected. Specific pain point unclear.',
            'pain_owner_role': 'Unknown',
            'pain_owner_department': 'Unknown',
            'outreach_angle': f'Noticed activity at {company_name}. {offering} might help with lead generation.',
            'urgency_level': 'LOW',
            'interpretation_confidence': 30
        })
    
    # Validate and return
    is_valid, validation_issues = validate_signal_interpretation(interpretation)
    interpretation['is_valid'] = is_valid
    interpretation['validation_issues'] = validation_issues
    
    if not is_valid:
        interpretation['interpretation_confidence'] = max(0, interpretation['interpretation_confidence'] - 30)
    
    return interpretation


# ============================================================================
# B2B MODE INTERPRETATION (Standard SaaS Campaign)
# ============================================================================

def interpret_b2b_signal(
    signal: str,
    signal_lower: str,
    company_name: str,
    company_type: str,
    offering: str,
    interpretation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Interpret signals for B2B campaign mode (client campaigns)
    
    Focus on:
    - Hiring (operational pain)
    - Funding (expansion mode)
    - Product launches (adoption needs)
    - Market expansion (scaling challenges)
    """
    
    # ========================================================================
    # TIER 1: Hiring (Strongest B2B Signal)
    # ========================================================================
    
    if 'hiring' in signal_lower or 'recruiting' in signal_lower:
        
        # Support/CX roles
        if any(role in signal_lower for role in ['support', 'customer success', 'cx', 'cs', 'customer service']):
            interpretation.update({
                'operational_implication': 'Support volume scaling beyond current team capacity. Ticket backlog accumulating, response times slipping.',
                'pain_owner_role': 'Head of Customer Success',
                'pain_owner_department': 'Customer Success',
                'outreach_angle': f'Your hiring for {signal} indicates support pressure. {offering} reduces ticket volume by 40%, buying your team breathing room before new hire onboards.',
                'urgency_level': 'CRITICAL',
                'interpretation_confidence': 95
            })
        
        # Sales roles (SDR, AE, BDR)
        elif any(role in signal_lower for role in ['sdr', 'sales development', 'bdr', 'account executive', 'ae', 'sales rep']):
            interpretation.update({
                'operational_implication': 'Ramping new sales headcount. Need to hit quota faster with less ramp time. Sales leadership under pressure.',
                'pain_owner_role': 'VP Sales',
                'pain_owner_department': 'Sales',
                'outreach_angle': f'Noticed you\'re hiring {signal}. New reps need pipeline fast. {offering} accelerates ramp time by 3 months by automating outreach.',
                'urgency_level': 'HIGH',
                'interpretation_confidence': 90
            })
        
        # Engineering/Product roles
        elif any(role in signal_lower for role in ['engineer', 'developer', 'devops', 'sre', 'backend', 'frontend', 'fullstack']):
            interpretation.update({
                'operational_implication': 'Infrastructure scaling. Likely launching features, expanding capacity, or addressing technical debt under load.',
                'pain_owner_role': 'CTO',
                'pain_owner_department': 'Engineering',
                'outreach_angle': f'Your hiring for {signal} suggests infrastructure scaling. {offering} helps manage increased load without linear team growth.',
                'urgency_level': 'MEDIUM',
                'interpretation_confidence': 85
            })
        
        # Marketing/Growth roles
        elif any(role in signal_lower for role in ['marketing', 'growth', 'demand gen', 'content', 'performance marketing']):
            interpretation.update({
                'operational_implication': 'Scaling go-to-market motion. Likely need more pipeline, better conversion, or new channels.',
                'pain_owner_role': 'VP Marketing',
                'pain_owner_department': 'Marketing',
                'outreach_angle': f'You\'re hiring {signal}, which signals GTM expansion. {offering} helps generate 40% more qualified pipeline without doubling headcount.',
                'urgency_level': 'MEDIUM',
                'interpretation_confidence': 80
            })
        
        # Generic hiring (lower confidence)
        else:
            interpretation.update({
                'operational_implication': 'General team expansion. Growth phase but specific pain unclear.',
                'pain_owner_role': 'Department Head',
                'pain_owner_department': 'Multiple',
                'outreach_angle': f'Noticed hiring activity at {company_name}. {offering} helps growing teams scale efficiently.',
                'urgency_level': 'LOW',
                'interpretation_confidence': 50
            })
    
    # ========================================================================
    # TIER 1: Funding Signals
    # ========================================================================
    
    elif 'funding' in signal_lower or 'raised' in signal_lower or 'series' in signal_lower or 'round' in signal_lower:
        interpretation.update({
            'operational_implication': 'New capital deployed. Building infrastructure, hiring, scaling GTM. High spending mode for 18-24 months.',
            'pain_owner_role': 'CEO / COO',
            'pain_owner_department': 'Executive',
            'outreach_angle': f'{company_name} just raised funding. {offering} helps deploy capital efficiently in [area], accelerating time-to-value and ROI visibility.',
            'urgency_level': 'HIGH',
            'interpretation_confidence': 85
        })
    
    # ========================================================================
    # TIER 2: Product/Market Changes
    # ========================================================================
    
    elif 'pricing' in signal_lower and ('update' in signal_lower or 'change' in signal_lower):
        interpretation.update({
            'operational_implication': 'Monetization strategy shift. Testing new packaging, moving upmarket, or addressing churn.',
            'pain_owner_role': 'VP Product',
            'pain_owner_department': 'Product',
            'outreach_angle': f'Your pricing page update suggests monetization focus. {offering} helps optimize conversion at new price points by [mechanism].',
            'urgency_level': 'MEDIUM',
            'interpretation_confidence': 75
        })
    
    elif 'product launch' in signal_lower or 'new feature' in signal_lower or 'release' in signal_lower:
        interpretation.update({
            'operational_implication': 'Expanding product surface area. Need adoption, onboarding, support for new capabilities. Feature visibility critical.',
            'pain_owner_role': 'VP Product',
            'pain_owner_department': 'Product',
            'outreach_angle': f'{company_name} launched new features. {offering} accelerates adoption by helping users discover value faster.',
            'urgency_level': 'MEDIUM',
            'interpretation_confidence': 70
        })
    
    elif 'market expansion' in signal_lower or 'new region' in signal_lower or 'international' in signal_lower:
        interpretation.update({
            'operational_implication': 'Geographic or vertical expansion. Replicating GTM motion in new territory with limited local knowledge.',
            'pain_owner_role': 'VP Sales',
            'pain_owner_department': 'Sales',
            'outreach_angle': f'Expanding to new markets means replicating your GTM motion. {offering} helps scale outreach without linear team growth.',
            'urgency_level': 'MEDIUM',
            'interpretation_confidence': 70
        })
    
    # ========================================================================
    # TIER 3: Weak Signals (Usually REJECT)
    # ========================================================================
    
    elif 'blog post' in signal_lower or 'article' in signal_lower or 'content' in signal_lower:
        interpretation.update({
            'operational_implication': 'Thought leadership or content marketing. Indirect indicator of priorities, not operational pain.',
            'pain_owner_role': 'Unknown',
            'pain_owner_department': 'Marketing',
            'outreach_angle': f'Saw your post about {signal}. {offering} aligns with your focus on [topic].',
            'urgency_level': 'LOW',
            'interpretation_confidence': 30
        })
    
    elif 'conference' in signal_lower or 'event' in signal_lower or 'sponsor' in signal_lower:
        interpretation.update({
            'operational_implication': 'Brand building or market presence. No clear operational pain.',
            'pain_owner_role': 'Unknown',
            'pain_owner_department': 'Marketing',
            'outreach_angle': f'{company_name} is active at conferences. {offering} might support your growth.',
            'urgency_level': 'LOW',
            'interpretation_confidence': 25
        })
    
    # ========================================================================
    # FALLBACK: Generic/Unknown Signal
    # ========================================================================
    
    else:
        interpretation.update({
            'operational_implication': 'Signal detected but context unclear. Requires manual validation.',
            'pain_owner_role': 'Unknown',
            'pain_owner_department': 'Unknown',
            'outreach_angle': f'Noticed {signal} at {company_name}. {offering} might be relevant.',
            'urgency_level': 'LOW',
            'interpretation_confidence': 20
        })
    
    # Validate and return
    is_valid, validation_issues = validate_signal_interpretation(interpretation)
    interpretation['is_valid'] = is_valid
    interpretation['validation_issues'] = validation_issues
    
    if not is_valid:
        interpretation['interpretation_confidence'] = max(0, interpretation['interpretation_confidence'] - 30)
    
    return interpretation


# ============================================================================
# DISPLAY FORMATTING (Fix #1 - Missing Function)
# ============================================================================

def format_interpretation_for_display(signal_interp: Dict[str, Any]) -> str:
    """
    Format signal interpretation for UI display
    Structure: Signal → Implies → Pain Owner → Outreach Angle
    
    Args:
        signal_interp: Interpretation dictionary
    
    Returns:
        Formatted multi-line string for display
    """
    if not signal_interp or not isinstance(signal_interp, dict):
        return "No interpretation available"
    
    validation_status = "✅ Valid" if signal_interp.get('is_valid') else "⚠️ Needs Review"
    
    output = (
        f"**Signal:** {signal_interp.get('signal', 'Unknown')}\n"
        f"**→ Implies:** {signal_interp.get('operational_implication', 'Unknown')}\n"
        f"**→ Pain Owner:** {signal_interp.get('pain_owner_role', 'Unknown')} "
        f"({signal_interp.get('pain_owner_department', 'Unknown')})\n"
        f"**→ Outreach Angle:** {signal_interp.get('outreach_angle', 'Unknown')}\n\n"
        f"**Urgency:** {signal_interp.get('urgency_level', 'UNKNOWN')} | "
        f"**Confidence:** {signal_interp.get('interpretation_confidence', 0)}%\n"
        f"**Status:** {validation_status}"
    )
    
    # Show validation issues if any
    validation_issues = signal_interp.get('validation_issues', [])
    if validation_issues:
        output += "\n\n**⚠️ Validation Issues:**"
        for issue in validation_issues:
            output += f"\n  • {issue}"
    
    return output


# ============================================================================
# BULK OPERATIONS (Fix #2 - Missing Function)
# ============================================================================

def bulk_interpret_signals(
    companies: List[Dict],
    offering: str = "",
    mode: str = "FIND_CLIENTS_FOR_CUSTOMER"
) -> List[Dict]:
    """
    Add signal interpretation to all companies in batch
    
    Args:
        companies: List of company dictionaries with 'signal' field
        offering: Your product/service offering description
        mode: Pipeline mode (affects interpretation style)
    
    Returns:
        Updated companies list with 'signal_interpretation' added
    """
    for company in companies:
        signal = company.get('signal', '')
        
        # Skip if no signal
        if not signal or signal.strip() == '':
            company['signal_interpretation'] = {
                'signal': '',
                'operational_implication': 'No signal detected',
                'pain_owner_role': 'Unknown',
                'outreach_angle': 'Generic outreach',
                'urgency_level': 'LOW',
                'interpretation_confidence': 0,
                'is_valid': False,
                'validation_issues': ['No signal provided']
            }
            company['signal_is_valid'] = False
            company['signal_confidence'] = 0
            continue
        
        # Interpret signal
        interp = interpret_signal(
            signal=signal,
            company_name=company.get('name', 'Unknown'),
            company_type=company.get('company_type', 'B2B SaaS'),
            offering=offering,
            mode=mode
        )
        
        company['signal_interpretation'] = interp
        
        # Add top-level flags for easy filtering
        company['signal_is_valid'] = interp['is_valid']
        company['signal_confidence'] = interp['interpretation_confidence']
    
    return companies


# ============================================================================
# FILTERING & STATISTICS
# ============================================================================

def filter_by_signal_quality(
    companies: List[Dict],
    min_confidence: int = 70,
    require_valid: bool = True
) -> List[Dict]:
    """
    Filter companies by signal interpretation quality
    
    Args:
        companies: List of companies with signal_interpretation
        min_confidence: Minimum confidence score (0-100)
        require_valid: If True, only keep validated signals
    
    Returns:
        Filtered list of high-quality signal companies
    """
    filtered = []
    
    for company in companies:
        interp = company.get('signal_interpretation', {})
        
        # Check confidence threshold
        confidence = interp.get('interpretation_confidence', 0)
        if confidence < min_confidence:
            continue
        
        # Check validation status
        if require_valid and not interp.get('is_valid', False):
            continue
        
        filtered.append(company)
    
    return filtered


def get_signal_statistics(companies: List[Dict]) -> Dict[str, Any]:
    """
    Analyze signal interpretation quality across all companies
    
    Args:
        companies: List of companies with signal_interpretation
    
    Returns:
        Statistics dictionary with quality metrics
    """
    total = len(companies)
    
    if total == 0:
        return {
            'total_companies': 0,
            'valid_signals': 0,
            'invalid_signals': 0,
            'avg_confidence': 0,
            'high_confidence_count': 0,
            'urgency_breakdown': {},
            'validation_rate': '0%',
            'high_confidence_rate': '0%'
        }
    
    # Count valid signals
    valid_count = sum(
        1 for c in companies 
        if c.get('signal_interpretation', {}).get('is_valid', False)
    )
    invalid_count = total - valid_count
    
    # Calculate confidence stats
    confidences = [
        c.get('signal_interpretation', {}).get('interpretation_confidence', 0) 
        for c in companies
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    high_confidence = sum(1 for conf in confidences if conf >= 80)
    
    # Urgency breakdown
    urgency_counts = {}
    for company in companies:
        urgency = company.get('signal_interpretation', {}).get('urgency_level', 'UNKNOWN')
        urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
    
    return {
        'total_companies': total,
        'valid_signals': valid_count,
        'invalid_signals': invalid_count,
        'validation_rate': f"{(valid_count/total)*100:.1f}%",
        'avg_confidence': round(avg_confidence, 1),
        'high_confidence_count': high_confidence,
        'high_confidence_rate': f"{(high_confidence/total)*100:.1f}%",
        'urgency_breakdown': urgency_counts
    }
