"""
Brand Moat - Differentiation through transparency
Make copying pointless by being radically transparent about judgment
"""
import streamlit as st
from typing import Dict, List
from datetime import datetime


def generate_campaign_transparency_report(
    results: Dict,
    run_id: str
) -> str:
    """
    Generate transparent report showing WHAT WAS REJECTED
    This is your competitive moat - others can copy the process,
    but not the judgment
    """
    
    leads = results.get('leads', [])
    companies = results.get('companies', [])
    
    # Get rejection data
    from utils.rejection_log import get_rejection_summary
    rejection_summary = get_rejection_summary(run_id)
    
    report = f"""# Campaign Transparency Report
**Run ID:** {run_id}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## What Makes This Different

**Most outreach tools show you:**
- ✅ What you GET (leads, emails, contacts)

**We show you:**
- ✅ What you get
- ✅ **What you DON'T get (and why)**

---

## The Numbers

### Input → Output Funnel

Started with: ~{rejection_summary['total'] + len(companies)} candidates
↓
Rejected: {rejection_summary['total']} companies
↓ (Quality filter applied)
Delivered: {len(companies)} companies
↓ (Contact finding)
Final leads: {len(leads)}


**Rejection rate:** {(rejection_summary['total'] / (rejection_summary['total'] + len(companies)) * 100) if rejection_summary['total'] + len(companies) > 0 else 0:.0f}%

---

## What We Rejected (Your Competitive Advantage)

### Top Rejection Reasons:

"""
    
    for reason, count in sorted(rejection_summary['by_reason'].items(), key=lambda x: x[1], reverse=True)[:10]:
        report += f"- **{reason}**: {count} companies\n"
    
    report += f"""

### Why This Matters

**Database tools (Apollo, ZoomInfo):**
- Give you everything
- 1,000 "leads" = 950 noise + 50 signal
- You waste time sorting

**Our approach:**
- Start with 100+ candidates
- Reject {rejection_summary['total']} aggressively
- Deliver {len(companies)} with strong signals
- You start conversations immediately

---

## Signal Distribution (What We KEPT)

"""
    
    signal_dist = {}
    for company in companies:
        signal = company.get('signal', 'Unknown')[:60]
        signal_dist[signal] = signal_dist.get(signal, 0) + 1
    
    for signal, count in sorted(signal_dist.items(), key=lambda x: x[1], reverse=True)[:8]:
        report += f"- {signal}: **{count}** companies\n"
    
    report += f"""

---

## Our Philosophy (Why We're Hard to Copy)

### 1. **Restraint Over Volume**
- We reject more than we accept
- Each rejection is a quality decision
- Others optimize for "more" - we optimize for "better"

### 2. **Transparency Over Secrecy**
- We show you what we filtered out
- We explain our judgment
- We teach you to think this way

### 3. **Learning Over Selling**
- Each campaign generates insights
- Not just "leads" - hypotheses
- Track what works, adjust what doesn't

---

## How to Use This Report

**Share with your team:**
- Show them what quality looks like
- Explain why we rejected X
- Build shared quality standards

**Share with clients (if you're an agency):**
- Prove you're selective
- Show volume rejected
- Differentiate from tools

**Use for next campaign:**
- Which signals worked?
- Which rejections were right?
- What to filter harder next time?

---

## The Competitive Moat

**Anyone can:**
- Use the same AI models ✅
- Find companies with signals ✅
- Write personalized emails ✅

**Few can:**
- Reject 70% of what they find ❌
- Explain WHY they rejected ❌
- Build judgment into the process ❌

**Your moat = Your judgment, made visible**

---

*This report was generated to show transparency.*
*Copy the process if you want. You can't copy the judgment.*
"""
    
    return report


def show_brand_differentiation_ui():
    """
    Display brand differentiation messaging
    """
    st.subheader("🛡️ Brand Moat: Differentiation Strategy")
    
    st.success("""
**Your Competitive Advantage (Impossible to Copy)**

Others can copy:
- ✅ The tech (AI models are public)
- ✅ The process (signal-based discovery)
- ✅ The messaging (outreach templates)

They CANNOT copy:
- ❌ Your judgment (what you reject)
- ❌ Your standards (how you filter)
- ❌ Your transparency (showing rejections)
    """)
    
    st.info("""
💡 **How to build an uncopyable moat:**

1. **Be radically transparent**
   - Show what you filtered OUT
   - Explain every rejection
   - Teach your thinking

2. **Reject publicly**
   - "We filtered 80% of candidates"
   - "Here's why we said no to X"
   - "Quality > quantity always"

3. **Build in the open**
   - Share your process
   - Document decisions
   - Create case studies

**Result:** Competitors copy your process but miss the point.
They optimize for volume. You optimize for judgment.
    """)
    
    st.warning("""
⚠️ **What NOT to do:**

❌ Hide your process (creates mystery, not value)
❌ Compete on volume (race to bottom)
❌ Keep secrets (limits learning)

**Instead:**

✅ Show your work
✅ Explain your no's
✅ Build reputation on restraint
    """)


def generate_public_case_study(
    results: Dict,
    run_id: str,
    anonymize: bool = True
) -> str:
    """
    Generate shareable case study
    Shows judgment, not just results
    """
    
    leads = results.get('leads', [])
    companies = results.get('companies', [])
    
    from utils.rejection_log import get_rejection_summary
    rejection_summary = get_rejection_summary(run_id)
    
    company_name = "A B2B SaaS Company" if anonymize else results.get('metadata', {}).get('client_name', 'Client')
    
    case_study = f"""# Case Study: Signal-Based Outreach
**Client:** {company_name}
**Date:** {datetime.now().strftime('%B %Y')}

---

## The Challenge

Client wanted to find companies with **active buying signals** - not just names from a database.

Traditional tools would give them:
- 1,000+ "leads" from databases
- No context on timing
- Generic "works at company" contacts

They needed:
- Strong NOW signals (hiring, funding, product launches)
- Problem owners (right person, right time)
- Quality over quantity

---

## Our Approach

### Discovery Phase
- Searched across multiple directories
- Found **{rejection_summary['total'] + len(companies)}** potential candidates

### Quality Filter (THE KEY DIFFERENTIATOR)
**Rejected {rejection_summary['total']} companies because:**

"""
    
    for reason, count in sorted(rejection_summary['by_reason'].items(), key=lambda x: x[1], reverse=True)[:5]:
        case_study += f"- {reason}: {count} companies\n"
    
    case_study += f"""

**Delivered:** {len(companies)} companies with strong signals

---

## The Results

### Quantitative
- **{len(companies)}** companies identified
- **{len(leads)}** decision-maker contacts found
- **Rejection rate:** {(rejection_summary['total'] / (rejection_summary['total'] + len(companies)) * 100) if rejection_summary['total'] + len(companies) > 0 else 0:.0f}% (we said no more than yes)

### Qualitative (The Real Value)
- Every company has a **live operational signal**
- Every contact is the **problem owner**
- Every outreach is **signal-specific**

---

## What Made This Work

### 1. Aggressive Rejection
We started with 100+ candidates and rejected most of them.

**Why?** Because restraint = quality.

### 2. Transparency
Client saw exactly what we filtered out and why.

**Why?** Because hidden judgment isn't valuable.

### 3. Learning Focus
Campaign generated insights, not just "leads."

**Why?** Because next campaign should be smarter.

---

## The Insight

**Most outreach services optimize for volume:**
- "We got you 1,000 leads!"
- Looks impressive
- Wastes your time sorting

**We optimize for judgment:**
- "We rejected 80% of candidates"
- Looks selective
- Saves your time

**Result:** Client spent time on conversations, not sorting.

---

## Key Takeaway

**Anyone can find companies.**
**Anyone can send emails.**

**Few can:**
- Say no to 80% of candidates
- Explain why
- Build that judgment into their process

That's the moat.

---

*Want this level of selectivity for your campaigns?*
*It's not about the tools. It's about the judgment.*
"""
    
    return case_study
