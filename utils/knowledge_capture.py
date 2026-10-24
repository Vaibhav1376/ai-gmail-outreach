"""
Knowledge Capture System - Turn taste into teachable rules
Prevents founder bottleneck
"""
import streamlit as st
from typing import Dict, List, Optional
import json
import os
from datetime import datetime


def capture_rejection_reason(
    company: Dict,
    user_reason: str,
    category: str,
    run_id: str
):
    """
    Capture WHY a lead was manually rejected
    Builds knowledge base of "good vs bad" examples
    
    Args:
        company: Company data
        user_reason: Manual rejection reason from user
        category: Rejection category (signal_quality, wrong_fit, timing, etc.)
        run_id: Campaign run ID
    """
    knowledge_base = "tmp/knowledge_base.jsonl"
    os.makedirs(os.path.dirname(knowledge_base), exist_ok=True)
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'company': company.get('name', 'Unknown'),
        'signal': company.get('signal', ''),
        'signal_tier': company.get('signal_tier', ''),
        'category': category,
        'user_reason': user_reason,
        'context': {
            'company_type': company.get('company_type', ''),
            'signal_score': company.get('signal_score', 0),
            'why_fit': company.get('why_fit', '')
        },
        'action': 'REJECTED'
    }
    
    with open(knowledge_base, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def capture_approval_reason(
    company: Dict,
    user_note: str,
    run_id: str
):
    """
    Capture WHY a lead was manually approved
    """
    knowledge_base = "tmp/knowledge_base.jsonl"
    os.makedirs(os.path.dirname(knowledge_base), exist_ok=True)
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'company': company.get('name', 'Unknown'),
        'signal': company.get('signal', ''),
        'signal_tier': company.get('signal_tier', ''),
        'user_note': user_note,
        'context': {
            'company_type': company.get('company_type', ''),
            'signal_score': company.get('signal_score', 0)
        },
        'action': 'APPROVED'
    }
    
    with open(knowledge_base, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def extract_rejection_patterns() -> Dict:
    """
    Analyze knowledge base to extract patterns
    Turns individual decisions into rules
    """
    knowledge_base = "tmp/knowledge_base.jsonl"
    
    if not os.path.exists(knowledge_base):
        return {'patterns': [], 'total_entries': 0}
    
    entries = []
    
    with open(knowledge_base, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                continue
    
    # Pattern analysis
    rejection_categories = {}
    signal_rejection_rate = {}
    
    for entry in entries:
        if entry.get('action') == 'REJECTED':
            category = entry.get('category', 'other')
            rejection_categories[category] = rejection_categories.get(category, 0) + 1
            
            signal = entry.get('signal', '')[:50]
            if signal:
                if signal not in signal_rejection_rate:
                    signal_rejection_rate[signal] = {'rejected': 0, 'total': 0}
                signal_rejection_rate[signal]['rejected'] += 1
                signal_rejection_rate[signal]['total'] += 1
    
    # Generate patterns/rules
    patterns = []
    
    for category, count in sorted(rejection_categories.items(), key=lambda x: x[1], reverse=True):
        if count >= 3:  # Pattern threshold
            patterns.append({
                'type': 'rejection_category',
                'category': category,
                'frequency': count,
                'rule': f"Auto-reject if {category} (seen {count} times)"
            })
    
    # Signal patterns
    for signal, stats in signal_rejection_rate.items():
        rejection_rate = stats['rejected'] / stats['total']
        if rejection_rate >= 0.7 and stats['total'] >= 3:
            patterns.append({
                'type': 'signal_pattern',
                'signal': signal,
                'rejection_rate': f"{rejection_rate * 100:.0f}%",
                'rule': f"Flag for review: '{signal}' (rejected {rejection_rate * 100:.0f}% of time)"
            })
    
    return {
        'patterns': patterns,
        'total_entries': len(entries),
        'rejection_categories': rejection_categories
    }


def show_knowledge_base_ui():
    """
    Display knowledge base and extracted patterns
    """
    st.subheader("🧠 Knowledge Base: Team Learning System")
    
    patterns = extract_rejection_patterns()
    
    if patterns['total_entries'] == 0:
        st.info("""
ℹ️ **No judgments captured yet**

As you review leads:
1. Mark why you reject certain companies
2. Note why you approve others
3. System learns patterns automatically
4. Team can replicate your judgment

**This solves the founder bottleneck.**
        """)
        return
    
    st.success(f"""
✅ **{patterns['total_entries']} judgments captured**

System is learning your quality standards.
    """)
    
    # Show patterns
    if patterns['patterns']:
        st.write("**🎯 Detected Patterns (Auto-generated Rules):**")
        
        for pattern in patterns['patterns'][:10]:
            if pattern['type'] == 'rejection_category':
                st.write(f"- **{pattern['category']}**: Rejected {pattern['frequency']} times → Auto-flag")
            elif pattern['type'] == 'signal_pattern':
                st.write(f"- Signal: '{pattern['signal']}' → {pattern['rejection_rate']} rejection rate")
    
    # Show category breakdown
    with st.expander("📊 Rejection Categories"):
        for category, count in patterns['rejection_categories'].items():
            st.write(f"- {category.replace('_', ' ').title()}: **{count}** times")
    
    # Export rules
    st.divider()
    
    st.info("""
💡 **How this prevents founder bottleneck:**

**Without knowledge capture:**
- All quality decisions in your head
- Team guesses your standards
- Quality inconsistent
- You review everything

**With knowledge capture:**
- Decisions documented automatically
- Patterns become rules
- Team follows proven standards
- You review exceptions only

**Export these rules to train:**
- New team members
- AI models
- Quality checkers
    """)
    
    # Generate training doc
    if patterns['patterns']:
        training_doc = generate_training_doc(patterns)
        
        st.download_button(
            "📥 Download Team Training Doc",
            data=training_doc,
            file_name="quality_standards_training.md",
            mime="text/markdown"
        )


def generate_training_doc(patterns: Dict) -> str:
    """
    Generate team training document from patterns
    """
    doc = f"""# Quality Standards Training
**Generated:** {datetime.now().strftime('%Y-%m-%d')}
**Based on:** {patterns['total_entries']} real decisions

---

## Quality Standards (Learned from Experience)

### Rejection Criteria

"""
    
    for pattern in patterns['patterns']:
        if pattern['type'] == 'rejection_category':
            doc += f"**{pattern['category'].replace('_', ' ').title()}**\n"
            doc += f"- Seen {pattern['frequency']} times\n"
            doc += f"- Action: {pattern['rule']}\n\n"
    
    doc += """
### Signal Quality Patterns

"""
    
    for pattern in patterns['patterns']:
        if pattern['type'] == 'signal_pattern':
            doc += f"**Signal:** {pattern['signal']}\n"
            doc += f"- Rejection rate: {pattern['rejection_rate']}\n"
            doc += f"- Action: Manual review required\n\n"
    
    doc += """
---

## How to Use This Guide

1. **Before accepting a lead, check:**
   - Does it match any rejection patterns?
   - Is the signal type high-quality?
   - Would the founder approve this?

2. **When in doubt:**
   - Flag for manual review
   - Document your decision
   - Add to knowledge base

3. **Quality over speed:**
   - Better to reject good leads than accept bad ones
   - Reputation matters more than volume
   - Each decision teaches the system

---

*This document updates automatically as more decisions are captured.*
"""
    
    return doc


def show_lead_review_ui(leads: List[Dict], run_id: str) -> List[Dict]:
    """
    Manual lead review interface with knowledge capture
    """
    st.subheader("👀 Lead Review & Knowledge Capture")
    
    st.info("""
Review leads and mark decisions. System learns from your choices.
    """)
    
    approved_leads = []
    
    for i, lead in enumerate(leads, 1):
        with st.expander(f"Lead #{i}: {lead.get('company', 'Unknown')}", expanded=(i == 1)):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Company:** {lead.get('company', 'Unknown')}")
                st.write(f"**Signal:** {lead.get('signal', 'N/A')}")
                st.write(f"**Tier:** {lead.get('signal_tier', 'N/A')}")
                st.write(f"**Contact:** {lead.get('contact', 'N/A')} - {lead.get('role', 'N/A')}")
            
            with col2:
                st.metric("Signal Score", lead.get('signal_score', 0))
                st.metric("Quality Score", lead.get('quality_score', 0))
            
            st.divider()
            
            # Decision
            decision = st.radio(
                "Decision",
                options=["✅ Approve", "❌ Reject", "⏭️ Skip"],
                key=f"decision_{i}",
                horizontal=True
            )
            
            if decision == "❌ Reject":
                category = st.selectbox(
                    "Why reject?",
                    options=[
                        "signal_quality",
                        "wrong_fit",
                        "timing_off",
                        "contact_not_right",
                        "company_too_small",
                        "company_too_big",
                        "other"
                    ],
                    key=f"category_{i}"
                )
                
                reason = st.text_input(
                    "Specific reason (for team learning)",
                    placeholder="e.g., 'Signal is just a blog post, not real operational change'",
                    key=f"reason_{i}"
                )
                
                if reason:
                    capture_rejection_reason(lead, reason, category, run_id)
                    st.caption("✅ Saved to knowledge base")
            
            elif decision == "✅ Approve":
                note = st.text_input(
                    "Why approve? (optional)",
                    placeholder="e.g., 'Perfect timing signal + right contact'",
                    key=f"note_{i}"
                )
                
                if note:
                    capture_approval_reason(lead, note, run_id)
                
                approved_leads.append(lead)
                st.success("✅ Approved")
    
    return approved_leads
