"""
Campaign Readiness Gate - Protect yourself from bad clients
Pause/warn/reject campaigns before they start
"""
from typing import Dict, List, Tuple
import streamlit as st
from datetime import datetime

def show_readiness_check(
    target_desc: str,
    offering_desc: str,
    num_companies: int,
    niche_mode: str,
) -> None:
    """Very simple placeholder readiness check UI."""
    st.subheader("📋 Campaign Readiness Check")

    issues = []

    if len(target_desc.strip()) < 20:
        issues.append("Target description is too short. Add more context about who you want to reach.")
    if len(offering_desc.strip()) < 20:
        issues.append("Offering description is too short. Explain the value you provide in more detail.")
    if num_companies <= 0:
        issues.append("Number of companies must be greater than 0.")
        # Allowed brain modes from the UI
    allowed_modes = [
        "DEFAULT",
        "BRAIN",
        "NICHE",
        "EXPERT",
        "Agency Sales Brain",
        "Founder Outreach Brain",
        "Service Provider Brain",
        "SaaS Sales Brain",
        "Agency Lead Brain",
        "Investor Outreach Brain",
        "Hiring Brain",
    ]

    if niche_mode not in allowed_modes:
        issues.append(f"Unexpected niche mode: {niche_mode}")


    if issues:
        st.error("Campaign is not fully ready:")
        for msg in issues:
            st.write(f"- {msg}")
    else:
        st.success("✅ Campaign looks ready to run.")

def evaluate_offer_clarity(offering: str) -> Tuple[int, List[str]]:
    """
    Score offer clarity (0-100)
    Returns: (score, issues)
    """
    issues = []
    score = 100
    
    # Must have outcome/benefit
    outcome_keywords = ['reduce', 'increase', 'improve', 'save', 'grow', 'faster', 'better', '%', 'x']
    has_outcome = any(kw in offering.lower() for kw in outcome_keywords)
    
    if not has_outcome:
        issues.append("No clear outcome/benefit (e.g., 'reduces by 40%')")
        score -= 30
    
    # Must be specific
    vague_words = ['help', 'assist', 'support', 'enable', 'empower', 'leverage', 'optimize', 'streamline']
    vague_count = sum(1 for word in vague_words if word in offering.lower())
    
    if vague_count >= 3:
        issues.append("Too vague - use specific outcomes instead of generic verbs")
        score -= 20
    
    # Minimum length
    if len(offering.split()) < 10:
        issues.append("Too short - describe what you do AND the outcome")
        score -= 15
    
    # Check for jargon overload
    jargon = ['synergy', 'leverage', 'ecosystem', 'paradigm', 'disrupt', 'revolutionary']
    jargon_count = sum(1 for word in jargon if word in offering.lower())
    
    if jargon_count >= 2:
        issues.append("Too much jargon - use plain language")
        score -= 10
    
    return max(0, score), issues


def evaluate_icp_clarity(target_desc: str) -> Tuple[int, List[str]]:
    """
    Score ICP clarity (0-100)
    Returns: (score, issues)
    """
    issues = []
    score = 100
    
    # Must have size indicator
    size_keywords = ['employees', 'people', 'team size', '10-50', '50-200', 'startup', 'enterprise']
    has_size = any(kw in target_desc.lower() for kw in size_keywords)
    
    if not has_size:
        issues.append("No company size specified")
        score -= 20
    
    # Must have industry/vertical
    if len(target_desc.split()) < 8:
        issues.append("Too vague - specify industry, size, stage, geography")
        score -= 25
    
    # Check for "everyone" language
    broad_words = ['all', 'any', 'every', 'anyone', 'everyone']
    if any(word in target_desc.lower() for word in broad_words):
        issues.append("Too broad - narrow down your target")
        score -= 30
    
    return max(0, score), issues


def check_fatal_objections(offering: str, target_desc: str) -> List[str]:
    """
    Identify fatal objections that will kill campaign
    """
    objections = []
    
    # Check if offering is too expensive for target
    if 'startup' in target_desc.lower() or 'small' in target_desc.lower():
        if 'enterprise' in offering.lower() or 'complex' in offering.lower():
            objections.append("FATAL: Offering sounds too expensive/complex for target (startups/small companies)")
    
    # Check if no clear ROI
    if not any(word in offering.lower() for word in ['save', 'reduce cost', 'increase revenue', 'roi', '%']):
        objections.append("WARNING: No clear ROI - hard to justify purchase")
    
    # Check if target is too broad
    if 'b2b' in target_desc.lower() and len(target_desc.split()) < 10:
        objections.append("WARNING: Target too broad ('B2B SaaS' = everyone)")
    
    return objections


def evaluate_campaign_readiness(
    offering: str,
    target_desc: str,
    sender_name: str,
    sender_company: str
) -> Dict:
    """
    Full campaign readiness check
    Returns readiness report
    """
    offer_score, offer_issues = evaluate_offer_clarity(offering)
    icp_score, icp_issues = evaluate_icp_clarity(target_desc)
    fatal_objections = check_fatal_objections(offering, target_desc)
    
    overall_score = (offer_score + icp_score) / 2
    
    # Determine readiness level
    if overall_score >= 80 and not fatal_objections:
        readiness = "READY"
        recommendation = "✅ Campaign ready to launch"
        can_proceed = True
    elif overall_score >= 60:
        readiness = "WARNING"
        recommendation = "⚠️ Campaign can proceed but fix issues for better results"
        can_proceed = True
    else:
        readiness = "BLOCK"
        recommendation = "🚫 PAUSE - Fix critical issues before launching"
        can_proceed = False
    
    return {
        'readiness': readiness,
        'overall_score': overall_score,
        'can_proceed': can_proceed,
        'recommendation': recommendation,
        'offer_score': offer_score,
        'offer_issues': offer_issues,
        'icp_score': icp_score,
        'icp_issues': icp_issues,
        'fatal_objections': fatal_objections,
        'improvements': generate_improvements(offer_issues, icp_issues, offering, target_desc)
    }


def generate_improvements(
    offer_issues: List[str],
    icp_issues: List[str],
    current_offer: str,
    current_icp: str
) -> Dict[str, str]:
    """
    Generate suggested improvements
    """
    improvements = {}
    
    if offer_issues:
        improvements['offer_rewrite'] = (
            f"Try: '{current_offer[:50]}... [ADD SPECIFIC OUTCOME]'\n"
            f"Example: 'reduces ticket volume by 40% and improves response time by 3x'"
        )
    
    if icp_issues:
        improvements['icp_rewrite'] = (
            f"Try: 'B2B SaaS companies, [INDUSTRY], [SIZE], [STAGE], [GEOGRAPHY], [PAIN SIGNAL]'\n"
            f"Example: 'B2B SaaS in fintech, 50-200 employees, Series A-B, US/EU, high support volume'"
        )
    
    return improvements


# ============================================================================
# 🆕 POST-CAMPAIGN & CLIENT MANAGEMENT (Problem #10 Fix)
# ============================================================================

def generate_campaign_brief(
    target_desc: str,
    offering_desc: str,
    num_companies: int,
    niche_mode: str,
    sender_name: str,
    sender_company: str
) -> str:
    """
    Generate campaign brief for client records
    """
    brief = f"""# Campaign Brief
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Client:** {sender_company}
**Campaign Manager:** {sender_name}

---

## Campaign Objective
Find and engage **{num_companies} companies** matching the target profile with strong buying signals.

## Target Profile (ICP)
{target_desc}

## Value Proposition
{offering_desc}

## Search Strategy
- **Brain Mode:** {niche_mode}
- **Signal Focus:** TIER1 and TIER2 only (operational signals)
- **Contact Level:** Founder/C-level/Problem owner preferred
- **Rejection Rate:** Expected 70-80% (quality over quantity)

---

## Expected Outcomes (Set Realistic Expectations)

### ✅ What Success Looks Like:
- **Conversations:** 20-30% open rate, 5-10% reply rate
- **Learning:** Which signals resonate, ICP refinement, messaging validation
- **Meetings:** 1-3 qualified meetings per 20 leads (varies by offer-market fit)
- **Insights:** Clear data on what works vs what doesn't

### ❌ What Success Is NOT:
- Volume of emails sent
- Database size
- "Leads" count without context
- Instant sales/ROI

---

## Success Metrics (Track These)

1. **Signal Quality:**
   - Which signal types got replies?
   - TIER1 vs TIER2 response rate
   
2. **Contact Accuracy:**
   - Right person reply rate
   - "Not the right person" rate
   
3. **Message Resonance:**
   - Which outreach angles worked?
   - Common objections received?
   
4. **Meeting Quality:**
   - Discovery calls booked
   - Qualified opportunities identified

---

## Follow-up Plan

**Week 1 (Days 1-7):**
- Send initial emails
- Monitor replies (peak response: days 2-4)
- Respond to questions
- Track signal patterns

**Week 2 (Days 8-14):**
- Send Follow-up #1 (to non-responders)
- Continue conversations from Week 1
- Note: Which signals are converting?

**Week 3 (Days 15-21):**
- Send Follow-up #2 (to non-responders)
- Schedule meetings from Week 2 replies
- Document learnings

**Week 4 (Days 22-28):**
- Send breakup email (final touchpoint)
- Complete campaign retrospective
- Plan adjustments for next campaign

---

## Campaign Retrospective Questions

After campaign completion, answer:

1. **What worked?**
   - Which signals got best response?
   - Which companies were most engaged?
   - What messaging resonated?

2. **What didn't work?**
   - Which signals were ignored?
   - What objections came up?
   - Wrong contact rate?

3. **What to change next time?**
   - Narrow/broaden target?
   - Different signals?
   - Adjust messaging angle?

---

## Important Reminders

🎯 **This is a LEARNING campaign, not a spray-and-pray operation.**

- Quality was prioritized over quantity
- Every company included has a REAL signal (not just "exists in database")
- Rejection rate is high BY DESIGN (filtered out noise)
- Outcomes = conversations + learning, NOT just "emails sent"

💡 **Why our approach is different:**

| Traditional Tools | Our Approach |
|------------------|-------------|
| 1,000 leads from database | 20 leads with live signals |
| Generic "works at company" | Specific problem owner |
| No timing context | Strong NOW signals |
| Spray-and-pray | Surgical precision |

---

**Next Steps:**
1. Review leads carefully
2. Customize where needed (add 20% personal touch)
3. Send via your email tool
4. Track responses with signal types
5. Report back learnings for next campaign

---

*Generated by Signal-Based Outreach System*
*Not a lead list. A hypothesis-driven campaign.*
"""
    
    return brief


def show_readiness_ui(
    target_desc: str,
    offering_desc: str,
    sender_name: str,
    sender_company: str,
    num_companies: int
) -> bool:
    """
    Display readiness check in Streamlit UI with visual feedback
    
    Returns:
        True if campaign can proceed, False otherwise
    """
    st.subheader("🎯 Campaign Readiness Check")
    
    # Run evaluation
    report = evaluate_campaign_readiness(
        offering_desc, target_desc,
        sender_name, sender_company
    )
    
    # Show overall score
    col1, col2, col3 = st.columns(3)
    
    with col1:
        score_color = "🟢" if report['overall_score'] >= 80 else "🟡" if report['overall_score'] >= 60 else "🔴"
        st.metric(
            "Overall Score",
            f"{score_color} {report['overall_score']:.0f}/100"
        )
    
    with col2:
        st.metric("Offer Clarity", f"{report['offer_score']:.0f}/100")
    
    with col3:
        st.metric("ICP Clarity", f"{report['icp_score']:.0f}/100")
    
    st.divider()
    
    # Show recommendation
    if report['readiness'] == "READY":
        st.success(report['recommendation'])
        
        # Show any minor warnings
        all_issues = report['offer_issues'] + report['icp_issues']
        if all_issues:
            with st.expander("💡 Optional Improvements"):
                for issue in all_issues:
                    st.write(f"- {issue}")
                
                if report['improvements']:
                    st.write("**Suggestions:**")
                    for key, suggestion in report['improvements'].items():
                        st.code(suggestion)
        
        return True
    
    elif report['readiness'] == "WARNING":
        st.warning(report['recommendation'])
        
        st.write("**Issues to address:**")
        for issue in report['offer_issues']:
            st.write(f"⚠️ Offer: {issue}")
        for issue in report['icp_issues']:
            st.write(f"⚠️ Target: {issue}")
        
        if report['improvements']:
            with st.expander("💡 How to Fix"):
                for key, suggestion in report['improvements'].items():
                    st.code(suggestion)
        
        # Show override option
        override = st.checkbox(
            "⚠️ I understand the risks and want to proceed anyway",
            help="Campaign may underperform if issues aren't fixed"
        )
        
        return override
    
    else:  # BLOCK
        st.error(report['recommendation'])
        
        st.write("**Critical issues (must fix):**")
        for issue in report['offer_issues']:
            st.write(f"🚫 Offer: {issue}")
        for issue in report['icp_issues']:
            st.write(f"🚫 Target: {issue}")
        
        if report['fatal_objections']:
            st.error("**Fatal objections detected:**")
            for objection in report['fatal_objections']:
                st.write(f"💀 {objection}")
        
        if report['improvements']:
            st.info("**How to fix:**")
            for key, suggestion in report['improvements'].items():
                st.code(suggestion)
        
        st.warning("""
💡 **Why we block:**

Bad campaigns = wasted API costs + frustrated clients + damaged reputation

Better to pause now, fix issues, then run a campaign that actually works.
        """)
        
        return False


def show_post_campaign_insights(results: Dict):
    """
    Display post-campaign insights and next steps
    """
    leads = results.get('leads', [])
    companies = results.get('companies', [])
    
    st.success("✅ Campaign Complete!")
    st.divider()
    
    st.subheader("📊 Campaign Insights")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Companies Found", len(companies))
    
    with col2:
        st.metric("Leads Generated", len(leads))
    
    with col3:
        tier1_count = sum(1 for c in companies if c.get('signal_tier') == 'TIER1')
        st.metric("TIER1 Signals", tier1_count)
    
    with col4:
        manual_count = sum(1 for l in leads if l.get('manual_lookup_required'))
        st.metric("Manual Lookup", manual_count)
    
    # Signal distribution
    with st.expander("🎯 Signal Distribution (What Signals We Found)"):
        signal_types = {}
        for company in companies:
            signal = company.get('signal', 'Unknown')[:60]
            signal_types[signal] = signal_types.get(signal, 0) + 1
        
        st.write("**Top Signals:**")
        for signal, count in sorted(signal_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            st.write(f"- {signal}: **{count}** companies")
    
    # Geographic distribution
    with st.expander("📍 Geographic Distribution"):
        geo_dist = {}
        for company in companies:
            geo = company.get('discovered_geo', 'unknown')
            geo_dist[geo] = geo_dist.get(geo, 0) + 1
        
        for geo, count in geo_dist.items():
            st.write(f"- {geo.title()}: **{count}** companies")
    
    st.divider()
    
    # Next steps
    st.subheader("🎯 Next Steps")
    
    st.info("""
**What to do now:**

1. **Review the leads** - Focus on TIER1 signals first
2. **Customize if needed** - AI wrote 80%, you add 20% personal touch
3. **Send emails** - Use your email tool (Gmail, Lemlist, etc.)
4. **Track responses** - Note which signals get replies
5. **Follow up** - Use the 3 follow-up angles provided

**Expected timeline:**
- Days 1-2: Replies start coming in
- Days 3-5: Peak response window
- Day 7-10: Send first follow-up
- Day 14-17: Send second follow-up
- Day 21: Send breakup email

**Success indicators:**
- 5-10% reply rate (1-2 replies per 20 emails)
- 1-2 meetings booked per 20 emails
- Clear learning about which signals work

❌ **NOT success:**
- Zero replies = messaging/targeting issue (fix before next campaign)
- High opens, no replies = weak CTA or value prop
- No opens = deliverability issue (check spam folder)
    """)
    
    # Campaign retrospective template
    with st.expander("📝 Campaign Retrospective Template"):
        st.markdown("""
### Track These Metrics:

**Response Tracking:**
- [ ] Open rate: ____%
- [ ] Reply rate: ____%
- [ ] Meeting booked: ___
- [ ] "Not interested": ___
- [ ] "Wrong person": ___

**Signal Performance:**
- Best performing signal: __________
- Worst performing signal: __________
- Unexpected insights: __________

**What Worked:**
- 
- 
- 

**What Didn't Work:**
- 
- 
- 

**Adjustments for Next Campaign:**
- 
- 
- 
        """)
