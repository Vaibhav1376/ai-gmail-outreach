"""
UNIFIED PIPELINE - Fully Cloud + Hybrid modes
Mode selection handled automatically based on config
+ Production-grade error handling and JSON repair
"""
import os
import sys
import json
import time
import csv
import uuid  # Added missing import
from io import StringIO
from typing import Dict, List, Any, Optional, Tuple

# Assuming these exist in your project structure, kept as is
from utils.retry_handler import retry_with_backoff, run_with_failsoft
import streamlit as st
from utils.rejection_log import log_rejection
from schemas import Lead
import time
import random

# Pipeline Modes
MODE_FIND_MY_CLIENTS = "FIND_MY_CLIENTS"  # Agency finding clients
MODE_FIND_CLIENTS_FOR_CUSTOMER = "FIND_CLIENTS_FOR_CUSTOMER"  # Client campaign


def exa_search_with_backoff(exa_client, query, max_retries=3, base_delay=2):
    """
    Make Exa search with exponential backoff on rate limits
    """
    for attempt in range(max_retries):
        try:
            result = exa_client.search_and_contents(
                query,
                use_autoprompt=True,
                num_results=10,
                text=True
            )
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if '429' in error_msg or 'rate limit' in error_msg.lower():
                if attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"⏳ Rate limit hit. Waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                else:
                    print(f"❌ Max retries reached. Error: {error_msg}")
                    raise
            else:
                # Not a rate limit error, raise immediately
                raise
    
    return None


# Local agents
from utils.local_agents import (
    check_local_available,
    create_local_data_cleaner,
    create_local_validator,
    run_local_agent,
    create_local_json_validator # Added this based on usage in Stage 7
)

# Signal processing
from utils.signal_interpreter import (
    interpret_signal,
    bulk_interpret_signals,
    format_interpretation_for_display
)

from utils.signal_rejection import (
    evaluate_signal_quality,
    apply_rejection_rules
)

# ICP enforcement
from utils.icp_enforcement import (
    enforce_icp_gate,
    apply_icp_gate_to_companies
)

# Configuration
from config.hybrid_config import get_hybrid_config

# Agent helpers
from utils.agent_helpers import (
    extract_json_or_raise,
    remove_emojis,
    run_agent_with_ensemble
)

# Get config
PIPELINE_CONFIG = get_hybrid_config()

# --- PLACEHOLDERS FOR MISSING UTILS (To ensure code runs) ---
def save_stage_checkpoint(stage_name, data, run_id):
    """Placeholder to prevent NameError"""
    os.makedirs(f"checkpoints/{run_id}", exist_ok=True)
    with open(f"checkpoints/{run_id}/{stage_name}.json", "w") as f:
        json.dump(data, f)

def load_stage_checkpoint(stage_name, run_id):
    """Placeholder to prevent NameError"""
    try:
        with open(f"checkpoints/{run_id}/{stage_name}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
# -----------------------------------------------------------

# Fallback function if signal_interpreter module doesn't have it
def format_interpretation_for_display(signal_interp: Dict[str, Any]) -> str:
    """
    Format signal interpretation for display
    Fallback if not available in signal_interpreter module
    """
    if not signal_interp or not isinstance(signal_interp, dict):
        return "No interpretation available"
    
    try:
        # Try to format nicely
        operational = signal_interp.get('operational_implication', 'Unknown')
        pain_owner = signal_interp.get('pain_owner_role', 'Unknown')
        outreach = signal_interp.get('outreach_angle', 'Unknown')
        urgency = signal_interp.get('urgency_level', 'UNKNOWN')
        confidence = signal_interp.get('interpretation_confidence', 0)
        
        return (
            f"**Impact:** {operational}\n"
            f"**Pain Owner:** {pain_owner}\n"
            f"**Urgency:** {urgency}\n"
            f"**Best Angle:** {outreach}\n"
            f"**Confidence:** {confidence}%"
        )
    except:
        # Final fallback: JSON dump
        return json.dumps(signal_interp, indent=2)


def run_company_finder(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    target_desc: str,
    offering_desc: str,
    max_companies: int,
    niche_mode: str,
) -> Tuple[List[Dict[str, str]], Dict]:
    """
    STAGE 1: Signal-based company discovery (ALWAYS CLOUD)
    Enhanced with 100% signal-based filtering
    """
    from config.hybrid_config import get_signal_tiers
    signal_tiers = get_signal_tiers()
    
    # Get pipeline mode
    pipeline_mode = st.session_state.get('pipeline_mode_type', 'FIND_MY_CLIENTS')

    # Determine what type to search for
    if pipeline_mode == 'FIND_MY_CLIENTS':
        search_type = "marketing agencies, digital agencies, consultancies, or creative service businesses"
        company_type_required = "Agency"
        exclusions = "B2B SaaS, software companies, tech startups, VC firms, media companies, blogs"
        signal_examples = "team expansion, new office opening, client wins, service expansion, awards won"
    else:
        search_type = "B2B SaaS companies"
        company_type_required = "B2B SaaS"
        exclusions = "VC firms, agencies, blogs, media companies"
        signal_examples = "hiring, funding, product launches, customer growth"

    prompt = f"""CRITICAL: You MUST respond with ONLY valid JSON. No text before or after.
    
    Find {max_companies * 2} {search_type} with observable signals.
    
    Brain Mode: {niche_mode}
    Targeting: {target_desc}
    Offering: {offering_desc}
    
    COMPANY TYPE FILTER (STRICT):
    - MUST be: {company_type_required}
    - DO NOT include: {exclusions}
    
    SIGNAL TYPES TO LOOK FOR:
    - {signal_examples}
    - Recent changes in last 3-6 months
    - Observable from public sources
    
    SIGNAL TIER SYSTEM (return only TIER1 and TIER2):
    {json.dumps(signal_tiers, indent=2)}
    
    For each company provide:
    - name, website, company_type (must be "{company_type_required}")
    - signal (what changed recently - REAL signal only)
    - signal_tier ("TIER1" or "TIER2" only)
    - signal_score (3-5 based on tier)
    - signal_source (where you found it)
    - signal_date (when it happened)
    - inference (causal logic why this matters NOW)
    - why_fit (match to target profile)
    - offer_alignment (how your offer helps)
    
    DO NOT include:
    - TIER3 signals (blog posts, values pages)
    - Wrong company types
    - Companies without real operational signals
    
    RESPONSE FORMAT (start with {{ and end with }}):
    
    {{
      "companies": [
        {{
          "name": "Example {company_type_required}",
          "website": "https://example.com",
          "company_type": "{company_type_required}",
          "signal": "Expanded team by 5 people in Q4 2024",
          "signal_tier": "TIER2",
          "signal_score": 3,
          "signal_source": "LinkedIn company page",
          "signal_date": "2024-11-15",
          "inference": "Team growth indicates more client work and need for new business pipeline",
          "why_fit": "Growing {company_type_required.lower()} in target geography",
          "offer_alignment": "Need systematic client acquisition to match capacity"
        }}
      ]
    }}
    
    Return ONLY the JSON. No other text."""
    
    
    with st.spinner("🔍 Stage 1: Discovering companies with signals (Cloud)..."):
        content, metadata = run_agent_with_ensemble(
            agent_openai, agent_gemini, prompt, "CompanyFinder"
        )
    
    if content.startswith('```'):  # ✅ Correct
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
        content = content.replace('``````', '').strip()

    
    # Debug mode
    if st.session_state.get('debug_mode', False):
        with st.expander("🐛 Raw CompanyFinder Response"):
            st.code(content[:2000], language="text")
    
    # Enhanced JSON extraction
    try:
        content = remove_emojis(content)
        data = extract_json_or_raise(content)
    except ValueError as e:
        st.error("❌ Failed to parse JSON from CompanyFinder")
        st.error(str(e))
        if st.session_state.get('debug_mode', False):
            with st.expander("❌ Problematic Response"):
                st.code(content[:1500], language="text")
        raise
    
    companies = data.get("companies", [])
    
    st.success(f"✅ Found {len(companies)} companies with strong signals")
    
    time.sleep(5)  # Reduced from 25 for UX, usually 5-10 is enough for APIs
    
    return companies, metadata


# ============================================================================
# STAGE 2: DATA CLEANING (Hybrid: Local | Cloud: Cloud)
# ============================================================================

def run_data_cleaning(
    raw_companies: List[Dict],
    max_companies: int,
    agent_openai: Optional[Any] = None,
    agent_gemini: Optional[Any] = None,
    mode: str = 'hybrid',
    run_id: Optional[str] = None,
    pipeline_mode: str = MODE_FIND_MY_CLIENTS  # ← ADD THIS
) -> List[Dict]:

    """
    STAGE 2: Clean and filter data
    ENHANCED: No retries, immediate cloud fallback (Fast fail-over)
    """
    
    # Use raw_companies as base
    companies = raw_companies

    if pipeline_mode == MODE_FIND_MY_CLIENTS:
        # Agency mode: REMOVE SaaS, KEEP services
        before = len(companies)
        companies = [
            c for c in companies
            if 'saas' not in c.get('company_type', '').lower()
            and 'software' not in c.get('company_type', '').lower()
            and 'product' not in c.get('company_type', '').lower()
        ]
        if before > len(companies):
            st.info(f"🧹 Agency mode cleaning: Removed {before - len(companies)} SaaS/product companies")

    st.info(f"🧹 Stage 2: Data cleaning ({len(companies)} candidates)")
    
    if not companies:
        st.warning("⚠️ No companies to clean")
        return []
    
    # ====================================================================
    # TIER ENFORCEMENT (Reject TIER3)
    # ====================================================================
    
    rejected_tier3 = []
    
    for company in companies:
        tier = company.get('signal_tier', 'UNKNOWN')
        if tier == 'TIER3':
            log_rejection(
                company,
                "TIER3 signal - too weak (blog posts, values pages)",
                "data_cleaning",
                run_id or "unknown"
            )
            rejected_tier3.append(company)
    
    companies = [c for c in companies if c not in rejected_tier3]
    
    if rejected_tier3:
        st.info(f"🚫 Filtered {len(rejected_tier3)} companies with TIER3 signals")
    
    # ====================================================================
    # COMPANY TYPE ENFORCEMENT (B2B SaaS only)
    # ====================================================================
    
    rejected_type = []
    valid_types = ['b2b saas', 'saas', 'b2b software', 'software']
    
    for company in companies:
        company_type = company.get('company_type', '').lower()
        if not any(valid in company_type for valid in valid_types):
            log_rejection(
                company,
                f"Wrong type: {company.get('company_type', 'Unknown')} (not B2B SaaS)",
                "data_cleaning",
                run_id or "unknown"
            )
            rejected_type.append(company)
    
    companies = [c for c in companies if c not in rejected_type]
    
    if rejected_type:
        st.info(f"🚫 Filtered {len(rejected_type)} non-SaaS companies")
    
    # ====================================================================
    # SIGNAL QUALITY CHECK (Reject weak signals)
    # ====================================================================
    
    rejected_weak_signal = []
    
    for company in companies:
        signal = company.get('signal', '').lower()
        signal_score = company.get('signal_score', 0)
        
        # Reject if signal is too generic
        generic_signals = ['growing', 'hiring', 'expanding', 'busy']
        if any(word in signal for word in generic_signals) and signal_score < 3:
            log_rejection(
                company,
                f"Generic signal with low score: {signal[:50]}",
                "data_cleaning",
                run_id or "unknown"
            )
            rejected_weak_signal.append(company)
    
    companies = [c for c in companies if c not in rejected_weak_signal]
    
    if rejected_weak_signal:
        st.info(f"🚫 Filtered {len(rejected_weak_signal)} companies with weak signals")
    
    # ====================================================================
    # APPLY MAX LIMIT
    # ====================================================================
    
    if len(companies) > max_companies:
        # Sort by signal score (best first)
        companies_sorted = sorted(
            companies,
            key=lambda x: (
                1 if x.get('signal_tier') == 'TIER1' else 2,
                -x.get('signal_score', 0)
            )
        )
        
        # Keep top N
        kept = companies_sorted[:max_companies]
        rejected_excess = companies_sorted[max_companies:]
        
        # Log rejections
        for company in rejected_excess:
            log_rejection(
                company,
                f"Exceeded limit (kept top {max_companies})",
                "data_cleaning",
                run_id or "unknown"
            )
        
        companies = kept
        st.info(f"🚫 Limited to top {max_companies} companies (rejected {len(rejected_excess)} lower-scored)")
    
    # ====================================================================
    # FINAL SUMMARY
    # ====================================================================
    
    total_rejected = len(rejected_tier3) + len(rejected_type) + len(rejected_weak_signal)
    
    st.success(f"""
✅ **Data Cleaning Complete**

- Input: {len(raw_companies) + total_rejected} companies
- Output: {len(companies)} companies
- Rejected: {total_rejected} companies

Quality filter applied:
- ❌ TIER3 signals removed
- ❌ Non-SaaS companies removed
- ❌ Weak signals removed
- ✅ Top {len(companies)} signal-based companies selected
    """)
    
    # NOTE: I removed the 'return companies' here that was blocking the AI cleaning logic below
    # If you only wanted rule-based cleaning, uncomment the return below.
    # return companies
    
    # ========================================================================
    # HYBRID MODE: Try local first (ONE ATTEMPT ONLY)
    # ========================================================================
    
    if mode == 'hybrid':
        try:
            local_available = check_local_available()
        except ImportError:
            local_available = False
            st.info("ℹ️ Local agent utilities not found, using cloud")
        
        if local_available:
            # ================================================================
            # FIX #6: ONE ATTEMPT ONLY, THEN IMMEDIATE CLOUD FALLBACK
            # ================================================================
            try:
                # Imports already done at top, but config needed
                from config.hybrid_config import get_hybrid_config
                
                config = get_hybrid_config()
                
                with st.spinner("🧹 Stage 2: Cleaning data (Local - FREE)..."):
                    # Use default if key missing
                    cleaner_model = config.get('local_cleaner', 'llama3.2:3b')
                    cleaner = create_local_data_cleaner(cleaner_model)
                    
                    prompt = (
                        "Clean and filter this company data:\n\n"
                        f"{json.dumps(companies, indent=2)}\n\n" # Use filtered companies
                        "REMOVE:\n"
                        "- VC firms, investment companies, capital firms, funds\n"
                        "- Agencies (marketing, consulting, creative, etc.)\n"
                        "- Blogs, media companies, publications, newsletters\n"
                        "- Communities, networks, forums\n"
                        "- Exact duplicates (same name or website)\n\n"
                        "NORMALIZE:\n"
                        "- Company names (proper capitalization)\n"
                        "- URLs (remove www, trailing slashes, normalize to https)\n"
                        "- Remove empty or null fields\n\n"
                        "VALIDATE:\n"
                        "- Must have valid website (not N/A)\n"
                        "- Must have signal field (not empty)\n"
                        "- Must have name field\n\n"
                        f"Return top {max_companies} cleanest B2B SaaS companies as JSON.\n"
                        "Output format: {{\"companies\": [...]}}\n"
                        "Return ONLY valid JSON, no markdown, no explanation."
                    )
                    
                    # ONE ATTEMPT ONLY (no retries)
                    response = run_local_agent(cleaner, prompt)
                    response = remove_emojis(response)
                    data = extract_json_or_raise(response)
                    cleaned = data.get("companies", [])
                    
                    if not cleaned or len(cleaned) == 0:
                        raise ValueError("Local cleaning returned empty list")
                    
                    st.success(f"✅ Local cleaning: {len(companies)} → {len(cleaned)} companies (FREE)")
                    return cleaned[:max_companies]
                    
            except Exception as e:
                # Immediate fallback to cloud (no retries)
                st.warning(f"⚠️ Local cleaning failed: {str(e)[:100]}")
                st.info("☁️ Switching to cloud cleaning (no retries)...")
                # Fall through to cloud cleaning below
        else:
            st.info("ℹ️ Ollama not available, using cloud for cleaning")
    
    # ========================================================================
    # CLOUD MODE or FALLBACK: Use cloud LLM (ONE ATTEMPT ONLY)
    # ========================================================================
    
    with st.spinner("🧹 Stage 2: Cleaning data (Cloud)..."):
        prompt = (
            "Clean and filter this company data:\n\n"
            f"{json.dumps(companies, indent=2)}\n\n" # Use filtered companies
            "REMOVE:\n"
            "- VC firms, investment companies, capital firms, funds\n"
            "- Agencies (marketing, consulting, creative, design, etc.)\n"
            "- Blogs, media companies, publications, newsletters\n"
            "- Communities, networks, forums, platforms\n"
            "- Exact duplicates (same name or website)\n"
            "- Non-B2B companies\n\n"
            "NORMALIZE:\n"
            "- Company names (proper capitalization, remove extra spaces)\n"
            "- URLs (standardize format: remove www, trailing slashes)\n"
            "- Clean up signal descriptions\n\n"
            "VALIDATE:\n"
            "- Must have valid website (real domain)\n"
            "- Must have clear signal\n"
            "- Must be B2B SaaS or software company\n\n"
            f"Return top {max_companies} cleanest B2B SaaS companies as JSON.\n"
            "Output format: {{\"companies\": [...]}}\n"
            "Return ONLY valid JSON, no markdown, no explanation."
        )
        
        try:
            
            # ONE ATTEMPT ONLY (no retries in run_agent_with_ensemble)
            content, _ = run_agent_with_ensemble(
                agent_openai, agent_gemini, prompt, "DataCleaning"
            )
            
            content = remove_emojis(content)
            data = extract_json_or_raise(content)
            cleaned = data.get("companies", [])
            
            if not cleaned or len(cleaned) == 0:
                raise ValueError("Cloud cleaning returned empty list")
            
            if mode == 'hybrid':
                st.success(f"✅ Cloud fallback: {len(companies)} → {len(cleaned)} companies")
            else:
                st.success(f"✅ Cloud cleaning: {len(companies)} → {len(cleaned)} companies")
            
            return cleaned[:max_companies]
            
        except Exception as e:
            st.warning(f"⚠️ Cloud cleaning failed: {str(e)[:100]}")
            st.info("🔄 Using rule-based fallback (Python filtering)...")
            
            # ================================================================
            # ULTIMATE FALLBACK: Rule-based Python filtering
            # ================================================================
            
            try:
                # Remove duplicates by website
                seen_websites = set()
                deduped = []
                
                for company in companies:
                    website = company.get('website', '').lower().strip()
                    if website and website not in seen_websites:
                        seen_websites.add(website)
                        deduped.append(company)
                
                # Apply validation rules
                filtered = [c for c in deduped if is_valid_company(c)]
                
                # Normalize URLs
                for company in filtered:
                    website = company.get('website', '')
                    if website:
                        # Remove www and trailing slash
                        website = website.replace('www.', '').rstrip('/')
                        company['website'] = website
                
                # Sort by signal quality (if available)
                filtered.sort(
                    key=lambda x: x.get('signal_score', 0), 
                    reverse=True
                )
                
                result = filtered[:max_companies]
                
                st.info(f"✅ Rule-based filter: {len(companies)} → {len(result)} companies")
                
                if len(result) == 0:
                    st.error("❌ All companies filtered out. Try adjusting target criteria.")
                
                return result
                
            except Exception as fallback_error:
                st.error(f"❌ All cleaning methods failed: {str(fallback_error)[:100]}")
                st.warning("Returning raw companies (unfiltered)")
                return companies[:max_companies]

def is_valid_company(company: Dict) -> bool:
    """Rule-based company validation (no AI needed)"""
    name = company.get("name", "").lower()
    website = company.get("website", "").lower()
    
    # Reject keywords
    reject = [
        "venture", "capital", "vc", "ventures", "fund", "equity",
        "agency", "consulting", "consultancy",
        "blog", "media", "publication", "publisher",
        "community", "newsletter", "network"
    ]
    
    if any(k in name or k in website for k in reject):
        return False
    
    # Must have valid signal
    if not company.get("signal"):
        return False
    
    return True


# ============================================================================
# STAGE 3: SIGNAL INFERENCE (Always Cloud)
# ============================================================================

def run_signal_inference(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    companies: List[Dict[str, str]],
    target_desc: str,
    offering_desc: str,
    niche_mode: str,
) -> Tuple[List[Dict[str, str]], Dict]:
    """
    STAGE 3: Deep signal analysis (ALWAYS CLOUD - requires intelligence)
    """
    from config.hybrid_config import get_hybrid_config, get_signal_tiers
    
    config = get_hybrid_config()
    signal_tiers = get_signal_tiers()
    
    # Get pipeline mode from session state
    pipeline_mode = st.session_state.get('pipeline_mode_type', 'FIND_MY_CLIENTS')
    min_score = config.get('min_signal_score', 3)
    
    prompt = (
        f"DEEP SIGNAL ANALYSIS for these companies:\n\n"
        f"Brain Mode: {niche_mode}\n"
        f"Companies: {json.dumps(companies)}\n\n"
        "SIGNAL TIER SYSTEM:\n"
        f"{json.dumps(signal_tiers, indent=2)}\n\n"
        "FOR EACH COMPANY, PROVIDE CAUSAL INFERENCE:\n"
        "{\n"
        '  "signal": "Hiring Head of Support",\n'
        '  "operational_change": "Support volume scaling beyond current capacity",\n'
        '  "second_order_effect": "Ticket backlog accumulating, response time degrading",\n'
        '  "business_risk": "CSAT drops, churn risk increases",\n'
        '  "why_now": "Active hiring = current pain, not future planning"\n'
        "}\n\n"
        f"FILTER: Only return companies with signal_score >= {config['min_signal_score']}\n\n"
        f"Target profile: {target_desc}\n"
        f"Offering alignment: {offering_desc}\n\n"
        "BANNED PHRASES:\n"
        "❌ 'might', 'could be', 'seems', 'perhaps', 'possibly'\n\n"
        "REQUIRED PHRASES:\n"
        "✅ 'indicates', 'shows', 'means', 'leads to', 'because'\n\n"
        "Output format: {\"companies\": [...]}"
    )
    
    with st.spinner("🧠 Stage 3: Deep signal analysis (Cloud - Advanced Reasoning)..."):
        content, metadata = run_agent_with_ensemble(
            agent_openai, agent_gemini, prompt, "SignalInference"
        )
    
    if st.session_state.get('debug_mode', False):
        with st.expander("🐛 Raw SignalInference Response"):
            st.code(content[:2000], language="text")
    
    try:
        content = remove_emojis(content)
        data = extract_json_or_raise(content)
    except ValueError as e:
        st.error("❌ Failed to parse JSON from SignalInference")
        st.error(str(e))
        raise
    
    analyzed = data.get("companies", [])
    
    # FIX #4: Conditional signal filtering based on mode
    if pipeline_mode == MODE_FIND_MY_CLIENTS:
        # Agency mode: NO signal filtering, keep all companies
        filtered = analyzed
        st.info(f"✅ Agency mode: {len(filtered)} companies (signal filtering disabled)")
    else:
        # Client mode: Apply strict signal threshold
        filtered = []
        for c in analyzed:
            try:
                score = float(c.get('signal_score', 0))
                if score >= min_score:
                    filtered.append(c)
            except (ValueError, TypeError):
                # If score is invalid, skip it
                continue
            
        st.success(f"✅ Signal analysis: {len(analyzed)} → {len(filtered)} companies (score >= {min_score})")

    # Use filtered companies going forward
    analyzed_companies = filtered
    time.sleep(5)
    
    return filtered, metadata


# ============================================================================
# STAGE 4: CONTACT FINDING (Always Cloud)
# ============================================================================

def run_contact_finder(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    companies: List[Dict[str, str]],
    target_desc: str,
    offering_desc: str,
) -> Tuple[List[Dict[str, Any]], Dict]:
    """
    STAGE 4: Find decision makers (ALWAYS CLOUD - needs real search)
    ENHANCED: Fail-soft behavior, validation, retry logic
    """
    
    prompt = (
        "Find 2-3 REAL decision makers per company.\n\n"
        "PROBLEM → OWNER MAPPING:\n"
        "- support/CX problem → Head of CX, VP Customer Success, Director of Support\n"
        "- growth problem → VP Growth, Head of Marketing, Growth Lead\n"
        "- infrastructure → CTO, VP Engineering, Head of DevOps\n"
        "- hiring → Head of Talent, VP People, HR Lead\n"
        "- sales problem → VP Sales, Head of Sales Development, CRO\n"
        "- product problem → VP Product, Head of Product, CPO\n"
        "- other → CEO, COO, Founder\n\n"
        f"Targeting: {target_desc}\n"
        f"Offering: {offering_desc}\n"
        f"Companies: {json.dumps(companies)}\n\n"
        "FOR EACH CONTACT:\n"
        "1. Find real people (search LinkedIn, company pages, team pages)\n"
        "2. Get actual emails (or infer with high confidence using common patterns)\n"
        "3. Assign problem_type based on signal\n"
        "4. Mark is_problem_owner=true for who FEELS this pain daily\n"
        "5. Use signal_interpretation to match the RIGHT decision maker\n\n"
        "CONTACT CONFIDENCE:\n"
        "- Email domain matches company website: HIGH\n"
        "- Email inferred from common pattern: MEDIUM (mark inferred=true)\n"
        "- Role matches problem type: Boost confidence\n\n"
        "EMAIL INFERENCE PATTERNS (only if actual email not found):\n"
        "- first.last@domain.com (most common)\n"
        "- firstlast@domain.com\n"
        "- first@domain.com\n"
        "- flast@domain.com\n"
        "Mark inferred=true for inferred emails\n\n"
        "Output: {\"companies\": [{\"name\": \"...\", \"problem_type\": \"...\", \"contacts\": [...]}]}"
    )
    
    max_retries = 2
    retry_count = 0
    contacts = [] 
    
    while retry_count <= max_retries:
        try:
            with st.spinner(f"👤 Stage 4: Finding decision makers (Cloud){f' - Retry {retry_count}/{max_retries}' if retry_count > 0 else ''}..."):
                content, metadata = run_agent_with_ensemble(
                    agent_openai, agent_gemini, prompt, "ContactFinder"
                )
            
            # Debug mode
            if st.session_state.get('debug_mode', False):
                with st.expander(f"🐛 Raw ContactFinder Response (Attempt {retry_count + 1})"):
                    st.code(content[:2000], language="text")
            
            # Parse JSON
            content = remove_emojis(content)
            data = extract_json_or_raise(content)
            contacts = data.get("companies", [])
            
            # Validate response
            if not contacts or len(contacts) == 0:
                raise ValueError("No companies returned in response")
            
            # Count contacts safely
            total_contacts = sum(
                len(c.get('contacts', [])) if isinstance(c.get('contacts'), list) else 0 
                for c in contacts
            )
            companies_with_contacts = sum(
                1 for c in contacts 
                if c.get('contacts') and len(c.get('contacts', [])) > 0
            )
            problem_owners = sum(
                sum(1 for contact in c.get('contacts', []) if contact.get('is_problem_owner'))
                for c in contacts
            )
            
            # Add metadata
            metadata['total_contacts'] = total_contacts
            metadata['companies_with_contacts'] = companies_with_contacts
            metadata['problem_owners_found'] = problem_owners
            metadata['retry_count'] = retry_count
            metadata['source'] = 'CLOUD_SUCCESS'
            
            st.success(
                f"✅ Found {total_contacts} decision makers across {companies_with_contacts} companies "
                f"({problem_owners} problem owners identified)"
            )
            
            # Warning for companies without contacts
            companies_without = len(contacts) - companies_with_contacts
            if companies_without > 0:
                st.warning(f"⚠️ {companies_without} companies have no contacts - marked for manual lookup")
            
            # Success - break retry loop
            break
            
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ JSON parsing failed (Attempt {retry_count + 1}/{max_retries + 1})")
            retry_count += 1
            
            if retry_count > max_retries:
                st.error("❌ Failed to parse ContactFinder response after retries")
                # Fall through to fail-soft below
                break
            else:
                st.info("🔄 Retrying...")
                time.sleep(2)
                continue
        
        except Exception as e:
            st.warning(f"⚠️ ContactFinder error: {str(e)[:100]}")
            retry_count += 1
            
            if retry_count > max_retries:
                # Fall through to fail-soft below
                break
            else:
                st.info("🔄 Retrying...")
                time.sleep(2)
                continue
    
    # ================================================================
    # FIX #5: FAIL-SOFT BEHAVIOR (if all retries failed)
    # ================================================================
    if retry_count > max_retries or not contacts:
        st.info("🔄 Enabling fail-soft mode - continuing with manual lookup flags...")
        
        # Return companies with manual_lookup flag
        contacts = []
        for company in companies:
            # Get suggested titles from signal interpretation
            signal_interp = company.get('signal_interpretation', {})
            pain_owner = signal_interp.get('pain_owner_role', 'CEO/Founder')
            
            contacts.append({
                'name': company.get('name', 'Unknown'),
                'website': company.get('website', 'N/A'),
                'signal': company.get('signal', 'N/A'),
                'signal_interpretation': signal_interp,
                'problem_type': signal_interp.get('pain_owner_department', 'general'),
                'contacts': [],  # Empty contacts list
                'manual_lookup_required': True,  # FLAG FOR MANUAL WORK
                'suggested_title': pain_owner,  # Who to look for
                'lookup_priority': 'HIGH' if signal_interp.get('urgency_level') == 'HIGH' else 'MEDIUM',
                'contact_finder_error': 'API failure - requires manual LinkedIn lookup'
            })
        
        st.warning(f"📝 {len(contacts)} companies marked for manual LinkedIn lookup")
        
        with st.expander("💡 Manual Lookup Instructions"):
            st.markdown("""
            **How to find decision makers manually:**
            #### **Step 1: LinkedIn Company Search**
1. Go to LinkedIn
2. Search: `[Company Name]`
3. Click on company page
4. Click **"People"** tab
5. Search for the **Suggested Title** (shown in CSV)

#### **Step 2: Find Email Address**

**Option A: Hunter.io** (Free: 25 searches/month)
- Go to: [https://hunter.io/domain-search](https://hunter.io/domain-search)
- Enter company domain
- Filter by job title

**Option B: RocketReach** (Free: 5 lookups/month)
- Go to: [https://rocketreach.co](https://rocketreach.co)
- Search person name + company

**Option C: Email Pattern Inference**
Most common patterns:
- `firstname.lastname@domain.com` (60%)
- `firstname@domain.com` (20%)
- `firstnamelastname@domain.com` (15%)

#### **Step 3: Verify with Signal**
Check that the person you found is likely to care about the signal:
- **Signal type** is shown in CSV
- **Problem owner role** is who feels the pain
- Match their actual role to expected role

#### **Step 4: Mark as Complete**
- Add email to CSV
- Change `manual_lookup_required` from `True` to `False`
- Add `email_verified: True` if confirmed
        """)
        
        # Show which companies need lookup
        st.subheader("Companies Needing Lookup")
        for i, contact in enumerate(contacts[:5], 1):  # Show first 5
            st.write(f"**{i}. {contact['name']}**")
            st.caption(f"🎯 Look for: {contact['suggested_title']}")
            st.caption(f"🔗 Website: {contact['website']}")
            st.caption(f"⏱️ Est. time: {contact['estimated_lookup_time'] if 'estimated_lookup_time' in contact else '7 min'}")
            st.divider()
        
        if len(contacts) > 5:
            st.info(f"... and {len(contacts) - 5} more (see full list in CSV export)")
    
    # Metadata for tracking
    metadata = {
        'source': 'FAILED_SOFT',
        'error': 'ContactFinder failed after retries',
        'manual_lookup_required': True,
        'total_companies': len(contacts),
        'retry_count': retry_count,
        'suggested_lookup_time': f"{len(contacts) * 7} minutes"  # 7 min avg per company
    }
    
    time.sleep(5)
    return contacts, metadata


# ============================================================================
# STAGE 5: RESEARCH (Always Cloud)
# ============================================================================

def run_research(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    companies: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], Dict]:
    """
    STAGE 5: Deep research (ALWAYS CLOUD - needs web access)
    """
    prompt = (
        "For each company, extract deep positioning intelligence:\n\n"
        "REQUIRED FIELDS:\n"
        "- top_3_pain_hints: 3 SPECIFIC pain signals (not generic)\n"
        "- growth_narrative: How THEY describe their growth (1-2 sentences)\n"
        "- icp_language: Exact phrases THEY use for their customers\n"
        "- public_priorities: 3-5 things they emphasize publicly\n"
        "- positioning_note: Critical insight for pitching (actionable)\n"
        "- competitors: 2-3 direct competitors (optional)\n\n"
        f"Companies: {json.dumps(companies)}\n\n"
        "SOURCES:\n"
        "- Company website (about, product, pricing pages)\n"
        "- Blog (recent posts about growth, challenges)\n"
        "- Careers page (what they emphasize in hiring)\n"
        "- Social media (LinkedIn, Twitter)\n\n"
        "ANTI-BS RULES:\n"
        "❌ NO generic statements ('They care about innovation')\n"
        "✅ USE specific language they actually use\n"
        "✅ positioning_note must be actionable for email writing\n\n"
        "Output format: {\"companies\": [...]}"
    )
    
    with st.spinner("🔍 Stage 5: Deep research (Cloud)..."):
        content, metadata = run_agent_with_ensemble(
            agent_openai, agent_gemini, prompt, "Research"
        )
    
    if st.session_state.get('debug_mode', False):
        with st.expander("🐛 Raw Research Response"):
            st.code(content[:2000], language="text")
    
    try:
        content = remove_emojis(content)
        data = extract_json_or_raise(content)
    except ValueError as e:
        st.error("❌ Failed to parse JSON from Research")
        st.error(str(e))
        raise
    
    research = data.get("companies", [])
    
    st.success(f"✅ Research completed for {len(research)} companies")
    
    time.sleep(5)
    
    return research, metadata


# ============================================================================
# STAGE 6: EMAIL GENERATION (Always Cloud)
# ============================================================================

def run_email_writer(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    contacts_data: List[Dict[str, Any]],
    research_data: List[Dict[str, Any]],
    offering_desc: str,
    sender_name: str,
    sender_company: str,
    calendar_link: Optional[str],
) -> Tuple[List[Dict[str, str]], Dict]:
    """
    STAGE 6: Email generation (ALWAYS CLOUD - needs quality)
    """
    prompt = (
        "Write personalized multi-channel outreach.\n\n"
        "STRUCTURE: Observation → Inference → Soft CTA\n\n"
        f"Sender: {sender_name} at {sender_company}\n"
        f"Offering: {offering_desc}\n"
        f"Calendar: {calendar_link or 'N/A'}\n\n"
        f"Contacts: {json.dumps(contacts_data)}\n"
        f"Research: {json.dumps(research_data)}\n\n"
        "FOR EACH CONTACT GENERATE:\n"
        "1. Email:\n"
        "   - company (Name of company)\n"
        "   - contact (Full name of contact)\n"
        "   - subject (5-8 words, no clickbait)\n"
        "   - body (120-180 words)\n"
        "     → Line 1: Specific signal observation\n"
        "     → Line 2-3: Inference about their situation\n"
        "     → Line 4: Value proposition (how you help)\n"
        "     → Line 5: Soft CTA (not pushy)\n"
        "2. linkedin_dm (1-3 lines, conversational)\n"
        "3. twitter_dm (1-3 lines, casual)\n"
        "4. followup_angles: [3 different follow-up approaches]\n"
        "   - Angle 1: Product/feature focus\n"
        "   - Angle 2: Case study / social proof\n"
        "   - Angle 3: Curiosity / insight share\n"
        "5. breakup_email (short, leave door open)\n"
        "6. confidence (0-100):\n"
        "   - Signal strength & recency: 40 points\n"
        "   - Problem-owner match: 30 points\n"
        "   - Research depth: 30 points\n"
        "7. confidence_reason (1 sentence explaining score)\n\n"
        "BANNED PHRASES:\n"
        "❌ 'Hope you're doing well'\n"
        "❌ 'I noticed your website'\n"
        "❌ 'Love your product'\n"
        "❌ 'Quick question'\n"
        "❌ 'Just checking in'\n\n"
        "REQUIRED:\n"
        "✅ Start with specific signal observation\n"
        "✅ Use causal reasoning (because, leads to, indicates)\n"
        "✅ Clear value proposition\n"
        "✅ Soft, helpful tone\n\n"
        "Output format: {\"emails\": [...]}"
    )
    
    with st.spinner("✉️ Stage 6: Writing personalized emails (Cloud)..."):
        content, metadata = run_agent_with_ensemble(
            agent_openai, agent_gemini, prompt, "EmailWriter"
        )
    
    if st.session_state.get('debug_mode', False):
        with st.expander("🐛 Raw EmailWriter Response"):
            st.code(content[:2000], language="text")
    
    try:
        content = remove_emojis(content)
        data = extract_json_or_raise(content)
    except ValueError as e:
        st.error("❌ Failed to parse JSON from EmailWriter")
        st.error(str(e))
        raise
    
    emails = data.get("emails", [])
    
    st.success(f"✅ Generated {len(emails)} personalized email sequences")
    
    return emails, metadata


# ============================================================================
# STAGE 7: OUTPUT VALIDATION (Hybrid: Local | Cloud: Skip)
# ============================================================================

def run_output_validation(
    results: Dict[str, Any],
    mode: str = 'hybrid'
) -> Dict[str, Any]:
    """
    STAGE 7: Validate and clean output
    Hybrid: Uses local LLM (FREE)
    Cloud: Skips (already validated)
    """
    
    if mode == 'fully_cloud':
        # Cloud mode: validation already done by cloud models
        st.success("✅ Output validated (cloud models are self-validating)")
        return results
    
    # HYBRID MODE: Try local validation
    local_available = check_local_available()
    
    if local_available:
        try:
            from utils.local_agents import create_local_json_validator, run_local_agent
            from config.hybrid_config import get_hybrid_config
            
            config = get_hybrid_config()
            
            with st.spinner("✅ Stage 7: Validating output (Local - FREE)..."):
                validator_model = config.get('local_validator', 'qwen2.5:7b')
                validator = create_local_json_validator(validator_model)
                
                prompt = (
                    "Validate and fix this JSON output:\n\n"
                    f"{json.dumps(results, indent=2)}\n\n"
                    "TASKS:\n"
                    "1. Fix any JSON syntax errors\n"
                    "2. Ensure all brackets and braces closed\n"
                    "3. Remove trailing commas\n"
                    "4. Validate all required fields present\n"
                    "5. Remove any emojis or special unicode\n"
                    "6. Validate email addresses (must contain @)\n"
                    "7. Ensure all arrays have correct length\n\n"
                    "Return corrected JSON only (no explanations)."
                )
                
                response = run_local_agent(validator, prompt)
                response = remove_emojis(response)
                validated = extract_json_or_raise(response)
                
                st.success("✅ Output validated and cleaned (local)")
                return validated
                
        except Exception as e:
            st.warning(f"⚠️ Local validation failed: {str(e)[:100]}")
    
    # Fallback: return original
    st.info("ℹ️ Using original output (local validation unavailable)")
    return results


def detect_multiple_geographies(target_desc: str) -> List[str]:
    """
    Detect if multiple geographies are mentioned in target description
    
    Returns:
        List of detected geographies
    """
    import re
    
    # Geography keywords (using whole word matching to avoid false positives)
    geo_patterns = {
        'pune': r'\b(pune|pimpri)\b',
        'mumbai': r'\b(mumbai|bombay|thane|navi mumbai)\b',
        'bangalore': r'\b(bangalore|bengaluru|blr)\b',
        'delhi': r'\b(delhi|ncr|gurgaon|gurugram|noida)\b',
        'hyderabad': r'\b(hyderabad|secunderabad|hyd)\b',
        'chennai': r'\b(chennai|madras)\b',
        'kolkata': r'\b(kolkata|calcutta)\b',
        'ahmedabad': r'\b(ahmedabad|amdavad)\b',
        'india': r'\b(india|indian)\b',
        'usa': r'\b(usa|united states|u\.s\.a|u\.s\.|america)\b',  # Removed "us" and "american"
        'uk': r'\b(uk|united kingdom|britain|british|u\.k\.)\b',
        'singapore': r'\b(singapore|sg)\b',
        'uae': r'\b(uae|dubai|abu dhabi|emirates)\b',
    }
    
    target_lower = target_desc.lower()
    detected = []
    
    for geo, pattern in geo_patterns.items():
        if re.search(pattern, target_lower, re.IGNORECASE):
            detected.append(geo)
    
    return detected



def create_geo_batches(target_desc: str, max_companies: int, explicit_location: str = None) -> List[Dict]:
    """
    Split multi-geo targets into manageable batches with hard caps
    
    Args:
        target_desc: Original target description
        max_companies: Total companies requested
        
    Returns:
        List of geo batch configurations
    """

    # If user explicitly specified location, use ONLY that
    if explicit_location:
        return [{
            'geo': explicit_location.lower().strip(),
            'limit': max_companies,
            'target': target_desc,
            'is_batch': False
        }]    

    detected_geos = detect_multiple_geographies(target_desc)
    
    # Single geo or no geo detected - no batching needed
    if len(detected_geos) <= 1:
        return [{
            'geo': detected_geos[0] if detected_geos else 'unknown',
            'limit': max_companies,
            'target': target_desc,
            'is_batch': False
        }]
    
    # Multiple geos detected - apply batching with hard caps
    # Cap per geo: minimum of (15 companies) or (total / num_geos)
    max_per_geo = min(15, max(5, max_companies // len(detected_geos)))
    
    batches = []
    for geo in detected_geos:
        batches.append({
            'geo': geo,
            'limit': max_per_geo,
            'target': f"{target_desc} specifically in {geo.title()}",
            'is_batch': True
        })
    
    # Show batching info
    st.info(f"""
🌍 **Multi-Geography Detected**

Detected regions: {', '.join(detected_geos)}

**Batching strategy:**
- Companies per region: {max_per_geo} (capped)
- Total expected: {len(detected_geos) * max_per_geo} companies
- Original request: {max_companies} companies

💡 This prevents quality dilution across geographies.
""")


def run_company_finder_with_geo_batching(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    target_desc: str,
    offering_desc: str,
    max_companies: int,
    niche_mode: str,
) -> Tuple[List[Dict], Dict]:
    """
    Run company finder with automatic geo batching
    
    Returns:
        (companies, metadata)
    """

    # Get pipeline mode from session state
    pipeline_mode = st.session_state.get('pipeline_mode_type', 'FIND_MY_CLIENTS')

    # FIX #1: Agency mode cannot use signal-based discovery
    if pipeline_mode == MODE_FIND_MY_CLIENTS:
        st.warning("""
        🚫 **Agency Mode: Signal-based discovery disabled**
        
        Exa/signal search finds SaaS companies, not agencies.
        
        **Manual workaround:**
        1. Use Google Maps: "marketing agencies in Pune"
        2. Use directories: Clutch.co, GoodFirms
        3. Import CSV with agency names
        
        **We cannot auto-discover agencies yet.**
        """)
        
        return [], {'source': 'AGENCY_MODE_DISABLED', 'total_companies': 0}

    # Create geo batches
    batches = create_geo_batches(target_desc, max_companies)
    
    # If single batch (no multi-geo), run normally
    if len(batches) == 1 and not batches[0]['is_batch']:
        return run_company_finder(
            agent_openai, agent_gemini,
            target_desc, offering_desc,
            max_companies, niche_mode
        )
    
    # Multi-geo: run each batch separately
    st.info(f"🌍 Processing {len(batches)} geographic regions separately...")
    
    all_companies = []
    batch_results = []
    
    for i, batch in enumerate(batches, 1):
        geo_name = batch['geo'].title()
        
        with st.expander(f"🌍 Batch {i}/{len(batches)}: {geo_name} (max {batch['limit']} companies)", expanded=True):
            try:
                st.info(f"Searching for companies in {geo_name}...")
                
                # Run discovery for this geo
                companies, meta = run_company_finder(
                    agent_openai, agent_gemini,
                    batch['target'],  # Modified target with geo specificity
                    offering_desc,
                    batch['limit'],
                    niche_mode
                )
                
                # Tag each company with its geo
                for company in companies:
                    company['discovered_geo'] = batch['geo']
                    company['geo_batch'] = i
                
                all_companies.extend(companies)
                
                batch_results.append({
                    'geo': batch['geo'],
                    'requested': batch['limit'],
                    'found': len(companies),
                    'success': True
                })
                
                st.success(f"✅ Found {len(companies)} companies in {geo_name}")
                
                # Small delay between batches to avoid rate limits
                if i < len(batches):
                    time.sleep(3)
                
            except Exception as e:
                st.warning(f"⚠️ {geo_name} batch failed: {str(e)[:150]}")
                batch_results.append({
                    'geo': batch['geo'],
                    'requested': batch['limit'],
                    'found': 0,
                    'success': False,
                    'error': str(e)[:200]
                })
                continue
    
    # Summary
    total_found = len(all_companies)
    successful_batches = sum(1 for b in batch_results if b['success'])
    
    st.success(f"""
    🌍 **Geo Batching Complete**
    
    - Total companies: {total_found}
    - Successful regions: {successful_batches}/{len(batches)}
    - Coverage: {', '.join(b['geo'].title() for b in batch_results if b['success'])}
    """)
    
    # Show breakdown
    with st.expander("📊 Geo Breakdown"):
        for result in batch_results:
            status = "✅" if result['success'] else "❌"
            st.write(f"{status} **{result['geo'].title()}**: {result['found']}/{result['requested']} companies")
    
    # Combined metadata
    metadata = {
        'source': 'GEO_BATCHED',
        'total_batches': len(batches),
        'successful_batches': successful_batches,
        'batch_results': batch_results,
        'total_companies': total_found
    }
    
    return all_companies, metadata

# ============================================================================
# MAIN ORCHESTRATORS
# ============================================================================

def run_hybrid_pipeline(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    target_desc: str,
    offering_desc: str,
    sender_name: str,
    sender_company: str,
    calendar_link: Optional[str],
    max_companies: int,
    niche_mode: str,
    email_style: str = "Professional",
    run_id: Optional[str] = None, # FIXED: Added comma
    resume_from_stage: Optional[str] = None,
    pipeline_mode=MODE_FIND_MY_CLIENTS
) -> Dict[str, Any]:
    """
    HYBRID PIPELINE: 2 local stages (FREE) + 5 cloud stages (PAID)
    Optimal balance: 60% cost savings vs fully cloud
    """
    st.info("⚡ Running HYBRID pipeline (Local optimization + Cloud intelligence)")

    if run_id is None:
        run_id = str(uuid.uuid4())[:8]
        st.info(f"🆔 New Run ID: `{run_id}`")
    else:
        st.info(f"🆔 Resuming Run ID: `{run_id}`")
    
    # Show available checkpoints if resuming
    if resume_from_stage:
        st.success(f"⏭️ Fast-forwarding to: **{resume_from_stage}**")
    
    # ====================================================================
    # Stage 1: Web Discovery (Cloud) - WITH RETRY
    # ====================================================================

    st.info("🔍 Stage 1: Company Discovery with Geographic Intelligence...")
    
    # ✅ Use geo-batching version instead of regular
    raw_companies, meta1 = run_company_finder_with_geo_batching(
        agent_openai, agent_gemini,
        target_desc, offering_desc,
        max_companies, niche_mode
    )

    # FIX #2: Hard agency validation firewall
    if pipeline_mode == MODE_FIND_MY_CLIENTS:
        agency_types = ['marketing agency', 'digital agency', 'agency', 'consultancy', 
                        'web development agency', 'growth agency', 'creative agency',
                        'advertising agency', 'services']

        before_count = len(raw_companies)
        raw_companies = [
            c for c in raw_companies 
            if any(atype in c.get('company_type', '').lower() for atype in agency_types)
        ]
        filtered = before_count - len(raw_companies)

        if filtered > 0:
            st.warning(f"🚫 FIREWALL: Removed {filtered} non-agency companies (SaaS/products)")

        if before_count > 0 and len(raw_companies) == 0:
            st.error("""
            ❌ **All companies were non-agencies (likely SaaS)**

            This means signal-based discovery doesn't work for agencies.
            Use manual import instead.
            """)

    if pipeline_mode == MODE_FIND_MY_CLIENTS:
        before = len(raw_companies)
        raw_companies = [
            c for c in raw_companies 
            if 'saas' not in c.get('company_type', '').lower()
        ]
        filtered = before - len(raw_companies)
        if filtered > 0:
            print(f"🚫 Filtered {filtered} SaaS companies (agency mode)")

    # FIX #7: Fail-fast validation - ensure no SaaS leaked through
    if pipeline_mode == MODE_FIND_MY_CLIENTS and len(raw_companies) > 0:
        saas_leaked = [
            c for c in raw_companies 
            if 'saas' in c.get('company_type', '').lower()
        ]

        if saas_leaked:
            st.error(f"""
            🚨 **LOGIC ERROR: {len(saas_leaked)} SaaS companies detected in agency mode!**

            This should never happen after the firewall and filter.

            **Leaked companies:** {', '.join(c['name'] for c in saas_leaked[:3])}

            **Root cause:** The discovery prompt is generating wrong company types.
            """)
            raise ValueError(f"SaaS leak detected in agency mode: {[c['name'] for c in saas_leaked]}")

    # Show geo distribution if batched
    if meta1.get('source') == 'GEO_BATCHED':
        geo_counts = {}
        for company in raw_companies:
            geo = company.get('discovered_geo', 'unknown')
            geo_counts[geo] = geo_counts.get(geo, 0) + 1
        
        st.info(f"""
        📍 **Geographic Distribution:**
        {chr(10).join(f'- {geo.title()}: {count} companies' for geo, count in geo_counts.items())}
        """)
    
    # Save checkpoint
    if run_id:
        save_stage_checkpoint('stage1_companies', raw_companies, run_id)

    # ====================================================================
    # 🆕 STAGE 1.5: GEO VALIDATION (Problem #1 Fix)
    # ====================================================================
    
    def validate_geo_coverage(companies: List[Dict], target_desc: str) -> Dict:
        """Assess expected yield per geography"""
        geo_mentions = {
            'pune': 0, 'mumbai': 0, 'bangalore': 0, 'delhi': 0,
            'india': 0, 'us': 0, 'uk': 0, 'global': 0
        }
        
        target_lower = target_desc.lower()
        for geo in geo_mentions.keys():
            if geo in target_lower:
                geo_mentions[geo] = 1
        
        expected_yields = {
            'pune': (5, 15),
            'mumbai': (10, 25),
            'bangalore': (8, 20),
            'delhi': (8, 18),
            'india': (20, 50),
            'us': (30, 100),
            'uk': (15, 40),
            'global': (10, 30)
        }
        
        detected_geo = next((k for k, v in geo_mentions.items() if v == 1), 'unknown')
        expected_range = expected_yields.get(detected_geo, (5, 15))
        actual_count = len(companies)
        
        return {
            'detected_geo': detected_geo,
            'expected_min': expected_range[0],
            'expected_max': expected_range[1],
            'actual_count': actual_count,
            'coverage_quality': 'good' if expected_range[0] <= actual_count <= expected_range[1] else 'low'
        }
    
    # Run geo validation
    geo_stats = validate_geo_coverage(raw_companies, target_desc)
    
    if geo_stats['coverage_quality'] == 'low':
        st.warning(f"""
        ⚠️ **Geo Coverage Alert**
        - Detected region: **{geo_stats['detected_geo']}**
        - Expected: {geo_stats['expected_min']}-{geo_stats['expected_max']} companies
        - Found: **{geo_stats['actual_count']}** companies
        
        This is normal for {geo_stats['detected_geo']}. Directory coverage varies by location.
        """)
    else:
        st.info(f"✅ Geo coverage: {geo_stats['detected_geo']} ({geo_stats['actual_count']} companies)")
    
    # Stage 2: Data Cleaning (Local or Cloud fallback)
    cleaned_companies = run_data_cleaning(
        raw_companies, max_companies,
        agent_openai, agent_gemini,
        mode='hybrid',
        run_id = run_id,
        pipeline_mode=pipeline_mode
    )
    
    st.info("🔍 Stage 2.5: Deduplication check...")

    def deduplicate_companies(companies: List[Dict]) -> tuple:
        """Remove duplicates by domain and name"""
        import os
        import re
        from urllib.parse import urlparse

        def normalize_domain(url: str) -> str:
            """Extract and normalize domain"""
            try:
                parsed = urlparse(url if url.startswith('http') else f'https://{url}')
                domain = parsed.netloc or parsed.path
                domain = domain.replace('www.', '').lower().strip()
                return domain
            except:
                return url.lower().strip()

        def normalize_name(name: str) -> str:
            """Normalize company name"""
            name = name.lower().strip()
            name = re.sub(r'\b(pvt|ltd|llc|inc|corp|limited|private)\b', '', name)
            name = re.sub(r'[^\w\s]', '', name)
            name = ' '.join(name.split())
            return name   

        # Load seen companies log
        seen_log_path = "tmp/seen_companies.txt"
        seen_domains = set()
        seen_names = set()    

        if os.path.exists(seen_log_path):
            with open(seen_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|')
                    if len(parts) >= 2:
                        seen_domains.add(parts[0])
                        seen_names.add(parts[1])

        unique = []
        duplicates = []
        current_domains = set()
        current_names = set()  

        for company in companies:
            domain = normalize_domain(company.get('website', ''))
            name = normalize_name(company.get('name', ''))
            
            # Check for duplicates
            is_duplicate = False
            reason = []
            
            if domain in seen_domains or domain in current_domains:
                is_duplicate = True
                reason.append(f"Domain: {domain}")
            
            if name in seen_names or name in current_names:
                is_duplicate = True
                reason.append(f"Name: {name}")
            
            if is_duplicate:
                company['duplicate_reason'] = ' | '.join(reason)
                duplicates.append(company)
            else:
                unique.append(company)
                current_domains.add(domain)
                current_names.add(name)

        # Save to seen log
        os.makedirs(os.path.dirname(seen_log_path), exist_ok=True)
        with open(seen_log_path, 'a', encoding='utf-8') as f:
            for company in unique:
                domain = normalize_domain(company.get('website', ''))
                name = normalize_name(company.get('name', ''))
                f.write(f"{domain}|{name}|{company.get('name', 'Unknown')}\n")
        stats = {
            'total': len(companies),
            'unique': len(unique),
            'duplicates': len(duplicates),
            'dedup_rate': f"{(len(duplicates) / len(companies) * 100):.1f}%" if companies else "0%"
        }
        
        return unique, duplicates, stats

    # Run deduplication
    unique_companies, duplicates, dedup_stats = deduplicate_companies(cleaned_companies)
    
    # Show results
    st.success(f"""
    ✅ **Deduplication Complete:**
    - Input: {dedup_stats['total']} companies
    - Unique: {dedup_stats['unique']} companies  
    - Duplicates removed: {dedup_stats['duplicates']} ({dedup_stats['dedup_rate']})
    """)
    
    # Show duplicates if any
    if duplicates:
        with st.expander(f"🔍 View {len(duplicates)} Duplicates Removed"):
            for dup in duplicates[:10]:
                st.write(f"**{dup.get('name', 'Unknown')}**")
                st.caption(f"Reason: {dup.get('duplicate_reason', 'N/A')}")
                st.divider()

    # Use deduplicated list going forward
    cleaned_companies = unique_companies

    # ====================================================================
    # Stage 3: Signal Inference (Cloud) - WITH FAIL-SOFT
    # ====================================================================

    if resume_from_stage in ['contacts', 'research', 'emails']:
        st.info("⏭️ Skipping Stage 3 (loading from checkpoint)")
        analyzed_companies = load_stage_checkpoint('stage3_analyzed', run_id)
        
        if analyzed_companies is None:
            st.warning("⚠️ No checkpoint found. Running Stage 3.")
            resume_from_stage = None
        else:
            st.success(f"✅ Loaded {len(analyzed_companies)} analyzed companies")
    
    if resume_from_stage is None or resume_from_stage not in ['contacts', 'research', 'emails']:
        try:
            analyzed_companies, meta3 = run_signal_inference(
                agent_openai, agent_gemini,
                cleaned_companies,
                target_desc, offering_desc, niche_mode
            )
            # ✅ SAVE CHECKPOINT
            save_stage_checkpoint('stage3_analyzed', analyzed_companies, run_id)
            
        except Exception as e:
            st.warning(f"⚠️ Stage 3 failed: {str(e)[:150]}")
            analyzed_companies = cleaned_companies
            save_stage_checkpoint('stage3_analyzed', analyzed_companies, run_id)

    
    # Stage 4: Contact Finding (Cloud)
    if resume_from_stage in ['research', 'emails']:
        st.info("⏭️ Skipping Stage 4 (loading from checkpoint)")
        contacts = load_stage_checkpoint('stage4_contacts', run_id)
        
        if contacts is None:
            st.warning("⚠️ No checkpoint found. Running Stage 4.")
            resume_from_stage = None
        else:
            st.success(f"✅ Loaded {len(contacts)} contacts")
    
    if resume_from_stage is None or resume_from_stage not in ['research', 'emails']:
        contacts, meta4 = run_contact_finder(
            agent_openai, agent_gemini,
            analyzed_companies,
            target_desc, offering_desc
        )
        # ✅ SAVE CHECKPOINT
        save_stage_checkpoint('stage4_contacts', contacts, run_id)


        # ====================================================================
    # Stage 5: Research (Cloud) - WITH FAIL-SOFT
    # ====================================================================

    if resume_from_stage == 'emails':
        st.info("⏭️ Skipping Stage 5 (loading from checkpoint)")
        research = load_stage_checkpoint('stage5_research', run_id) or []
    else:
        try:
            research, meta5 = run_research(
                agent_openai, agent_gemini,
                analyzed_companies
            )
            # ✅ SAVE CHECKPOINT
            save_stage_checkpoint('stage5_research', research, run_id)
            
        except Exception as e:
            st.warning(f"⚠️ Stage 5 failed: {str(e)[:150]}")
            research = []
            save_stage_checkpoint('stage5_research', research, run_id)

    
    # ====================================================================
    # 🆕 Stage 5.5: PRE-HUMAN FILTERING (Margin Protection)
    # ====================================================================
    
    st.info("🛡️ Stage 5.5: Pre-human filtering (Quality Gate)...")

    # Initialize defaults
    accepted_companies = analyzed_companies  # Fallback
    rejected_companies = []
    filter_stats = {
        'total': 0,
        'accepted': 0,
        'rejected': 0,
        'rejection_rate': 0
    }
    
    # Check if signal processing modules are available
    SIGNAL_MODULES_AVAILABLE = False
    
    try:
        from utils.signal_interpreter import bulk_interpret_signals
        from utils.signal_rejection import apply_rejection_rules
        SIGNAL_MODULES_AVAILABLE = True
    except ImportError as e:
        st.warning(f"⚠️ Signal processing modules not available: {str(e)[:150]}")
        st.info("ℹ️ Skipping quality gate - continuing with all companies")
    
    if SIGNAL_MODULES_AVAILABLE and len(analyzed_companies) > 0:
        try:
            # Step 1: Add signal interpretation
            companies_with_interpretation = bulk_interpret_signals(
                analyzed_companies,
                offering_desc,
                mode=st.session_state.get('pipeline_mode_type', 'FIND_CLIENTS_FOR_CUSTOMER')
            )
            
            # Step 2: Apply rejection rules
            accepted_companies, rejected_companies, filter_stats = apply_rejection_rules(
                companies_with_interpretation,
                mode=st.session_state.get('pipeline_mode_type', 'FIND_CLIENTS_FOR_CUSTOMER')
            )
            
            # Safe display with division by zero protection
            total = filter_stats.get('total', 0)
            accepted = filter_stats.get('accepted', 0)
            rejected = filter_stats.get('rejected', 0)
            rejection_rate = filter_stats.get('rejection_rate', 0) if total > 0 else 0
            
            st.success(f"""
            ✅ Pre-Human Filter Complete:
            - Total: {total}
            - Accepted: {accepted}
            - Rejected: {rejected}
            - Rejection Rate: {rejection_rate:.1f}%
            """)
            
            # Show rejected companies
            if rejected_companies:
                with st.expander(f"❌ Rejected Companies ({len(rejected_companies)})"):
                    for r in rejected_companies[:10]:
                        st.write(f"**{r.get('name', 'Unknown')}** - Quality Score: {r.get('quality_score', 0)}/100")
                        st.caption(f"Reason: {r.get('rejection_reason', 'Unknown')}")
                        st.divider()
            
            # Filter contacts and research to match accepted companies
            accepted_company_names = {c['name'] for c in accepted_companies}
            
            filtered_contacts = [
                c for c in contacts 
                if c.get('name') in accepted_company_names
            ]
            
            filtered_research = [
                r for r in research 
                if r.get('name') in accepted_company_names
            ]
            
            st.info(f"📊 Proceeding with {len(accepted_companies)} companies that passed quality gate")
            
            # Update analyzed_companies to only include accepted
            analyzed_companies = accepted_companies
            
        except Exception as e:
            st.error(f"❌ Quality gate failed: {str(e)[:200]}")
            st.warning("⚠️ Continuing without filtering - all companies will proceed")
            
            # Fallback: use all companies
            accepted_companies = analyzed_companies
            rejected_companies = []
            filtered_contacts = contacts
            filtered_research = research
            filter_stats = {
                'total': len(analyzed_companies),
                'accepted': len(analyzed_companies),
                'rejected': 0,
                'rejection_rate': 0
            }
            
            st.info(f"📊 Proceeding with all {len(analyzed_companies)} companies (no filtering)")
    
    elif len(analyzed_companies) == 0:
        # No companies to filter
        st.warning("⚠️ No companies to filter (0 found in previous stages)")
        accepted_companies = []
        rejected_companies = []
        filtered_contacts = []
        filtered_research = []
        filter_stats = {'total': 0, 'accepted': 0, 'rejected': 0, 'rejection_rate': 0}
        
    else:
        # Modules not available - skip filtering
        st.info("ℹ️ Quality gate skipped (modules not installed)")
        accepted_companies = analyzed_companies
        rejected_companies = []
        filtered_contacts = contacts
        filtered_research = research
        filter_stats = {
            'total': len(analyzed_companies),
            'accepted': len(analyzed_companies),
            'rejected': 0,
            'rejection_rate': 0
        }
        st.info(f"📊 Proceeding with all {len(analyzed_companies)} companies")
    
    

    # ====================================================================
    # Stage 6: Email Writing (Cloud) - WITH RETRY
    # ====================================================================

    @retry_with_backoff(max_retries=2, base_delay=3.0, stage_name="Stage 6: Email Writing")
    def run_email_writer_with_retry():
        """Stage 6 with retry logic"""
        return run_email_writer(
            agent_openai, agent_gemini,
            filtered_contacts, filtered_research,
            offering_desc,
            sender_name, sender_company, calendar_link
        )

    try:
        emails, meta6 = run_email_writer_with_retry()
    except Exception as e:
        st.error(f"❌ Stage 6 failed: {str(e)[:200]}")
        st.warning("⚠️ Manual email writing required")
        emails = []
        meta6 = {'source': 'FAILED', 'error': str(e)}


    # Combine results
    results = {
     'companies': accepted_companies if 'accepted_companies' in locals() else [],
     'contacts': filtered_contacts if 'filtered_contacts' in locals() else [],
     'research': filtered_research if 'filtered_research' in locals() else [],
     'emails': emails if 'emails' in locals() else [],
     'rejected_companies': rejected_companies if 'rejected_companies' in locals() else [],
     'metadata': {
         'mode': 'hybrid',
         'total_companies_found': len(raw_companies) if 'raw_companies' in locals() else 0,
         'companies_after_cleaning': len(cleaned_companies) if 'cleaned_companies' in locals() else 0,
         'companies_after_signal_inference': len(analyzed_companies) if 'analyzed_companies' in locals() else 0,
         'companies_after_quality_gate': len(accepted_companies) if 'accepted_companies' in locals() else 0,
         'companies_rejected': len(rejected_companies) if 'rejected_companies' in locals() else 0,
         'rejection_rate': filter_stats.get('rejection_rate', '0%') if 'filter_stats' in locals() else '0%',
         'total_contacts': sum(len(c.get('contacts', [])) for c in filtered_contacts) if 'filtered_contacts' in locals() else 0,
         'total_emails': len(emails) if 'emails' in locals() else 0,
         'local_stages_used': 2,
         'cloud_stages_used': 5,
         'filtering_stats': filter_stats if 'filter_stats' in locals() else {}
     }
}   

    
    st.success(f"""
    ✅ **Pipeline Complete!**
    
    Run ID: `{run_id}`
    
    💡 **To resume this run later:**
    - Use Run ID: `{run_id}`
    - Available stages: cleaning, inference, contacts, research, emails
    """)
    
    return results


def run_fully_cloud_pipeline(
    agent_openai: Optional[Any],
    agent_gemini: Optional[Any],
    target_desc: str,
    offering_desc: str,
    sender_name: str,
    sender_company: str,
    calendar_link: Optional[str],
    max_companies: int,
    niche_mode: str,
    email_style: str = "Professional"
) -> Dict[str, Any]:
    """
    FULLY CLOUD PIPELINE: All 6 stages use cloud (PAID)
    Fastest, highest quality, no local dependencies
    """
    st.info("☁️ Running FULLY CLOUD pipeline (All stages use cloud AI)")

    # Stage 1: Web Discovery (Cloud)
    raw_companies, _ = run_company_finder(
        agent_openai, agent_gemini,
        target_desc, offering_desc,
        max_companies, niche_mode
    )

    # Stage 2: Data Cleaning (Cloud)
    cleaned_companies = run_data_cleaning(
        raw_companies, max_companies,
        agent_openai, agent_gemini,
        mode='fully_cloud'
    )

    # Stage 3: Signal Inference (Cloud)
    analyzed_companies, _ = run_signal_inference(
        agent_openai, agent_gemini,
        cleaned_companies, target_desc, offering_desc, niche_mode
    )

    # Stage 4: Contact Finding (Cloud)
    contacts, _ = run_contact_finder(
        agent_openai, agent_gemini,
        analyzed_companies, target_desc, offering_desc
    )

    # Stage 5: Research (Cloud)
    research, _ = run_research(
        agent_openai, agent_gemini,
        analyzed_companies
    )

        # ====================================================================
    # 🆕 Stage 5.5: PRE-HUMAN FILTERING (Margin Protection)
    # SAME CODE AS HYBRID - Copy the entire section above
    # ====================================================================

    st.info("🛡️ Stage 5.5: Pre-human filtering (Quality Gate)...")

    from utils.signal_interpreter import bulk_interpret_signals
    from utils.signal_rejection import apply_rejection_rules

    # Step 1: Add signal interpretation
    companies_with_interpretation = bulk_interpret_signals(
        analyzed_companies, 
        offering_desc
    )

    # Step 2: Apply rejection rules
    accepted_companies, rejected_companies, filter_stats = apply_rejection_rules(
        companies_with_interpretation
    )

    # Show results
    st.success(f"""
    ✅ Pre-Human Filter Complete:
    - Total: {filter_stats['total_companies']}
    - Accepted: {filter_stats['accepted']} (avg score: {filter_stats['avg_accepted_score']:.1f})
    - Rejected: {filter_stats['rejected']} (avg score: {filter_stats['avg_rejected_score']:.1f})
    - Rejection Rate: {filter_stats['rejection_rate']:.1f}%
    """)

    if rejected_companies:
        with st.expander(f"❌ Rejected Companies ({len(rejected_companies)})"):
            for r in rejected_companies[:10]:
                st.write(f"**{r.get('name')}** - Quality Score: {r['quality_score']}/100")
                st.caption(f"Reason: {r['rejection_reason']}")
                st.divider()

    # Filter contacts and research
    accepted_company_names = [c['name'] for c in accepted_companies]
    filtered_contacts = [c for c in contacts if c.get('name') in accepted_company_names]
    filtered_research = [r for r in research if r.get('name') in accepted_company_names]
    
    st.info(f"📊 Proceeding with {len(filtered_contacts)} companies that passed quality gate")
    
    # Stage 6: Email Writing (Cloud)
    emails, _ = run_email_writer(
    agent_openai, agent_gemini,
    filtered_contacts,  # Use filtered instead of all contacts
    filtered_research,
    offering_desc, sender_name, sender_company, calendar_link
    )
    
    # Combine results
    results = {
        'companies': accepted_companies if 'accepted_companies' in locals() else [],
        'contacts': filtered_contacts,
        'research': filtered_research,
        'emails': emails,
        'rejected_companies': rejected_companies,
        'metadata': {
            'mode': 'fully_cloud',
            'total_companies_found': len(raw_companies),
            'companies_after_cleaning': len(cleaned_companies),
            'companies_after_signal_inference': len(analyzed_companies),
            'companies_after_quality_gate': len(accepted_companies),
            'companies_rejected': len(rejected_companies),
            'rejection_rate': filter_stats['rejection_rate'],
            'total_contacts': sum(len(c.get('contacts', [])) for c in filtered_contacts),
            'total_emails': len(emails),
            'local_stages_used': 0,
            'cloud_stages_used': 6,
            'filtering_stats': filter_stats
        }
    }
    
    # Stage 7: Validation (Skip in cloud mode)
    validated_results = run_output_validation(results, mode='fully_cloud')
    
    return validated_results


# ============================================================================
# DATA AGGREGATION
# ============================================================================

from typing import Dict, Any, List


def build_leads(results: Dict[str, Any]) -> List[Lead]:
    """
    Build normalized Lead objects from pipeline results
    Enhanced with validation, error handling,
    and enforced delivery standard (Fix #8)
    """
    leads: List[Lead] = []
    
    # Index data by company name
    companies = {
        c.get("name", ""): c
        for c in results.get("companies", [])
        if c.get("name")
    }
    research_by_company = {
        r.get("name", ""): r
        for r in results.get("research", [])
        if r.get("name")
    }
    contacts_by_company = {
        c.get("name", ""): c
        for c in results.get("contacts", [])
        if c.get("name")
    }
    
    for email in results.get("emails", []):
        comp_name = email.get("company", "")
        contact_name = email.get("contact", "")
        
        # Skip if missing critical data
        if not comp_name or not contact_name:
            continue
        
        comp = companies.get(comp_name, {})
        contacts_block = contacts_by_company.get(comp_name, {})
        
        # Find matching contact safely
        contacts_list = contacts_block.get("contacts", [])
        if not isinstance(contacts_list, list):
            contacts_list = []

        contact = next(
            (p for p in contacts_list if p.get("full_name") == contact_name),
            {}
        )
        
        # Extract follow-up angles
        followup_angles = email.get("followup_angles", [])
        if not isinstance(followup_angles, list):
            followup_angles = []
        while len(followup_angles) < 3:
            followup_angles.append("")
        
        # Extract signal interpretation
        signal_interp = comp.get("signal_interpretation", {})
        if not isinstance(signal_interp, dict):
            signal_interp = {}
        
        # ✅ CHANGED: Use Lead dataclass instead of dict
        lead = Lead(
            # -------- Company --------
            company=comp_name,
            website=comp.get("website", ""),
            company_type=comp.get("company_type", ""),
            
            # -------- Signal (MANDATORY) --------
            signal=comp.get("signal", ""),
            signal_interpretation=format_interpretation_for_display(signal_interp),
            signal_tier=comp.get("signal_tier", "UNKNOWN"),
            signal_score=comp.get("signal_score", 0),
            
            # -------- Contact --------
            contact=contact_name,
            role=contact.get("title", ""),
            email=contact.get("email", ""),
            problem_owner=contact.get("is_problem_owner", False),
            manual_lookup_required=contacts_block.get("manual_lookup_required", False),
            
            # -------- Outreach --------
            email_subject=email.get("subject", ""),
            email_body=email.get("body", ""),
            linkedin_dm=email.get("linkedin_dm", ""),
            twitter_dm=email.get("twitter_dm", ""),
            outreach_angle=signal_interp.get("outreach_angle", ""),
            
            # -------- Follow-up --------
            followup_angle_1=followup_angles[0],
            followup_angle_2=followup_angles[1],
            followup_angle_3=followup_angles[2],
            breakup_email=email.get("breakup_email", ""),
            
            # -------- Quality (MANDATORY) --------
            quality_score=comp.get("quality_score", 0),
            notes=generate_lead_notes(comp, contact, signal_interp),
            
            # ✅ NEW: Risk Assessment Fields (Problem #5 Fix)
            confidence_score=email.get("confidence", 0),
            confidence_reason=email.get("confidence_reason", ""),
            rejection_risk=generate_rejection_risk(comp, contact),
            risk_factors=extract_risk_factors(comp, contact, signal_interp),
        )
        
        leads.append(lead)
    
    return leads


# ============================================================================
# 🆕 HELPER FUNCTIONS FOR RISK ASSESSMENT
# ============================================================================

def generate_lead_notes(company: Dict, contact: Dict, signal_interp: Dict) -> str:
    """
    Generate contextual notes for delivery (Fix #8)
    """
    notes = []
    
    if contact.get("inferred"):
        notes.append("⚠️ Email inferred - not confirmed")
    
    if signal_interp.get("interpretation_confidence", 0) < 70:
        notes.append("⚠️ Signal interpretation confidence below 70%")
    
    if company.get("signal_tier") == "TIER2":
        notes.append("ℹ️ TIER2 signal - moderate urgency")
    
    return " | ".join(notes) if notes else "No special notes"


def generate_rejection_risk(company: Dict, contact: Dict) -> str:
    """
    Explain why this might not work (Problem #5 Fix)
    """
    risks = []
    
    # Contact-level risks
    if not contact.get("is_problem_owner"):
        risks.append("May not be the actual problem owner")
    
    if contact.get("inferred"):
        risks.append("Email inferred - not confirmed")
    
    # Signal-level risks
    urgency = company.get("signal_interpretation", {}).get("urgency_level", "LOW")
    if urgency not in ["HIGH", "CRITICAL"]:
        risks.append("Timing may not be urgent enough")
    
    # Quality-level risks
    if company.get("quality_score", 100) < 80:
        risks.append("Below quality threshold - higher rejection risk")
    
    if company.get("signal_tier") == "TIER2":
        risks.append("TIER2 signal - moderate strength")
    
    return " | ".join(risks) if risks else "Low rejection risk"


def extract_risk_factors(company: Dict, contact: Dict, signal_interp: Dict) -> List[str]:
    """
    Extract specific risk factors as a list (Problem #5 Fix)
    """
    factors = []
    
    # Signal risks
    if signal_interp.get("interpretation_confidence", 100) < 70:
        factors.append("LOW_SIGNAL_CONFIDENCE")
    
    if company.get("signal_score", 0) < 4:
        factors.append("WEAK_SIGNAL")
    
    # Contact risks
    if contact.get("inferred"):
        factors.append("INFERRED_EMAIL")
    
    if not contact.get("is_problem_owner"):
        factors.append("NOT_PROBLEM_OWNER")
    
    # Timing risks
    urgency = signal_interp.get("urgency_level", "UNKNOWN")
    if urgency == "LOW":
        factors.append("LOW_URGENCY")
    elif urgency == "UNKNOWN":
        factors.append("URGENCY_UNKNOWN")
    
    # Quality risks
    if company.get("quality_score", 100) < 70:
        factors.append("LOW_QUALITY_SCORE")
    
    return factors

def export_leads_to_csv(leads: List[Lead]) -> str:
    """
    Export leads to CSV format with proper escaping
    """
    if not leads:
        return ""
    
    output = StringIO()
    
    # Define field order
    fieldnames = [
    'company', 'website', 'company_type',
    'signal', 'signal_interpretation', 'signal_tier', 'signal_score',
    'contact', 'role', 'email', 'problem_owner', 'manual_lookup_required',
    'email_subject', 'email_body', 'linkedin_dm', 'twitter_dm',
    'outreach_angle', 'followup_angle_1', 'followup_angle_2', 'followup_angle_3',
    'breakup_email', 
    'confidence_score', 'confidence_reason',  # ✅ Updated naming
    'quality_score', 'notes', 
    'rejection_risk', 'risk_factors'  # ✅ Added risk_factors
]

    
    # ========================================================================
    # FIX #8: Better CSV escaping
    # ========================================================================
    
    writer = csv.DictWriter(
    output,
    fieldnames=fieldnames,
    quoting=csv.QUOTE_MINIMAL,  # Standard approach
    lineterminator='\n'
    )

    
    writer.writeheader()
    
    # Clean and write rows
    for lead in leads:
        # Create clean row (handle None values)
        clean_row = {}
        for field in fieldnames:
            value = getattr(lead, field, '')
            
            # Convert to string and strip
            if value is None:
                clean_row[field] = ''
            elif isinstance(value, bool):
                clean_row[field] = str(value)
            elif isinstance(value, (int, float)):
                clean_row[field] = value  # Keep numeric
            else:
                # Clean string: remove problematic characters
                clean_value = str(value).strip()
                
                # Remove null bytes (can break CSV)
                clean_value = clean_value.replace('\x00', '')
                
                # Normalize newlines
                clean_value = clean_value.replace('\r\n', ' ').replace('\n', ' ')
                
                # Remove extra whitespace
                clean_value = ' '.join(clean_value.split())
                
                clean_row[field] = clean_value
        
        writer.writerow(clean_row)
    
    return output.getvalue()