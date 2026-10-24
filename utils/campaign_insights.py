"""
Post-Campaign Insight Summary - Anti-Churn
Turn "25 leads" into "25 market experiments"
"""
from typing import Dict, List, Any
from collections import Counter


def generate_campaign_insights(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate actionable insights from campaign results
    Enhanced with safety checks for zero-division and missing keys
    """
    companies = results.get('companies', [])
    emails = results.get('emails', [])
    # Safe access to nested metadata
    metadata = results.get('metadata', {}) or {}
    filtering_stats = metadata.get('filtering_stats', {}) or {}
    rejected = filtering_stats.get('rejected_companies', [])
    
    insights = {
        'executive_summary': {},
        'signal_performance': {},
        'title_analysis': {},
        'rejection_learnings': {},
        'next_steps': []
    }
    
    # ========================================================================
    # 1. EXECUTIVE SUMMARY
    # ========================================================================
    
    total_companies = len(companies) + len(rejected)
    
    # Calculate averages safely
    avg_confidence = 0
    high_confidence_count = 0
    if emails:
        total_conf = 0
        for e in emails:
            try:
                # Handle string scores like "85" or int 85
                score = float(e.get('confidence', 0))
                total_conf += score
                if score >= 80:
                    high_confidence_count += 1
            except (ValueError, TypeError):
                continue
        avg_confidence = total_conf / len(emails)

    rejection_pct = 0.0
    if total_companies > 0:
        rejection_pct = (len(rejected) / total_companies) * 100

    insights['executive_summary'] = {
        'total_companies_discovered': total_companies,
        'companies_passed_quality_filter': len(companies),
        'companies_rejected': len(rejected),
        'rejection_rate': f"{rejection_pct:.1f}%",
        'total_outreach_sequences': len(emails),
        'avg_confidence_score': avg_confidence,
        'high_confidence_leads': high_confidence_count,
    }
    
    # ========================================================================
    # 2. SIGNAL PERFORMANCE
    # ========================================================================
    
    signal_types = Counter()
    signal_urgency = Counter()
    signal_confidence = {}
    
    for company in companies:
        sig_interp = company.get('signal_interpretation', {})
        if not sig_interp: 
            sig_interp = {} # Ensure dict if None
            
        signal = str(company.get('signal', '')).lower()
        
        # Classify signal type explicitly (don't rely on Counter order)
        current_type = 'Other'
        if 'hiring' in signal:
            current_type = 'Hiring'
        elif 'funding' in signal:
            current_type = 'Funding'
        elif 'product' in signal or 'launch' in signal:
            current_type = 'Product Launch'
        elif 'pricing' in signal:
            current_type = 'Pricing Change'
            
        signal_types[current_type] += 1
        
        # Track urgency
        urgency = sig_interp.get('urgency_level', 'LOW')
        signal_urgency[urgency] += 1
        
        # Track confidence by type
        if current_type not in signal_confidence:
            signal_confidence[current_type] = []
            
        try:
            conf_val = float(sig_interp.get('interpretation_confidence', 0))
            signal_confidence[current_type].append(conf_val)
        except (ValueError, TypeError):
            pass
    
    # Calculate averages
    signal_performance = {}
    for sig_type, confidences in signal_confidence.items():
        if not confidences:
            avg_conf = 0
        else:
            avg_conf = sum(confidences) / len(confidences)
            
        signal_performance[sig_type] = {
            'count': signal_types[sig_type],
            'avg_confidence': avg_conf,
            'recommendation': 'Focus here' if avg_conf > 75 else 'Needs improvement'
        }
    
    # Determine best/worst safely
    best_signal = 'N/A'
    worst_signal = 'N/A'
    if signal_performance:
        best_signal = max(signal_performance.items(), key=lambda x: x[1]['avg_confidence'])[0]
        worst_signal = min(signal_performance.items(), key=lambda x: x[1]['avg_confidence'])[0]

    insights['signal_performance'] = {
        'breakdown': dict(signal_types),
        'urgency_distribution': dict(signal_urgency),
        'performance_by_type': signal_performance,
        'best_performing_signal': best_signal,
        'worst_performing_signal': worst_signal,
    }
    
    # ========================================================================
    # 3. TITLE ANALYSIS
    # ========================================================================
    
    titles = []
    problem_owners = []
    
    # Index contacts by company name for faster lookup
    contacts_map = {
        c.get('name'): c.get('contacts', []) 
        for c in results.get('contacts', []) 
        if c.get('name')
    }

    for email in emails:
        comp_name = email.get('company')
        contact_name = email.get('contact')
        
        if not comp_name or not contact_name:
            continue
            
        company_contacts = contacts_map.get(comp_name, [])
        if not isinstance(company_contacts, list):
            continue

        for person in company_contacts:
            if person.get('full_name') == contact_name:
                title = person.get('title', 'Unknown')
                titles.append(title)
                if person.get('is_problem_owner'):
                    problem_owners.append(title)
    
    title_counter = Counter(titles)
    
    # Safe recommendation generation
    top_3_titles = [t for t, _ in title_counter.most_common(3)]
    rec_string = ", ".join(top_3_titles) if top_3_titles else "No specific titles found"

    insights['title_analysis'] = {
        'most_common_titles': dict(title_counter.most_common(5)),
        'problem_owner_titles': list(set(problem_owners)),
        'total_unique_titles': len(set(titles)),
        'recommendation': f"Focus outreach on: {rec_string}"
    }
    
    # ========================================================================
    # 4. REJECTION LEARNINGS
    # ========================================================================
    
    rejection_reasons = Counter()
    for company in rejected:
        reason = company.get('rejection_reason', 'Unknown')
        # Extract first reason if multiple
        first_reason = reason.split('|')[0].strip() if '|' in reason else reason
        rejection_reasons[first_reason] += 1
    
    insights['rejection_learnings'] = {
        'top_rejection_reasons': dict(rejection_reasons.most_common(5)),
        'total_rejected': len(rejected),
        'key_learnings': []
    }
    
    # Generate learnings (Check keys exists)
    reason_keys = set(rejection_reasons.keys())
    
    # Fuzzy matching for keys to catch slight variations
    def check_reason_keyword(keyword, keys):
        return any(keyword.lower() in k.lower() for k in keys)

    if check_reason_keyword('generic', reason_keys):
        insights['rejection_learnings']['key_learnings'].append(
            "🔴 Many companies rejected for generic signals. Need stronger, more specific triggers."
        )
    if check_reason_keyword('owner', reason_keys) or check_reason_keyword('contact', reason_keys):
        insights['rejection_learnings']['key_learnings'].append(
            "🔴 Can't identify decision makers. Narrow ICP to roles we can map."
        )
    if check_reason_keyword('urgency', reason_keys):
        insights['rejection_learnings']['key_learnings'].append(
            "🔴 Signals lack urgency. Focus on hiring/funding over soft signals."
        )
    
    # ========================================================================
    # 5. NEXT STEPS (Actionable Recommendations)
    # ========================================================================
    
    next_steps = []
    
    # Signal recommendations
    if best_signal != 'N/A':
        next_steps.append(f"✅ DOUBLE DOWN: {best_signal} signals performed best. Run next campaign focused on these.")
    
    # Title recommendations
    if top_3_titles:
        next_steps.append(f"✅ TARGET: Focus on {', '.join(top_3_titles)} - they appeared most often.")
    
    # Rejection rate optimization
    # Parse rate safely
    try:
        rate_float = float(insights['executive_summary']['rejection_rate'].rstrip('%'))
        if rate_float < 50 and total_companies > 10:
            next_steps.append("⚠️ TIGHTEN: Rejection rate too low. Increase quality bar to improve signal strength.")
        elif rate_float > 80:
            next_steps.append("⚠️ LOOSEN: Rejection rate too high. Slightly relax criteria or improve signal sources.")
    except (ValueError, TypeError):
        pass
    
    # Confidence optimization
    if avg_confidence > 0 and avg_confidence < 70:
        next_steps.append("🔴 IMPROVE: Low confidence scores. Need better research or clearer signals.")
    
    # Follow-up recommendations
    high_conf = insights['executive_summary']['high_confidence_leads']
    if high_conf > 0:
        next_steps.append(f"📧 SEND: {high_conf} high-confidence leads (80%+) ready for immediate outreach.")
    
    if len(emails) > high_conf:
        next_steps.append(f"⏰ NURTURE: Remaining leads need follow-up sequences or additional research.")
    
    insights['next_steps'] = next_steps
    
    return insights


def format_insights_for_export(insights: Dict[str, Any]) -> str:
    """
    Format insights as readable report
    """
    report = []
    
    report.append("=" * 80)
    report.append("CAMPAIGN INSIGHTS REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Executive Summary
    report.append("## EXECUTIVE SUMMARY")
    report.append("")
    exec_sum = insights.get('executive_summary', {})
    for key, value in exec_sum.items():
        key_fmt = str(key).replace('_', ' ').title()
        # Format float values for display
        val_fmt = f"{value:.2f}" if isinstance(value, float) and key != 'rejection_rate' else str(value)
        report.append(f"  {key_fmt}: {val_fmt}")
    report.append("")
    
    # Signal Performance
    report.append("## SIGNAL PERFORMANCE")
    report.append("")
    sig_perf = insights.get('signal_performance', {})
    report.append(f"  Best Performing: {sig_perf.get('best_performing_signal', 'N/A')}")
    report.append(f"  Worst Performing: {sig_perf.get('worst_performing_signal', 'N/A')}")
    report.append("")
    report.append("  Breakdown:")
    
    perf_by_type = sig_perf.get('performance_by_type', {})
    if not perf_by_type:
        report.append("    No signal data available.")
    else:
        for sig_type, data in perf_by_type.items():
            report.append(f"    - {sig_type}: {data.get('count', 0)} companies, {data.get('avg_confidence', 0):.1f}% confidence → {data.get('recommendation', '')}")
    report.append("")
    
    # Title Analysis
    report.append("## TITLE ANALYSIS")
    report.append("")
    title_analysis = insights.get('title_analysis', {})
    report.append(f"  Recommendation: {title_analysis.get('recommendation', 'N/A')}")
    report.append("")
    
    # Rejection Learnings
    report.append("## REJECTION LEARNINGS")
    report.append("")
    learnings = insights.get('rejection_learnings', {}).get('key_learnings', [])
    if not learnings:
        report.append("  No specific rejection patterns detected.")
    else:
        for learning in learnings:
            report.append(f"  {learning}")
    report.append("")
    
    # Next Steps
    report.append("## NEXT STEPS")
    report.append("")
    steps = insights.get('next_steps', [])
    if not steps:
        report.append("  Review raw data for manual next steps.")
    else:
        for step in steps:
            report.append(f"  {step}")
    report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)