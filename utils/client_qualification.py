"""
Client Qualification - Say no to bad-fit clients early
"""
import streamlit as st
from typing import Tuple, List


def qualify_client(
    target_desc: str,
    offering_desc: str,
    expected_volume: int
) -> Tuple[str, List[str]]:
    """
    Qualify if client is ready for this service
    
    Returns:
        (tier, red_flags)
        tier: "IDEAL", "WORKABLE", "HIGH_RISK", "NO_GO"
    """
    red_flags = []
    green_flags = []
    
    # ====================================================================
    # GREEN FLAGS (Ideal Client Indicators)
    # ====================================================================
    
    # Clear ICP
    if len(target_desc.split()) >= 10:
        green_flags.append("✅ Clear target description")
    else:
        red_flags.append("❌ Vague target - will waste runs")
    
    # Specific offering
    if len(offering_desc.split()) >= 15:
        green_flags.append("✅ Clear value proposition")
    else:
        red_flags.append("❌ Unclear offering - recipients won't care")
    
    # Reasonable expectations
    if expected_volume <= 20:
        green_flags.append("✅ Reasonable first campaign size")
    elif expected_volume <= 50:
        red_flags.append("⚠️ High volume - may dilute quality")
    else:
        red_flags.append("❌ Unrealistic volume expectations")
    
    # B2B focus
    if any(word in target_desc.lower() for word in ['b2b', 'saas', 'enterprise', 'companies']):
        green_flags.append("✅ B2B focus (fits service)")
    else:
        red_flags.append("⚠️ Not clearly B2B - may not work")
    
    # ====================================================================
    # RED FLAGS (High-Risk Client Indicators)
    # ====================================================================
    
    # Volume obsession
    volume_words = ['thousand', '1000', 'massive', 'huge', 'tons of', 'many']
    if any(word in target_desc.lower() + offering_desc.lower() for word in volume_words):
        red_flags.append("🚩 Volume-focused mindset - wrong expectations")
    
    # Tool comparison
    tool_words = ['apollo', 'zoominfo', 'lusha', 'database', 'list']
    if any(word in target_desc.lower() + offering_desc.lower() for word in tool_words):
        red_flags.append("🚩 Comparing to tools - wants volume, not judgment")
    
    # Spray-and-pray language
    spray_words = ['everyone', 'anyone', 'all', 'any company']
    if any(word in target_desc.lower() for word in spray_words):
        red_flags.append("🚩 Spray-and-pray mindset - bad fit for signal-based approach")
    
    # ====================================================================
    # TIER ASSIGNMENT
    # ====================================================================
    
    if len(red_flags) == 0 and len(green_flags) >= 3:
        tier = "IDEAL"
    elif len(red_flags) <= 2 and len(green_flags) >= 2:
        tier = "WORKABLE"
    elif len(red_flags) <= 3:
        tier = "HIGH_RISK"
    else:
        tier = "NO_GO"
    
    return tier, red_flags + green_flags


def show_client_qualification():
    """
    Show client qualification UI in Streamlit
    """
    st.subheader("🎯 Client Self-Assessment")
    
    st.info("""
    **Is this service right for you?**
    
    This tool is for clients who:
    ✅ Want quality over quantity
    ✅ Value judgment and rejection
    ✅ Understand outreach is learning, not magic
    
    NOT for clients who:
    ❌ Want 1,000 "leads" 
    ❌ Think more = better
    ❌ Expect instant ROI
    """)
    
    # Quick quiz
    with st.expander("📋 Quick Fit Quiz"):
        q1 = st.radio(
            "What matters more to you?",
            options=[
                "10 perfect-fit leads with strong signals",
                "100 leads from a database"
            ]
        )
        
        q2 = st.radio(
            "How do you measure success?",
            options=[
                "Conversations + learnings",
                "Number of emails sent"
            ]
        )
        
        q3 = st.radio(
            "Your offer is:",
            options=[
                "Clear problem → clear solution",
                "Still figuring it out"
            ]
        )
        
        q4 = st.radio(
            "Your ICP is:",
            options=[
                "Specific (e.g., 'B2B SaaS in fintech with 10-50 employees')",
                "Broad (e.g., 'any company that needs help')"
            ]
        )
        
        # Score
        score = 0
        if "perfect-fit" in q1:
            score += 1
        if "Conversations" in q2:
            score += 1
        if "Clear problem" in q3:
            score += 1
        if "Specific" in q4:
            score += 1
        
        st.divider()
        
        if score == 4:
            st.success("""
            ✅ **Perfect Fit!**
            
            You understand:
            - Quality > Quantity
            - Signal-based > Spray-and-pray
            - Learning > Volume
            
            This service will work great for you.
            """)
        elif score >= 2:
            st.warning("""
            ⚠️ **Workable, But...**
            
            You're close, but may need to adjust expectations.
            
            Before running:
            1. Clarify your ICP (who exactly?)
            2. Clarify your offer (what problem?)
            3. Accept 10 quality > 100 noise
            """)
        else:
            st.error("""
            ❌ **Not a Good Fit**
            
            You may be looking for:
            - Apollo / ZoomInfo (database tools)
            - Lemlist / Instantly (email automation)
            - VA services (volume-based outreach)
            
            This service is for:
            - Signal-based discovery (not database scraping)
            - Judgment-heavy selection (not volume)
            - Learning campaigns (not spray-and-pray)
            """)
