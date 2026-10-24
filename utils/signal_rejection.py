"""
Aggressive Signal Rejection Engine
Target: Reject 60-70% of leads to maintain quality
Fewer leads, stronger narrative
"""
from typing import Dict, List, Tuple


def evaluate_signal_quality(company: Dict, mode: str = "FIND_CLIENTS_FOR_CUSTOMER") -> Tuple[bool, str, int]:
    """
    AGGRESSIVE rejection with mode awareness
    Target rejection rate: 60-70%
    
    Returns: (should_accept, rejection_reason, quality_score)
    Quality Score: 0-100 (minimum 75 to pass)
    """
    rejection_reasons = []
    quality_score = 100
    
    signal = company.get('signal', '').lower()
    signal_interpretation = company.get('signal_interpretation', {})
    
    # ========================================================================
    # RULE 0: Signal Interpretation MUST be valid (CRITICAL)
    # ========================================================================
    
    if not signal_interpretation.get('is_valid', False):
        validation_issues = signal_interpretation.get('validation_issues', [])
        rejection_reasons.append(f"REJECT: Invalid interpretation - {'; '.join(validation_issues)}")
        quality_score -= 50
    
    # ========================================================================
    # RULE 1: Vague signals = AUTO REJECT
    # ========================================================================
    
    vague_signals = [
        'growing', 'innovating', 'transforming', 'evolving',
        'scaling', 'expanding', 'improving', 'optimizing',
        'growth', 'scale', 'innovation', 'transformation',
        'digital', 'cloud', 'AI', 'ML', 'modernization'
    ]
    
    # If signal is ONLY vague words, reject
    signal_words = signal.split()
    vague_count = sum(1 for word in vague_signals if word in signal)
    
    if vague_count >= 2 or (vague_count == 1 and len(signal_words) < 5):
        rejection_reasons.append("REJECT: Signal too vague (generic growth language)")
        quality_score -= 40
    
    # ========================================================================
    # RULE 2: Minimum 2 Hiring Roles (if hiring signal)
    # ========================================================================
    
    if 'hiring' in signal:
        # Check if signal mentions specific number
        if 'hiring 1' in signal or signal.count('hiring') == 1:
            rejection_reasons.append("REJECT: Hiring < 2 roles (single hire = not urgent)")
            quality_score -= 40
    
    # ========================================================================
    # RULE 3: No Clear Pain Owner = REJECT
    # ========================================================================
    
    pain_owner = signal_interpretation.get('pain_owner_role', '')
    if pain_owner in ['Unknown', 'Multiple', 'Various', 'Team', 'Department', '']:
        rejection_reasons.append("REJECT: No identifiable pain owner")
        quality_score -= 35
    
    # ========================================================================
    # RULE 4: No Timing Implication = REJECT
    # ========================================================================
    
    urgency = signal_interpretation.get('urgency_level', 'LOW')
    if urgency == 'LOW':
        rejection_reasons.append("REJECT: No clear timing implication (why now unclear)")
        quality_score -= 30
    
    # ========================================================================
    # RULE 5: Low Interpretation Confidence = REJECT
    # ========================================================================
    
    confidence = signal_interpretation.get('interpretation_confidence', 0)
    if confidence < 60:
        rejection_reasons.append(f"REJECT: Low interpretation confidence ({confidence}%)")
        quality_score -= 20
    
    # ========================================================================
    # RULE 6: "Too Stable" Check
    # ========================================================================
    
    stability_indicators = [
        'established', 'mature', 'stable', 'consistent',
        'steady', 'veteran', 'leading', 'dominant', 'industry leader'
    ]
    
    company_desc = f"{company.get('name', '')} {company.get('why_fit', '')}".lower()
    
    if any(indicator in company_desc for indicator in stability_indicators):
        rejection_reasons.append("REJECT: Company appears too stable (low urgency)")
        quality_score -= 25
    
    # ========================================================================
    # RULE 7: "Would You Feel Awkward?" Test
    # ========================================================================
    
    # Check if signal is too weak to message about
    awkward_signals = [
        'posted on linkedin', 'tweeted', 'blog post',
        'mentioned in interview', 'values page', 'about page update',
        'article', 'press release', 'news mention'
    ]
    
    if any(awkward in signal for awkward in awkward_signals):
        rejection_reasons.append("REJECT: Too awkward to message about (weak pretext)")
        quality_score -= 40
    
    # ========================================================================
    # RULE 8: TIER_3 Signals = Auto-Reject
    # ========================================================================
    
    if company.get('signal_tier') == 'TIER_3':
        rejection_reasons.append("REJECT: TIER_3 signal (too weak)")
        quality_score -= 50
    
    # ========================================================================
    # RULE 9: Company Type Validation
    # ========================================================================
    
    company_type = company.get('company_type', '').lower()
    if 'saas' not in company_type and 'software' not in company_type and 'b2b' not in company_type:
        rejection_reasons.append("REJECT: Not B2B SaaS/Software")
        quality_score -= 40
    
    # ========================================================================
    # RULE 10: Missing Critical Fields
    # ========================================================================
    
    required_fields = ['name', 'website', 'signal', 'signal_interpretation']
    missing = [f for f in required_fields if not company.get(f)]
    
    if missing:
        rejection_reasons.append(f"REJECT: Missing fields: {', '.join(missing)}")
        quality_score -= 15 * len(missing)
    
    # ========================================================================
    # RULE 11: Generic Offer Alignment Check
    # ========================================================================
    
    offer_alignment = company.get('offer_alignment', '').lower()
    generic_alignment_phrases = [
        'could help', 'might be useful', 'potentially relevant',
        'may benefit', 'possibly useful', 'could be a fit'
    ]
    
    if any(phrase in offer_alignment for phrase in generic_alignment_phrases):
        rejection_reasons.append("REJECT: Offer alignment too vague/uncertain")
        quality_score -= 25
    
    # ========================================================================
    # MODE-SPECIFIC RULES
    # ========================================================================
    
    if mode == "FIND_MY_CLIENTS":
        # Agency mode: Even more aggressive
        
        # Must have founder/owner pressure signal
        agency_pressure_signals = [
            'referral', 'lead flow', 'pipeline', 'founder',
            'owner', 'sales team', 'closing', 'prospecting',
            'revenue', 'growth', 'clients'
        ]
        
        has_agency_signal = any(ps in signal for ps in agency_pressure_signals)
        
        if not has_agency_signal:
            rejection_reasons.append("REJECT: No clear agency pain signal")
            quality_score -= 30
        
        # Higher confidence threshold for agencies
        if confidence < 75:
            rejection_reasons.append(f"REJECT: Confidence too low for agency outreach ({confidence}%)")
            quality_score -= 25
    
    elif mode == "INVESTOR_OUTREACH":
        # Investor mode: Must show traction/momentum
        
        traction_signals = [
            'funding', 'raised', 'series', 'revenue', 'growth',
            'customers', 'arr', 'mrr', 'unicorn', 'valuation'
        ]
        
        has_traction = any(ts in signal for ts in traction_signals)
        
        if not has_traction:
            rejection_reasons.append("REJECT: No clear traction signal for investors")
            quality_score -= 35
    
    elif mode == "HIRING_BRAIN":
        # Hiring mode: Must show team growth
        
        if 'hiring' not in signal and 'team' not in signal and 'headcount' not in signal:
            rejection_reasons.append("REJECT: No hiring/team growth signal")
            quality_score -= 40
    
    # ========================================================================
    # DECISION: Target 60-70% rejection (AGGRESSIVE threshold)
    # ========================================================================
    
    # Aggressive threshold: 75/100 (raised from 70)
    should_accept = quality_score >= 75 and len(rejection_reasons) == 0
    
    rejection_summary = " | ".join(rejection_reasons) if rejection_reasons else "PASS"
    
    return should_accept, rejection_summary, max(0, quality_score)


def apply_rejection_rules(
    companies: List[Dict], 
    mode: str = "FIND_CLIENTS_FOR_CUSTOMER"
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Apply aggressive rejection rules with mode awareness
    Returns: (accepted_companies, rejected_companies, stats)
    """
    accepted = []
    rejected = []
    
    for company in companies:
        should_accept, reason, score = evaluate_signal_quality(company, mode)
        
        company['quality_score'] = score
        company['rejection_reason'] = reason if not should_accept else None
        company['passed_quality_gate'] = should_accept
        
        if should_accept:
            accepted.append(company)
        else:
            rejected.append(company)
    
    stats = {
        'total_companies': len(companies),
        'accepted': len(accepted),
        'rejected': len(rejected),
        'rejection_rate': round((len(rejected) / len(companies) * 100), 1) if companies else 0,
        'acceptance_rate': round((len(accepted) / len(companies) * 100), 1) if companies else 0,
        'avg_accepted_score': round(sum(c['quality_score'] for c in accepted) / len(accepted), 1) if accepted else 0,
        'avg_rejected_score': round(sum(c['quality_score'] for c in rejected) / len(rejected), 1) if rejected else 0,
        'target_rejection_range': '60-70%',
        'status': 'GOOD' if len(companies) > 0 and 60 <= (len(rejected) / len(companies) * 100) <= 70 else 'ADJUST_THRESHOLDS'
    }
    
    return accepted, rejected, stats


def get_rejection_breakdown(rejected_companies: List[Dict]) -> Dict[str, any]:
    """
    Analyze why companies were rejected
    Returns insights on rejection patterns
    """
    if not rejected_companies:
        return {
            'total_rejected': 0,
            'top_rejection_reasons': {},
            'avg_score': 0,
            'insights': []
        }
    
    # Count rejection reasons
    reason_counts = {}
    
    for company in rejected_companies:
        reasons = company.get('rejection_reason', '')
        if reasons and reasons != 'PASS':
            # Split multiple reasons
            for reason in reasons.split(' | '):
                reason_key = reason.split(':')[0].replace('REJECT', '').strip()
                reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
    
    # Sort by frequency
    top_reasons = dict(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    # Generate insights
    insights = []
    
    if reason_counts.get('Signal too vague', 0) > len(rejected_companies) * 0.3:
        insights.append("30%+ rejections due to vague signals - refine signal detection criteria")
    
    if reason_counts.get('No identifiable pain owner', 0) > len(rejected_companies) * 0.25:
        insights.append("25%+ rejections due to unclear pain owner - improve signal interpretation")
    
    if reason_counts.get('No clear timing implication', 0) > len(rejected_companies) * 0.2:
        insights.append("20%+ rejections due to low urgency - focus on time-sensitive signals")
    
    avg_score = sum(c['quality_score'] for c in rejected_companies) / len(rejected_companies)
    
    return {
        'total_rejected': len(rejected_companies),
        'top_rejection_reasons': top_reasons,
        'avg_rejected_score': round(avg_score, 1),
        'insights': insights
    }


def suggest_threshold_adjustments(stats: Dict) -> Dict[str, str]:
    """
    Suggest threshold adjustments based on rejection rate
    Goal: Hit 60-70% rejection rate
    """
    rejection_rate = stats.get('rejection_rate', 0)
    suggestions = {}
    
    if rejection_rate < 50:
        suggestions['action'] = 'INCREASE_STRICTNESS'
        suggestions['recommendation'] = 'Rejection rate too low (<50%). Increase minimum quality score from 75 to 80.'
        suggestions['new_threshold'] = 80
    
    elif rejection_rate < 60:
        suggestions['action'] = 'SLIGHT_INCREASE'
        suggestions['recommendation'] = 'Rejection rate slightly low (50-60%). Consider raising threshold to 78.'
        suggestions['new_threshold'] = 78
    
    elif rejection_rate > 80:
        suggestions['action'] = 'DECREASE_STRICTNESS'
        suggestions['recommendation'] = 'Rejection rate too high (>80%). Lower threshold to 72 to pass more leads.'
        suggestions['new_threshold'] = 72
    
    elif rejection_rate > 70:
        suggestions['action'] = 'SLIGHT_DECREASE'
        suggestions['recommendation'] = 'Rejection rate slightly high (70-80%). Consider lowering to 73.'
        suggestions['new_threshold'] = 73
    
    else:
        suggestions['action'] = 'MAINTAIN'
        suggestions['recommendation'] = f'Perfect range! Rejection rate at {rejection_rate:.1f}% (target: 60-70%)'
        suggestions['new_threshold'] = 75
    
    return suggestions


def filter_companies_with_explanation(
    companies: List[Dict],
    mode: str = "FIND_CLIENTS_FOR_CUSTOMER",
    verbose: bool = False
) -> Dict[str, any]:
    """
    Complete filtering with detailed explanations
    Perfect for debugging and understanding rejection patterns
    
    Returns: {
        'accepted': [...],
        'rejected': [...],
        'stats': {...},
        'rejection_breakdown': {...},
        'threshold_suggestions': {...}
    }
    """
    accepted, rejected, stats = apply_rejection_rules(companies, mode)
    rejection_breakdown = get_rejection_breakdown(rejected)
    threshold_suggestions = suggest_threshold_adjustments(stats)
    
    result = {
        'accepted': accepted,
        'rejected': rejected,
        'stats': stats,
        'rejection_breakdown': rejection_breakdown,
        'threshold_suggestions': threshold_suggestions
    }
    
    # Verbose mode: Add detailed logs
    if verbose:
        result['detailed_logs'] = []
        
        for company in companies:
            log_entry = {
                'company': company.get('name'),
                'score': company.get('quality_score'),
                'passed': company.get('passed_quality_gate'),
                'reason': company.get('rejection_reason')
            }
            result['detailed_logs'].append(log_entry)
    
    return result


def quick_quality_check(companies: List[Dict], mode: str = "FIND_CLIENTS_FOR_CUSTOMER") -> str:
    """
    Quick summary for CLI/logging
    Returns: Human-readable summary string
    """
    accepted, rejected, stats = apply_rejection_rules(companies, mode)
    
    summary = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    QUALITY GATE RESULTS                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Total Companies:        {stats['total_companies']:>4}                                   ║
║ ✅ Accepted:            {stats['accepted']:>4} ({stats['acceptance_rate']:>5}%)                        ║
║ ❌ Rejected:            {stats['rejected']:>4} ({stats['rejection_rate']:>5}%)                        ║
║                                                               ║
║ Avg Score (Accepted):   {stats['avg_accepted_score']:>5.1f} / 100                          ║
║ Avg Score (Rejected):   {stats['avg_rejected_score']:>5.1f} / 100                          ║
║                                                               ║
║ Target Range:           60-70% rejection                      ║
║ Status:                 {stats['status']:<30}      ║
╚═══════════════════════════════════════════════════════════════╝
    """
    
    return summary.strip()