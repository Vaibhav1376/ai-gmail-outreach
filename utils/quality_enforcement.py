"""
Quality Enforcement - Prevent "speed over quality" decay
"""
import streamlit as st
from typing import Dict, List
from datetime import datetime
import json
import os


def enforce_review_time_limit(num_leads: int) -> Dict:
    """
    Calculate minimum review time to maintain quality
    Prevents rushing through reviews
    
    Args:
        num_leads: Number of leads to review
        
    Returns:
        Time requirements and warnings
    """
    # Standards (based on maintaining quality)
    min_seconds_per_lead = 45  # Minimum 45 seconds per lead
    recommended_seconds = 90    # Recommended 90 seconds
    
    min_time_minutes = (num_leads * min_seconds_per_lead) / 60
    recommended_time_minutes = (num_leads * recommended_seconds) / 60
    
    return {
        'num_leads': num_leads,
        'min_time_minutes': min_time_minutes,
        'recommended_time_minutes': recommended_time_minutes,
        'min_seconds_per_lead': min_seconds_per_lead,
        'recommended_seconds_per_lead': recommended_seconds
    }


def track_review_quality(
    review_start_time: datetime,
    num_leads_reviewed: int,
    num_approved: int,
    num_rejected: int,
    run_id: str
):
    """
    Track review quality metrics
    Flag if team is rushing
    """
    review_log = "tmp/review_quality.jsonl"
    os.makedirs(os.path.dirname(review_log), exist_ok=True)
    
    review_end_time = datetime.now()
    duration_seconds = (review_end_time - review_start_time).total_seconds()
    seconds_per_lead = duration_seconds / num_leads_reviewed if num_leads_reviewed > 0 else 0
    
    # Quality indicators
    rejection_rate = num_rejected / num_leads_reviewed if num_leads_reviewed > 0 else 0
    is_rushing = seconds_per_lead < 45
    rejection_too_low = rejection_rate < 0.2  # Should reject at least 20%
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'num_leads': num_leads_reviewed,
        'approved': num_approved,
        'rejected': num_rejected,
        'rejection_rate': rejection_rate,
        'duration_seconds': duration_seconds,
        'seconds_per_lead': seconds_per_lead,
        'quality_flags': {
            'rushing': is_rushing,
            'low_rejection': rejection_too_low
        }
    }
    
    with open(review_log, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')
    
    return entry


def show_quality_enforcement_ui(num_leads: int):
    """
    Display quality enforcement warnings
    """
    st.subheader("⏱️ Quality Enforcement")
    
    time_req = enforce_review_time_limit(num_leads)
    
    st.info(f"""
**Quality Review Standards:**

Reviewing **{num_leads} leads**

- **Minimum time:** {time_req['min_time_minutes']:.1f} minutes ({time_req['min_seconds_per_lead']}s per lead)
- **Recommended:** {time_req['recommended_time_minutes']:.1f} minutes ({time_req['recommended_seconds_per_lead']}s per lead)

**Why this matters:**
- Rushing = quality decay
- Each lead needs proper evaluation
- Rejecting bad leads is MORE valuable than approving good ones
    """)
    
    st.warning("""
⚠️ **Quality Standards (Non-Negotiable):**

1. **Rejection quota:** Reject at least 20% of leads
   - If you're approving everything, you're not being selective enough
   
2. **Time per lead:** Minimum 45 seconds
   - Read the signal
   - Check the contact
   - Verify fit
   
3. **Document decisions:** Capture why you reject
   - Builds knowledge base
   - Trains the team
   - Improves AI over time

💡 **Remember:** You're paid for JUDGMENT, not SPEED
    """)


def show_quality_dashboard():
    """
    Dashboard showing team quality metrics over time
    """
    review_log = "tmp/review_quality.jsonl"
    
    if not os.path.exists(review_log):
        st.info("No review history yet")
        return
    
    st.subheader("📊 Quality Dashboard")
    
    reviews = []
    with open(review_log, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                reviews.append(json.loads(line))
            except:
                continue
    
    if not reviews:
        st.info("No reviews logged yet")
        return
    
    # Calculate metrics
    total_reviews = len(reviews)
    avg_rejection_rate = sum(r['rejection_rate'] for r in reviews) / total_reviews
    avg_time_per_lead = sum(r['seconds_per_lead'] for r in reviews) / total_reviews
    rushing_count = sum(1 for r in reviews if r['quality_flags']['rushing'])
    low_rejection_count = sum(1 for r in reviews if r['quality_flags']['low_rejection'])
    
    # Display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        color = "🟢" if avg_rejection_rate >= 0.2 else "🔴"
        st.metric(
            "Avg Rejection Rate",
            f"{color} {avg_rejection_rate * 100:.1f}%",
            help="Should be >= 20%"
        )
    
    with col2:
        color = "🟢" if avg_time_per_lead >= 45 else "🔴"
        st.metric(
            "Avg Time/Lead",
            f"{color} {avg_time_per_lead:.0f}s",
            help="Should be >= 45s"
        )
    
    with col3:
        st.metric(
            "Total Reviews",
            total_reviews
        )
    
    # Warnings
    if rushing_count > 0:
        st.error(f"""
🚨 **Quality Alert: Rushing Detected**

{rushing_count} review sessions were done too quickly (< 45s per lead).

**Impact:**
- Quality likely compromised
- Bad leads may have slipped through
- Client trust at risk

**Action:**
- Review those campaigns manually
- Enforce time minimums
- Team training needed
        """)
    
    if low_rejection_count > 0:
        st.warning(f"""
⚠️ **Quality Alert: Low Rejection Rate**

{low_rejection_count} sessions had rejection rate < 20%.

**This suggests:**
- Not being selective enough
- Approving borderline cases
- Quality standards slipping

**Action:**
- Reject more aggressively
- "When in doubt, reject"
- Document why you reject
        """)
    
    # Recent reviews
    with st.expander("📋 Recent Reviews"):
        for review in reviews[-10:]:
            st.write(f"**Run {review['run_id'][:8]}** - {review['timestamp'][:10]}")
            st.write(f"- Leads: {review['num_leads']} | Approved: {review['approved']} | Rejected: {review['rejected']}")
            st.write(f"- Time/lead: {review['seconds_per_lead']:.0f}s")
            
            if review['quality_flags']['rushing']:
                st.error("🚨 RUSHING")
            if review['quality_flags']['low_rejection']:
                st.warning("⚠️ LOW REJECTION RATE")
            
            st.divider()


def generate_quality_scorecard(run_id: str) -> str:
    """
    Generate quality scorecard for a campaign
    """
    review_log = "tmp/review_quality.jsonl"
    
    if not os.path.exists(review_log):
        return "No quality data available"
    
    # Find run
    run_review = None
    with open(review_log, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                review = json.loads(line)
                if review['run_id'] == run_id:
                    run_review = review
                    break
            except:
                continue
    
    if not run_review:
        return "No review data for this run"
    
    scorecard = f"""# Quality Scorecard
**Run ID:** {run_id}
**Date:** {run_review['timestamp'][:10]}

---

## Metrics

- **Total Leads Reviewed:** {run_review['num_leads']}
- **Approved:** {run_review['approved']}
- **Rejected:** {run_review['rejected']}
- **Rejection Rate:** {run_review['rejection_rate'] * 100:.1f}%

---

## Quality Assessment

**Time per Lead:** {run_review['seconds_per_lead']:.0f} seconds

"""
    
    if run_review['quality_flags']['rushing']:
        scorecard += "❌ **QUALITY ISSUE:** Rushing detected (< 45s per lead)\n\n"
    else:
        scorecard += "✅ Adequate review time\n\n"
    
    if run_review['quality_flags']['low_rejection']:
        scorecard += "⚠️ **QUALITY WARNING:** Low rejection rate (< 20%)\n\n"
    else:
        scorecard += "✅ Healthy rejection rate\n\n"
    
    scorecard += """
---

## Standards

- ✅ Minimum time: 45s per lead
- ✅ Minimum rejection: 20%
- ✅ Document all rejections

**Remember:** Rejecting bad leads is MORE valuable than approving good ones.
"""
    
    return scorecard
