"""
Service-First Philosophy - Resist premature SaaS-ification
Keep the human judgment that creates value
"""
import streamlit as st
from typing import Dict


def show_saas_readiness_check(
    total_campaigns_run: int,
    avg_manual_override_rate: float,
    quality_consistency_score: float
) -> Dict:
    """
    Check if you're ready to SaaS-ify (spoiler: you're probably not)
    
    Args:
        total_campaigns_run: Number of campaigns completed
        avg_manual_override_rate: How often human overrides AI (0-1)
        quality_consistency_score: How consistent quality is (0-1)
    
    Returns:
        Readiness assessment
    """
    
    # Thresholds
    min_campaigns = 100  # Need at least 100 campaigns before considering SaaS
    max_override_rate = 0.15  # If overriding AI >15%, judgment not stable
    min_consistency = 0.85  # Need 85%+ consistency
    
    ready = (
        total_campaigns_run >= min_campaigns and
        avg_manual_override_rate <= max_override_rate and
        quality_consistency_score >= min_consistency
    )
    
    blockers = []
    
    if total_campaigns_run < min_campaigns:
        blockers.append(f"Need {min_campaigns - total_campaigns_run} more campaigns (currently {total_campaigns_run})")
    
    if avg_manual_override_rate > max_override_rate:
        blockers.append(f"Manual override rate too high ({avg_manual_override_rate * 100:.0f}% > {max_override_rate * 100:.0f}%)")
    
    if quality_consistency_score < min_consistency:
        blockers.append(f"Quality consistency too low ({quality_consistency_score * 100:.0f}% < {min_consistency * 100:.0f}%)")
    
    return {
        'ready_for_saas': ready,
        'blockers': blockers,
        'recommendation': 'STAY SERVICE' if not ready else 'CONSIDER PRODUCT',
        'reasoning': generate_saas_reasoning(ready, blockers)
    }


def generate_saas_reasoning(ready: bool, blockers: list[str]) -> str:
    """
    Explain SaaS readiness decision
    """
    if ready:
        return """
✅ **You might be ready to productize**

Your judgment is stable enough to encode into software.

BUT - ask yourself:
1. Is your edge still the JUDGMENT, or just the execution?
2. Will automation make you compete with tools?
3. Can you maintain quality at scale?

If yes to all → Consider productization
If no to any → Stay service, charge more
        """
    else:
        return f"""
🚫 **Not ready for SaaS (and that's GOOD)**

**Blockers:**
{chr(10).join(f'- {b}' for b in blockers)}

**Why this is good:**
- Your edge is still judgment (high value)
- Clients pay for your decisions (not automation)
- You can charge premium service rates

**What to do instead:**
1. Run more campaigns
2. Document judgment patterns
3. Build knowledge base
4. Train team on your standards
5. Charge MORE, not automate

**When judgment is stable (100+ campaigns):**
- THEN consider productization
- THEN you'll have real IP to encode
- THEN automation won't kill your edge
        """


def show_service_vs_product_ui():
    """
    Display service-first philosophy
    """
    st.subheader("🎯 Service vs Product: Strategic Decision")
    
    st.error("""
⚠️ **Premature SaaS-ification Kills Value**

**The Pattern:**
1. Service works (judgment creates value)
2. Pressure to "scale" and "automate"
3. Build SaaS product
4. Remove human judgment
5. Compete with tools
6. Race to bottom on price
7. Value destroyed

**Better path:**
1. Service works
2. Get really good at judgment
3. Document patterns
4. Train team
5. Charge MORE for judgment
6. SaaS later (if ever)
    """)
    
    st.success("""
✅ **When to Stay Service (Probably Forever)**

**Stay service if:**
- Your edge is JUDGMENT
- Clients pay for your decisions
- Quality requires human oversight
- Each campaign is different
- Learning is ongoing

**These are FEATURES, not bugs.**

**Charge accordingly:**
- $500-2000 per campaign (service)
- Not $50/month (SaaS competing with Apollo)
    """)
    
    st.info("""
💡 **The Service-First Playbook**

**Phase 1 (Campaigns 1-50): Learn**
- Run campaigns manually
- Document every decision
- Build knowledge base
- Find patterns

**Phase 2 (Campaigns 51-100): Systematize**
- Create decision frameworks
- Train team members
- Automate execution (not judgment)
- Maintain quality

**Phase 3 (Campaigns 101+): Scale Service**
- Team can replicate quality
- Judgment is documented
- Automation supports (doesn't replace)
- **Keep charging service rates**

**Phase 4 (Maybe Never): Consider Product**
- ONLY if judgment is 90%+ codifiable
- ONLY if automation doesn't kill edge
- ONLY if you can compete on features (not just data)

**Most valuable companies stay in Phase 3 forever.**
    """)
    
    # Decision matrix
    st.subheader("📊 Service vs SaaS Decision Matrix")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
**🟢 Stay Service If:**

- [ ] Edge is human judgment
- [ ] Each campaign unique
- [ ] Quality needs oversight
- [ ] Clients value decisions
- [ ] Manual override >10%
- [ ] Premium pricing works
- [ ] Team is key asset

**Outcome:** High-value service business
        """)
    
    with col2:
        st.markdown("""
**🔵 Consider SaaS If:**

- [ ] Judgment is codified
- [ ] Process is repeatable
- [ ] Quality is consistent
- [ ] Decisions are automated
- [ ] Manual override <5%
- [ ] Scale is the goal
- [ ] Software is the asset

**Outcome:** Product company
        """)


def generate_pricing_guidance(phase: str) -> str:
    """
    Pricing guidance based on service maturity
    """
    pricing_guide = {
        'phase_1': """
# Pricing Guidance: Phase 1 (Learning)

**Current State:** Campaigns 1-50, building judgment

**Pricing Strategy:**
- **Campaign price:** $300-800
- **Reasoning:** You're still learning, but providing value
- **Positioning:** "Custom research + outreach"

**What NOT to do:**
- ❌ Don't compete on price
- ❌ Don't offer "unlimited" anything
- ❌ Don't promise volume

**What to emphasize:**
- ✅ Learning + insights
- ✅ Quality over quantity
- ✅ Signal-based approach
        """,
        
        'phase_2': """
# Pricing Guidance: Phase 2 (Systematizing)

**Current State:** Campaigns 51-100, patterns documented

**Pricing Strategy:**
- **Campaign price:** $800-1500
- **Reasoning:** Proven process, consistent quality
- **Positioning:** "Signal-based lead generation with proven playbook"

**What's changed:**
- ✅ You have case studies
- ✅ Process is documented
- ✅ Quality is consistent
- ✅ Team can deliver

**Value prop:**
- Not "we'll find you leads"
- But "we'll reject 80% and deliver only strong signals"
        """,
        
        'phase_3': """
# Pricing Guidance: Phase 3 (Scale Service)

**Current State:** Campaigns 101+, judgment encoded, team trained

**Pricing Strategy:**
- **Campaign price:** $1500-3000+
- **Reasoning:** Maximum value, proven outcomes
- **Positioning:** "The anti-database approach to outreach"

**At this point:**
- ✅ Premium positioning
- ✅ Case studies prove ROI
- ✅ Team delivers without you
- ✅ Rejection rate is a feature

**Competitive moat:**
- Others copy your process → doesn't matter
- They can't copy your judgment
- They can't copy your brand (rejection as value)
        """
    }
    
    return pricing_guide.get(phase, "Unknown phase")
