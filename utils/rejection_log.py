"""
Rejection Log - Show what was filtered OUT
"""
import streamlit as st
from typing import List, Dict
import json
import os
from datetime import datetime


def log_rejection(
    company: Dict,
    reason: str,
    stage: str,
    run_id: str
):
    """
    Log when a company is rejected
    
    Args:
        company: Company data
        reason: Why it was rejected
        stage: Which stage rejected it
        run_id: Campaign run ID
    """
    rejection_log = "tmp/rejections.jsonl"
    os.makedirs(os.path.dirname(rejection_log), exist_ok=True)
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'stage': stage,
        'company': company.get('name', 'Unknown'),
        'website': company.get('website', ''),
        'reason': reason,
        'signal': company.get('signal', ''),
        'signal_tier': company.get('signal_tier', '')
    }
    
    with open(rejection_log, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def get_rejection_summary(run_id: str = None) -> Dict:
    """
    Get summary of rejections for a run
    
    Returns:
        Dictionary with rejection statistics
    """
    rejection_log = "tmp/rejections.jsonl"
    
    if not os.path.exists(rejection_log):
        return {'total': 0, 'by_reason': {}, 'by_stage': {}}
    
    rejections = []
    
    with open(rejection_log, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if run_id is None or entry.get('run_id') == run_id:
                    rejections.append(entry)
            except:
                continue
    
    # Aggregate
    by_reason = {}
    by_stage = {}
    
    for rej in rejections:
        reason = rej.get('reason', 'Unknown')
        stage = rej.get('stage', 'Unknown')
        
        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_stage[stage] = by_stage.get(stage, 0) + 1
    
    return {
        'total': len(rejections),
        'by_reason': by_reason,
        'by_stage': by_stage,
        'examples': rejections[:10]  # First 10
    }


def show_rejection_report(run_id: str = None):
    """
    Display rejection report in Streamlit
    """
    summary = get_rejection_summary(run_id)
    
    if summary['total'] == 0:
        st.info("ℹ️ No rejections logged yet")
        return
    
    st.subheader("🚫 What We DIDN'T Include (Your Competitive Edge)")
    
    st.success(f"""
    **Total companies filtered OUT: {summary['total']}**
    
    This is what separates you from Apollo/ZoomInfo:
    - They give you EVERYTHING (noise + signal)
    - You give ONLY what matters (signal only)
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Top Rejection Reasons:**")
        for reason, count in sorted(summary['by_reason'].items(), key=lambda x: x[1], reverse=True)[:5]:
            st.write(f"- {reason}: **{count}** companies")
    
    with col2:
        st.write("**Rejections by Stage:**")
        for stage, count in summary['by_stage'].items():
            st.write(f"- {stage}: **{count}** filtered")
    
    with st.expander("📋 Example Rejections (Why They Didn't Make the Cut)"):
        for example in summary['examples']:
            st.write(f"**{example['company']}**")
            st.caption(f"Reason: {example['reason']} | Stage: {example['stage']}")
            st.divider()
    
    st.info("""
    💡 **Why this matters:**
    
    **Tools like Apollo:** 1,000 leads = 950 noise + 50 signal
    **Your approach:** 20 leads = 20 signal (everything else rejected)
    
    **Client pays for:**
    - Quality of judgment (what you excluded)
    - Signal intelligence (why these companies matter NOW)
    - Personalization depth (research + custom messaging)
    
    **NOT:**
    - Database size
    - Email count
    - Volume
    """)
