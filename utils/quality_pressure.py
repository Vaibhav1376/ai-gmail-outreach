"""
Quality Pressure System - Enforce "If quality feels easy, we're doing it wrong"
The meta-problem that kills all quality businesses
"""
import streamlit as st
from typing import Dict, List
from datetime import datetime


def calculate_quality_pressure_score(
    rejection_rate: float,
    avg_review_time_seconds: float,
    manual_override_rate: float,
    client_complained_about_volume: bool
) -> Dict:
    """
    Calculate if you're maintaining quality pressure
    
    Quality pressure = intentional difficulty in saying yes
    
    Args:
        rejection_rate: Percentage of candidates rejected (0-1)
        avg_review_time_seconds: Time spent per lead review
        manual_override_rate: How often humans override AI
        client_complained_about_volume: Red flag - client wants more
    
    Returns:
        Quality pressure assessment
    """
    
    # Healthy ranges
    target_rejection_rate = 0.7  # Should reject 70%+
    target_review_time = 60  # 60+ seconds per lead
    healthy_override_rate = (0.10, 0.30)  # 10-30% override is good
    
    warnings = []
    score = 100
    
    # Check rejection rate
    if rejection_rate < 0.5:
        warnings.append(f"🚨 CRITICAL: Rejection rate too low ({rejection_rate * 100:.0f}% < 50%)")
        score -= 40
    elif rejection_rate < target_rejection_rate:
        warnings.append(f"⚠️ Rejection rate below target ({rejection_rate * 100:.0f}% < 70%)")
        score -= 20
    
    # Check review time
    if avg_review_time_seconds < 30:
        warnings.append(f"🚨 CRITICAL: Rushing through reviews ({avg_review_time_seconds:.0f}s < 30s)")
        score -= 30
    elif avg_review_time_seconds < target_review_time:
        warnings.append(f"⚠️ Review time too fast ({avg_review_time_seconds:.0f}s < 60s)")
        score -= 15
    
    # Check override rate
    if manual_override_rate < healthy_override_rate[0]:
        warnings.append(f"⚠️ Too automated - humans not questioning AI enough ({manual_override_rate * 100:.0f}%)")
        score -= 15
    elif manual_override_rate > healthy_override_rate[1]:
        warnings.append(f"⚠️ Too manual - AI not reliable ({manual_override_rate * 100:.0f}%)")
        score -= 10
    
    # Check client pressure
    if client_complained_about_volume:
        warnings.append("🚨 CLIENT PUSHING FOR VOLUME - Resist or lose quality edge")
        score -= 25
    
    # Assess
    if score >= 80:
        status = "HEALTHY"
        message = "✅ Quality pressure maintained"
    elif score >= 60:
        status = "AT_RISK"
        message = "⚠️ Quality pressure weakening"
    else:
        status = "FAILING"
        message = "🚨 Quality pressure collapsed - urgent intervention needed"
    
    return {
        'score': max(0, score),
        'status': status,
        'message': message,
        'warnings': warnings,
        'recommendations': generate_quality_recommendations(warnings)
    }


def generate_quality_recommendations(warnings: List[str]) -> List[str]:
    """
    Generate specific recommendations based on warnings
    """
    recommendations = []
    
    for warning in warnings:
        if "Rejection rate too low" in warning:
            recommendations.append("INCREASE rejection threshold - reject anything borderline")
        
        if "Rushing" in warning:
            recommendations.append("ENFORCE minimum 60s per lead - build it into UI")
        
        if "Too automated" in warning:
            recommendations.append("ADD manual review steps - don't trust AI blindly")
        
        if "CLIENT PUSHING" in warning:
            recommendations.append("EDUCATE client or fire them - volume kills quality")
    
    if not recommendations:
        recommendations.append("Maintain current standards - quality pressure is healthy")
    
    return recommendations


def show_quality_pressure_dashboard(
    rejection_rate: float = 0.0,
    avg_review_time: float = 0.0,
    override_rate: float = 0.0
):
    """
    Display quality pressure monitoring
    """
    st.subheader("⚖️ Quality Pressure Monitor")
    
    st.error("""
🎯 **THE META-PROBLEM**

**Every successful business faces this:**

1. Quality works (hard choices = value)
2. Growth pressure (need more revenue)
3. Volume temptation ("just say yes more")
4. Quality decays (silent, gradual)
5. Commodity business (compete on price)

**This system prevents that.**
    """)
    
    # Calculate score
    assessment = calculate_quality_pressure_score(
        rejection_rate,
        avg_review_time,
        override_rate,
        False  # Track this separately
    )
    
    # Display score
    if assessment['status'] == 'HEALTHY':
        st.success(f"""
{assessment['message']}

**Quality Pressure Score:** {assessment['score']}/100

You're maintaining the discipline that creates value.
        """)
    elif assessment['status'] == 'AT_RISK':
        st.warning(f"""
{assessment['message']}

**Quality Pressure Score:** {assessment['score']}/100

**Warnings detected - address before quality collapses.**
        """)
    else:
        st.error(f"""
{assessment['message']}

**Quality Pressure Score:** {assessment['score']}/100

**🚨 URGENT: Quality standards are failing**
        """)
    
    # Show warnings
    if assessment['warnings']:
        st.write("**Issues Detected:**")
        for warning in assessment['warnings']:
            st.write(f"- {warning}")
    
    # Show recommendations
    if assessment['recommendations']:
        st.write("**Actions Required:**")
        for rec in assessment['recommendations']:
            st.write(f"✅ {rec}")
    
    st.divider()
    
    # Quality mantras
    st.info("""
💡 **Quality Mantras (Pin These)**

1. **"If quality feels easy, we're doing something wrong"**
   - Saying yes should be hard
   - Rejection should be frequent
   - Each acceptance needs justification

2. **"More is the enemy of better"**
   - More leads ≠ more value
   - More campaigns ≠ more learning
   - More clients ≠ more profit

3. **"Reject first, question later"**
   - Default to no
   - Make "yes" require evidence
   - When in doubt, reject

4. **"We're paid for what we DON'T include"**
   - Filtering is the value
   - Anyone can find companies
   - We reject 80% - that's the skill

5. **"Quality decays silently - measure aggressively"**
   - Track rejection rate daily
   - Monitor review time
   - Catch slippage early
    """)


def show_more_vs_better_comparison():
    """
    Visual comparison of "more" vs "better" paths
    """
    st.subheader("📊 The Fork in the Road")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
### 🔴 The "More" Path (Death Spiral)

**Year 1:**
- 10 campaigns, high quality
- $1000/campaign
- Happy clients

**Year 2:**
- Pressure to scale
- Lower standards ("just say yes more")
- 50 campaigns, declining quality
- $500/campaign (price pressure)

**Year 3:**
- Competing on volume
- 200 campaigns, commodity service
- $200/campaign
- Burning out

**Year 4:**
- Replaced by AI tools
- Can't compete on price
- Business dies

**Outcome:** 💀 Commodity, burned out, replaced
        """)
    
    with col2:
        st.markdown("""
### 🟢 The "Better" Path (Value Creation)

**Year 1:**
- 10 campaigns, high quality
- $1000/campaign
- Happy clients

**Year 2:**
- Maintain standards
- Document patterns
- 30 campaigns, same quality
- $1500/campaign (premium for consistency)

**Year 3:**
- Reputation for judgment
- Case studies prove value
- 40 campaigns, selective clients
- $2500/campaign

**Year 4:**
- Industry leader
- Known for saying no
- 50 campaigns, premium only
- $3000/campaign

**Outcome:** 🚀 Premium positioning, sustainable, differentiated
        """)
    
    st.warning("""
⚠️ **The Choice Is Daily**

Every day you choose:
- Say yes to borderline case? (MORE)
- Reject and explain why? (BETTER)

Every campaign you choose:
- Accept volume-focused client? (MORE)
- Fire them for culture fit? (BETTER)

Every quarter you choose:
- Automate judgment? (MORE)
- Build team judgment? (BETTER)

**The "more" path is always easier in the moment.**
**The "better" path creates lasting value.**
    """)


def enforce_quality_circuit_breaker(
    recent_rejection_rate: float,
    campaigns_this_week: int
) -> Dict:
    """
    Circuit breaker - stops operations if quality drops
    
    This is the nuclear option but necessary
    """
    
    # Thresholds
    min_rejection_rate = 0.4  # If below 40%, something is very wrong
    max_campaigns_per_week = 10  # If above 10, likely rushing
    
    should_pause = False
    reasons = []
    
    if recent_rejection_rate < min_rejection_rate:
        should_pause = True
        reasons.append(f"Rejection rate critically low ({recent_rejection_rate * 100:.0f}%)")
    
    if campaigns_this_week > max_campaigns_per_week:
        should_pause = True
        reasons.append(f"Volume too high ({campaigns_this_week} campaigns this week)")
    
    return {
        'should_pause': should_pause,
        'reasons': reasons,
        'message': generate_circuit_breaker_message(should_pause, reasons)
    }


def generate_circuit_breaker_message(should_pause: bool, reasons: List[str]) -> str:
    """
    Generate circuit breaker message
    """
    if not should_pause:
        return "✅ Quality within acceptable range"
    
    message = """
🚨 **CIRCUIT BREAKER TRIGGERED**

**Operations paused automatically due to quality concerns:**

"""
    
    for reason in reasons:
        message += f"- {reason}\n"
    
    message += """

**Required actions before resuming:**

1. Review last 5 campaigns manually
2. Identify where standards slipped
3. Team training session
4. Adjust rejection thresholds
5. Manual approval required for next 3 campaigns

**This pause protects:**
- Your reputation
- Client outcomes
- Long-term value

**"Better to pause than deliver garbage"**
    """
    
    return message
