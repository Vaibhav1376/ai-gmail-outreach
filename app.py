"""
GTM Outreach v2 - Main Streamlit Application
FULLY CLOUD + HYBRID modes with graceful degradation
"""
import datetime
import json
import os
import time
from typing import Any, Dict, List

import streamlit as st

# Import agents and pipeline
from agents import (
    create_company_finder_agents,
    create_contact_finder_agents,
    create_research_agents,
    create_email_writer_agents,
)

# At top of app.py
from utils.agent_helpers import (
    extract_json_or_raise,
    remove_emojis,
    run_agent_with_ensemble,
    select_best_response,
    create_company_finder_agents,
    create_contact_finder_agents,
    create_email_writer_agents,
    get_email_style_instruction,
)

from utils.geo_validator import detect_multiple_geographies
from utils.campaign_readiness import evaluate_campaign_readiness
# Now you can delete those functions from app.py and just use the imports!


# Import BOTH pipeline modes
from pipeline import (
    run_hybrid_pipeline,
    run_fully_cloud_pipeline,
    build_leads,
    export_leads_to_csv
)


from services.offer_validation import validate_offer


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="GTM Outreach v2",
    page_icon="🚀",
    layout="wide"
)


# ============================================================================
# SIDEBAR - PIPELINE MODE + AI CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Pipeline Configuration")

    # ========================================================================
    # MODE SELECTOR (FIX #2 - BEFORE EVERYTHING ELSE)
    # ========================================================================
    
    st.subheader("🎯 What are you finding?")
    
    pipeline_mode_type = st.radio(
        "Select use case",
        [
            "🏢 Finding clients FOR a customer",
            "🎯 Finding MY clients (agencies)"
        ],
        index=0,
        key="pipeline_mode_type_radio"
    )
    
    if "MY clients" in pipeline_mode_type:
        mode_type = "FIND_MY_CLIENTS"
        st.warning("""
        **AGENCY MODE ACTIVE**
        - Target: Marketing/Growth Agencies
        - Volume: 2-5 max per run
        - Signal: Referral dependency, lead flow issues
        - Contact: Founder/Owner only
        """)
    else:
        mode_type = "FIND_CLIENTS_FOR_CUSTOMER"
        st.info("""
        **CLIENT CAMPAIGN MODE**
        - Target: Client's ICP
        - Volume: Up to 10 per run
        - Signal: Growth, hiring, expansion
        - Contact: Problem owner (varies)
        """)
    
    st.session_state['pipeline_mode_type'] = mode_type
    
    st.divider()

    with st.expander("⚖️ Quality Monitor"):
        from utils.quality_pressure import show_quality_pressure_dashboard
        
        # Simple version - just show the mantras
        st.warning("""
**Quality Mantras:**

1. "If quality feels easy, we're doing it wrong"
2. "Reject first, question later"
3. "We're paid for what we DON'T include"
        """)
    
    with st.expander("🎯 Is This Right for You?"):
        from utils.client_qualification import show_client_qualification
        show_client_qualification()

    
    # ========================================================================
    # STEP 1: PIPELINE MODE SELECTION
    # ========================================================================
    
    st.subheader("1️⃣ Select Pipeline Mode")
    
    pipeline_mode = st.radio(
        "Choose Your Pipeline",
        [
            "☁️ Fully Cloud (Fastest, Best Quality)",
            "⚡ Hybrid (Recommended - 60% Cost Savings)"
        ],
        index=1,  # Default to Hybrid
        help="""
        **Fully Cloud:** All 6 stages use Gemini/OpenAI. Fastest, highest quality.
        Cost: $0.15-0.30 per 10 companies
        
        **Hybrid:** 2 stages use local Ollama (FREE), 4 stages use cloud.
        Cost: $0.06-0.10 per 10 companies (60% savings!)
        """,
        key="pipeline_mode_radio"
    )
    
    # Extract mode
    if "Fully Cloud" in pipeline_mode:
        mode = 'fully_cloud'
        st.success("☁️ All stages will use cloud models")
    elif "Hybrid" in pipeline_mode:
        mode = 'hybrid'
        st.info("⚡ Using cloud + local optimization")
    
    st.session_state['pipeline_mode'] = mode
    
    st.divider()
    
    # Show pipeline diagram
    with st.expander("🔍 See Pipeline Architecture"):
        if mode == 'fully_cloud':
            st.markdown("""
            ### ☁️ Fully Cloud Pipeline
            
            1. 🔍 Web Discovery → **Cloud**
            2. 🧹 Data Cleaning → **Cloud**
            3. 🧠 Signal Inference → **Cloud**
            4. 👤 Contact Finding → **Cloud**
            5. 🔍 Research → **Cloud**
            6. ✉️ Email Generation → **Cloud**
            
            **Speed:** ⚡⚡⚡ 2-3 minutes
            **Quality:** ⭐⭐⭐⭐⭐
            **Cost:** $0.15-0.30 / 10 companies
            """)
        else:
            st.markdown("""
            ### ⚡ Hybrid Pipeline
            
            1. 🔍 Web Discovery → **Cloud** (Paid)
            2. 🧹 Data Cleaning → **Local** (FREE) ✨
            3. 🧠 Signal Inference → **Cloud** (Paid)
            4. 👤 Contact Finding → **Cloud** (Paid)
            5. 🔍 Research → **Cloud** (Paid)
            6. ✉️ Email Generation → **Cloud** (Paid)
            7. ✅ Validation → **Local** (FREE) ✨
            
            **Speed:** ⚡⚡ 3-5 minutes
            **Quality:** ⭐⭐⭐⭐
            **Cost:** $0.06-0.10 / 10 companies
            **Savings:** 60% vs Fully Cloud
            """)
    
    st.divider()
    
    # ========================================================================
    # STEP 2: COST ESTIMATOR
    # ========================================================================
    
    st.subheader("💰 Cost Estimator")
    
    num_companies_estimate = st.slider(
        "Estimate for # companies",
        min_value=1,
        max_value=50,
        value=10,
        key="cost_estimate_slider"
    )
    
    if mode == 'fully_cloud':
        cost_min = num_companies_estimate * 0.015
        cost_max = num_companies_estimate * 0.030
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Min Cost", f"${cost_min:.2f}")
        with col2:
            st.metric("Max Cost", f"${cost_max:.2f}")
        
        st.caption("⚡ ~2-3 minutes processing time")
        
    else:  # hybrid
        cost_min = num_companies_estimate * 0.006
        cost_max = num_companies_estimate * 0.010
        cloud_cost = num_companies_estimate * 0.020
        savings = cloud_cost - cost_max
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cost", f"${cost_min:.2f} - ${cost_max:.2f}")
        with col2:
            st.metric("Savings", f"${savings:.2f}", delta="-60%")
        
        st.caption("⚡ ~3-5 minutes processing time")
    
    st.divider()
    
    # ========================================================================
    # STEP 3: CLOUD AI CONFIGURATION
    # ========================================================================
    
    st.subheader("☁️ Cloud AI Models")
    
    tab1, tab2 = st.tabs(["🔷 Gemini", "🟢 OpenAI"])
    
    # ====================================================================
    # GEMINI TAB
    # ====================================================================
    
    with tab1:
        st.subheader("Google Gemini")

        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            value=os.getenv('GEMINI_API_KEY', ''),
            key="gemini_api_key_input"
        )

        # Model list with descriptions (for help text)
        gemini_models_info = {
            # Gemini 2.5 (Latest)
            "gemini-2.5-flash": "⭐ Best balance - 1M context, 15 RPM",
            "gemini-2.5-pro": "Highest quality - slower, 5 RPM",
            "gemini-2.5-flash-lite": "⚠️ Fastest but limited - NOT for production",

            # Gemini 2.0
            "gemini-2.0-flash": "Fast & reliable - 1M context, 10 RPM",
            "gemini-2.0-flash-exp": "Experimental V2 - 15 RPM",

            # Gemini 1.5 (Most Stable)
            "gemini-1.5-flash": "Most stable - proven reliability, 15 RPM",
            "gemini-1.5-flash-8b": "⚠️ Ultra fast but basic - NOT recommended",
            "gemini-1.5-pro": "High quality - 2M context, 5 RPM",

            # Experimental
            "gemini-exp-1206": "🧪 Experimental - strict 2 RPM limit",
        }

        # Show ONLY model names in dropdown (no emojis/descriptions)
        selected_gemini = st.selectbox(
            "Gemini Model",
            list(gemini_models_info.keys()),
            index=0,  # Default to gemini-2.5-flash
            # NO format_func = shows raw model names
            key="gemini_model_select",
            help="Select your Gemini model"
        )

        # Show description BELOW the selectbox
        st.caption(f"ℹ️ {gemini_models_info[selected_gemini]}")

        if gemini_key:
            os.environ['GEMINI_API_KEY'] = gemini_key
            st.session_state['has_gemini'] = True  # ✅ ADD THIS LINE
            st.session_state['gemini_model'] = selected_gemini  # ✅ ADD THIS LINE
            st.success("✅ Connected")
        else:
            st.session_state['has_gemini'] = False
            st.session_state['gemini_model'] = None

        # Warnings for problematic models
        
        if "8b" in selected_gemini:
            st.warning("""
            ⚠️ **Limited Capabilities**
            - Basic tasks only
            - May struggle with reasoning

            **Better:** `gemini-2.5-flash`
            """)

        if "exp" in selected_gemini:
            st.info("🧪 Experimental model - may have strict rate limits (2-10 RPM)")

    
    # ====================================================================
    # OPENAI TAB
    # ====================================================================
    
    with tab2:
        st.subheader("OpenAI")
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            key="openai_key_input",
            help="Get API key: https://platform.openai.com/api-keys"
        )
        if openai_key:
            os.environ['OPENAI_API_KEY'] = openai_key
            st.success("✅ Connected")

        # Model list with descriptions
        openai_models_info = {
            "gpt-4o": "Latest GPT-4 - $5/1M tokens",
            "gpt-4o-mini": "⭐ BEST VALUE - 90% quality, 10x cheaper ($0.15/1M)",
            "gpt-4-turbo": "Fast GPT-4 - $10/1M tokens",
            "gpt-4": "Original GPT-4 - $30/1M tokens (expensive)",
            "gpt-3.5-turbo": "Cheapest - $0.50/1M tokens",
            "o1-mini": "⚠️ Reasoning model - OVERKILL for this",
        }

        # Show ONLY model names in dropdown
        selected_openai = st.selectbox(
            "OpenAI Model",
            list(openai_models_info.keys()),
            index=1,  # Default to gpt-4o-mini
            # NO format_func = shows raw model names
            key="openai_model_select",
            help="Select your OpenAI model"
        )

        # Show description BELOW
        st.caption(f"ℹ️ {openai_models_info[selected_openai]}")

        # Warnings for expensive models
        if selected_openai in ["gpt-4", "o1-mini"]:
            st.warning("""
            ⚠️ **HIGH COST MODEL**
            This model is expensive for outreach.

            **Better value:** `gpt-4o-mini`
            """)


        st.divider()
    
    # ====================================================================
    # PROVIDER SELECTION
    # ====================================================================
    
    st.subheader("🎯 Primary Provider")
    
    has_gemini = bool(os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
    has_openai = bool(os.environ.get('OPENAI_API_KEY'))
    
    if has_gemini and has_openai:
        primary_provider = st.radio(
            "Which provider to use?",
            ["🔷 Gemini (Cheaper)", "🟢 OpenAI (More Reliable)"],
            key="primary_provider_radio"
        )
        
        # Ensemble option
        use_ensemble = st.checkbox(
            "🔀 Use Both (Ensemble)",
            value=False,
            help="Run both models, select best response. 2x cost but best quality.",
            key="use_ensemble_checkbox"
        )
        
    elif has_gemini:
        st.success("Using: 🔷 Gemini")
        use_ensemble = False
        
    elif has_openai:
        st.success("Using: 🟢 OpenAI")
        use_ensemble = False
        
    else:
        st.error("❌ Add at least one API key")
        use_ensemble = False
    
    st.divider()
    
    # ========================================================================
    # STEP 4: LOCAL MODEL CONFIGURATION (Only for Hybrid)
    # ========================================================================
    
    if mode == 'hybrid':
        st.subheader("🖥️ Local Models (FREE)")

        # Check Ollama installation
        try:
            import subprocess
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                st.success("✅ Ollama installed")
                ollama_installed = True

                # Parse installed models
                installed_models = []
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        installed_models.append(model_name)

                if installed_models:
                    with st.expander("📋 Your Installed Models"):
                        for model in installed_models:
                            st.write(f"- {model}")
            else:
                st.error("❌ Ollama not found")
                ollama_installed = False
                installed_models = []
        except:
            st.error("❌ Ollama not installed")
            ollama_installed = False
            installed_models = []

        if not ollama_installed:
            st.warning("""
            ⚠️ **Ollama not detected**

            Hybrid mode will fall back to cloud for all stages.

            **Install Ollama to save 60%:**
            1. Download: https://ollama.com/download
            2. Install and restart terminal
            3. Run: `ollama pull llama3.2:3b`
            """)

            if st.button("📥 Open Ollama Download"):
                import webbrowser
                webbrowser.open("https://ollama.com/download")

        st.divider()

        # ========================================================================
        # LOCAL MODEL SELECTION (Updated with TinyLlama + descriptions)
        # ========================================================================

        st.markdown("### 🧹 Cleaner Model")
        st.caption("Used for data filtering (Stage 2)")

        # All available cleaner models (including TinyLlama)
        cleaner_models_info = {
            "tinyllama:latest": "⚡ FASTEST - 1.1B params, 637MB (you have this!)",
            "llama3.2:3b": "⭐ RECOMMENDED - Fast, 2GB, good quality",
            "llama3.1:8b": "Better quality - 4.7GB, slower",
            "qwen2.5:7b": "Best for structured data - 4.3GB",
            "phi3:3b": "Microsoft model - 2.3GB",
        }

        # Show dropdown with ONLY model names
        cleaner_model = st.selectbox(
            "Select cleaner model",
            list(cleaner_models_info.keys()),
            index=0 if "tinyllama" in installed_models else 1,  # Default to tinyllama if installed
            key="cleaner_model_select"
        )

        # Show description below
        st.caption(f"ℹ️ {cleaner_models_info[cleaner_model]}")

        # Show if installed or not
        if cleaner_model.split(':')[0] in str(installed_models):
            st.success("✅ Already installed")
        else:
            st.warning("⚠️ Not installed yet")
            if st.button(f"📥 Install {cleaner_model}", key="install_cleaner"):
                with st.spinner(f"Downloading {cleaner_model}..."):
                    try:
                        result = subprocess.run(
                            ['ollama', 'pull', cleaner_model],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        if result.returncode == 0:
                            st.success(f"✅ Installed {cleaner_model}")
                            st.rerun()
                        else:
                            st.error(f"Failed: {result.stderr[:200]}")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")

        st.divider()

        # ========================================================================
        # VALIDATOR MODEL SELECTION (Updated with TinyLlama)
        # ========================================================================

        st.markdown("### ✅ Validator Model")
        st.caption("Used for JSON validation (Stage 7)")

        validator_models_info = {
            "qwen2.5:7b": "⭐ RECOMMENDED - Best for JSON, 4.3GB",
            "llama3.1:8b": "Good alternative - 4.7GB",
            "llama3.2:3b": "Fast option - 2GB",
            "tinyllama:latest": "Fastest - 637MB (may struggle with JSON)",
            "phi3:3b": "Microsoft - 2.3GB",
        }

        validator_model = st.selectbox(
            "Select validator model",
            list(validator_models_info.keys()),
            index=0,
            key="validator_model_select"
        )

        st.caption(f"ℹ️ {validator_models_info[validator_model]}")

        # Show if installed
        if validator_model.split(':')[0] in str(installed_models):
            st.success("✅ Already installed")
        else:
            st.warning("⚠️ Not installed yet")
            if st.button(f"📥 Install {validator_model}", key="install_validator"):
                with st.spinner(f"Downloading {validator_model}..."):
                    try:
                        result = subprocess.run(
                            ['ollama', 'pull', validator_model],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        if result.returncode == 0:
                            st.success(f"✅ Installed {validator_model}")
                            st.rerun()
                        else:
                            st.error(f"Failed: {result.stderr[:200]}")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")

        # Store local config
        st.session_state['local_cleaner'] = cleaner_model
        st.session_state['local_validator'] = validator_model

        st.divider()

    
    # ========================================================================
    # EXA API KEY
    # ========================================================================
    
    st.subheader("🔍 Exa Search")
    exa_key = st.text_input(
        "Exa API Key",
        type="password",
        value=os.getenv("EXA_API_KEY", ""),
        help="Required for company & contact research"
    )
    if exa_key:
        os.environ['EXA_API_KEY'] = exa_key
        st.success("✅ Connected")
    
    st.divider()
    
    # ========================================================================
    # ADVANCED SETTINGS
    # ========================================================================
    
    with st.expander("⚙️ Advanced Settings"):
        temperature = st.slider(
            "Temperature", 
            0.0, 1.0, 0.7, 0.1,
            key="temperature_slider"
        )
        max_tokens = st.slider(
            "Max Tokens", 
            512, 4096, 2048, 256,
            key="max_tokens_slider"
        )
        
        # Debug mode
        debug_mode = st.checkbox(
            "🐛 Debug Mode (Show raw responses)", 
            value=False,
            key="debug_mode_checkbox"
        )
        st.session_state['debug_mode'] = debug_mode
    
    # ========================================================================
    # SAVE CONFIGURATION
    # ========================================================================
    
    st.session_state['ai_config'] = {
        'mode': mode,
        'has_gemini': has_gemini,
        'has_openai': has_openai,
        'use_ensemble': use_ensemble if (has_gemini and has_openai) else False,
        'gemini_model': selected_gemini if has_gemini else None,
        'openai_model': selected_openai if has_openai else None,
    }
    
    # Validation
    if not has_gemini and not has_openai:
        st.error("❌ Add at least one cloud API key to continue")


# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("🚀 GTM Outreach v2 - Signal & Brain-Based")

# Status bar
status_cols = st.columns(4)
with status_cols[0]:
    if has_gemini:
        st.success("🔷 Gemini Ready")
    else:
        st.error("🔷 Gemini Missing")
with status_cols[1]:
    if has_openai:
        st.success("🟢 OpenAI Ready")
    else:
        st.error("🟢 OpenAI Missing")
with status_cols[2]:
    if exa_key:
        st.success("🔍 Exa Ready")
    else:
        st.error("🔍 Exa Missing")
with status_cols[3]:
    mode_display = "☁️ Cloud" if mode == 'fully_cloud' else "⚡ Hybrid"
    st.info(f"Mode: {mode_display}")

st.divider()

# Info banner
st.info(
    f"🎯 **Running in {mode_display} Mode** - Signal-based discovery, "
    "decision-maker mapping, deep research, and multi-channel outreach with confidence scoring."
)

# ============================================================================
# INPUT FORM (UPDATED WITH MODE-AWARE CONTROLS)
# ============================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Target & Offering")
    
    # ========================================================================
    # MODE-AWARE TARGET INPUT
    # ========================================================================
    
    mode_pipeline = st.session_state.get('pipeline_mode_type', 'FIND_CLIENTS_FOR_CUSTOMER')
    
    if mode_pipeline == 'FIND_MY_CLIENTS':
        # Agency-finding mode
        target_placeholder = (
            "Example:\n"
            "- Marketing agencies, 5-20 employees\n"
            "- Growth agencies struggling with lead flow\n"
            "- Founder-led, dependent on referrals\n"
            "- US/UK/Canada based"
        )
        target_help = "Describe the agencies you want as clients (YOUR ICP)"
        
        offering_placeholder = (
            "Example:\n"
            "We help marketing agencies build predictable outbound systems "
            "that reduce referral dependency by 60% and generate 15-20 qualified "
            "conversations per month without hiring SDRs."
        )
        offering_help = "What do YOU offer to agencies? Focus on outcomes."
        
    else:
        # Client campaign mode
        target_placeholder = (
            "Example:\n"
            "- B2B SaaS companies in fintech\n"
            "- 50-200 employees, Series A-B funded\n"
            "- High support volume, US/EU\n"
            "- Hiring customer success roles"
        )
        target_help = "Describe YOUR CLIENT's target companies (their ICP)"
        
        offering_placeholder = (
            "Example:\n"
            "AI-powered customer support automation that reduces ticket volume "
            "by 40%, improves response time by 3x, and cuts support costs by $200K/year."
        )
        offering_help = "What does YOUR CLIENT offer? Focus on outcomes."
    
    # Target input
    target_desc = st.text_area(
        "Target Companies",
        placeholder=target_placeholder,
        height=140,
        help=target_help,
        key="target_desc_input"
    )
    
    if target_desc:
        #detected_geos = detect_multiple_geographies(target_desc)
        detected_geos = {'multiple_geos': False, 'geographies': [], 'warning': None}
        if len(detected_geos) > 1:
            st.info(f"""
            🌍 **Multi-geo detected:** {', '.join(g.title() for g in detected_geos)}
        
            System will:
            - Process each region separately
            - Cap at 15 companies per region
            - Maintain quality across geographies
            """)
        elif len(detected_geos) == 1:
            st.caption(f"📍 Target region: {detected_geos[0].title()}")
        else:
            st.caption("ℹ️ No specific geography detected - will search globally")

    # Offering input
    offering_desc = st.text_area(
        "Your Offering" if mode_pipeline == 'FIND_MY_CLIENTS' else "Client's Offering",
        placeholder=offering_placeholder,
        height=140,
        help=offering_help,
        key="offering_desc_input"
    )
    
    # ========================================================================
    # BRAIN MODE (MODE-AWARE)
    # ========================================================================
    
    if mode_pipeline == 'FIND_MY_CLIENTS':
        brain_modes = [
            "Agency Sales Brain",
            "Founder Outreach Brain",
            "Service Provider Brain"
        ]
        default_brain = 0
    else:
        brain_modes = [
            "SaaS Sales Brain",
            "Agency Lead Brain",
            "Investor Outreach Brain",
            "Hiring Brain"
        ]
        default_brain = 0
    
    niche_mode = st.selectbox(
        "🧠 Brain Mode",
        brain_modes,
        index=default_brain,
        help="Adapts signals, tone, and CTAs to your use case",
        key="niche_mode_select"
    )
    
    # Offer validation
    if st.button("🔍 Validate Offer", key="validate_offer_btn"):
        if offering_desc and target_desc:
            with st.spinner("Validating offer..."):
                try:
                    from services.offer_validation import validate_offer
                    validation = validate_offer(offering_desc, target_desc, niche_mode)
                    
                    if validation['is_strong']:
                        st.success(f"✅ Offer score: {validation['score']}/100")
                    else:
                        st.warning(f"⚠️ Offer score: {validation['score']}/100")
                        
                        if validation.get('issues'):
                            st.write("**Issues:**")
                            for issue in validation['issues']:
                                st.write(f"- {issue}")
                        
                        if validation.get('suggested_rewrite'):
                            st.write("**Suggested improvement:**")
                            st.info(validation['suggested_rewrite'])
                except ImportError:
                    st.warning("Offer validation service not available")
        else:
            st.error("Fill in both target and offering first")

with col2:
    st.subheader("📧 Outreach Settings")
    
    sender_name = st.text_input(
        "Your Name",
        placeholder="Alex Johnson",
        key="sender_name_input"
    )
    
    sender_company = st.text_input(
        "Your Company",
        placeholder="TechCorp",
        key="sender_company_input"
    )
    
    calendar_link = st.text_input(
        "Calendar Link (optional)",
        placeholder="https://calendly.com/yourname",
        help="Include for easier booking",
        key="calendar_link_input"
    )
    
    # ========================================================================
    # MODE-AWARE COMPANY COUNT (FIX #7)
    # ========================================================================
    
    col2a, col2b = st.columns(2)
    
    with col2a:
        # Get mode-specific limits
        if mode_pipeline == 'FIND_MY_CLIENTS':
            max_allowed = 5
            default_value = 3
            help_text = "🎯 Agency mode: 2-5 companies max (quality over quantity)"
        else:
            max_allowed = 10
            default_value = 5
            help_text = "⚠️ Max 10 per run to avoid rate limits. Run multiple times for larger lists."
        
        num_companies = st.number_input(
            "Companies to Find",
            min_value=1,
            max_value=max_allowed,
            value=default_value,
            help=help_text,
            key="num_companies_input"
        )
        
        # Visual indicator
        if num_companies >= max_allowed:
            st.caption(f"🔴 At maximum ({max_allowed})")
        elif num_companies >= max_allowed - 2:
            st.caption(f"🟡 Near maximum")
        else:
            st.caption(f"🟢 Within limits")
    
    with col2b:
        # Email style (mode-aware)
        if mode_pipeline == 'FIND_MY_CLIENTS':
            email_styles = [
                "Founder-to-Founder",
                "Consultative",
                "Professional"
            ]
            default_style = 0
        else:
            email_styles = [
                "Professional",
                "Casual",
                "Consultative",
                "Executive"
            ]
            default_style = 0
        
        email_style = st.selectbox(
            "Email Style",
            email_styles,
            index=default_style,
            help="Choose tone and format",
            key="email_style_select"
        )

# ============================================================================
# MODE-SPECIFIC WARNING BANNER
# ============================================================================

if mode_pipeline == 'FIND_MY_CLIENTS':
    st.warning("""
    ### 🎯 Agency Finding Mode Active
    
    **What this will do:**
    - Find 2-5 agencies matching your ICP
    - Filter OUT all SaaS/product companies
    - Focus on founder/owner-level contacts
    - Target referral dependency & lead flow signals
    
    **Expected rejection rate:** 70%+ (by design)
    
    **Output:** High-quality leads for manual founder outreach
    """)
else:
    st.info("""
    ### 🏢 Client Campaign Mode
    
    **What this will do:**
    - Find up to 10 companies matching client's ICP
    - Identify decision makers based on problem type
    - Generate multi-channel outreach sequences
    
    **Expected rejection rate:** 60%+ (quality filter)
    
    **Output:** Deliverable for client review
    """)

st.divider()


# ============================================================================
# ACTION BUTTON (FIXED - Only ONE handler)
# ============================================================================

if st.button("🚀 Start Outreach Campaign", type="primary", use_container_width=True, key="start_campaign_top"):
    # Validation
    if not (has_gemini or has_openai):
        st.error("⚠️ Configure at least one AI provider in sidebar")
        st.stop()
    if not exa_key:
        st.error("⚠️ Exa API key required for research")
        st.stop()
    if not target_desc or not offering_desc:
        st.error("⚠️ Fill in target companies and offering")
        st.stop()
    if not sender_name or not sender_company:
        st.error("⚠️ Fill in your name and company")
        st.stop()
    
    # ========================================================================
    # RUN PIPELINE
    # ========================================================================
    
    try:
        progress = st.progress(0)
        status = st.empty()
        
        # Initialize agents
        status.info("Initializing AI agents...")
        
        # Get AI config from session state
        has_gemini = st.session_state.get('has_gemini', False)
        has_openai = st.session_state.get('has_openai', False)
        openai_model = st.session_state.get('openai_model', 'gpt-4o')
        gemini_model = st.session_state.get('gemini_model', 'gemini-2.0-flash-exp')

        # Validate at least one provider
        if not has_gemini and not has_openai:
            st.error("❌ Configure OpenAI or Gemini in the sidebar first")
            st.stop()

        company_agents = create_company_finder_agents(
            has_gemini=has_gemini,
            has_openai=has_openai,
            openai_model=openai_model,
            gemini_model=gemini_model
        )

        contact_agents = create_contact_finder_agents(
            has_gemini=has_gemini,
            has_openai=has_openai,
            openai_model=openai_model,
            gemini_model=gemini_model
        )

        research_agents = create_research_agents(niche_mode)

        email_agents = create_email_writer_agents(
            email_style,
            niche_mode,
            openai_model,
            gemini_model
        )
        
        agent_openai = company_agents[0]
        agent_gemini = company_agents[1]
        
        progress.progress(10)
        
        # ====================================================================
        # RUN SELECTED PIPELINE MODE
        # ====================================================================
        
        results = None

        if mode == 'fully_cloud':
            status.info("☁️ Running FULLY CLOUD pipeline (all stages use cloud AI)...")
            
            results = run_fully_cloud_pipeline(
                agent_openai, agent_gemini,
                target_desc.strip(),
                offering_desc.strip(),
                sender_name.strip(),
                sender_company.strip(),
                calendar_link.strip() or None,
                int(num_companies),
                niche_mode
            )

            if not results:
                st.error("Pipeline failed. Fix the error above.")
                st.stop()
            
        else:  # hybrid
            status.info("⚡ Running HYBRID pipeline (2 local + 5 cloud stages)...")
            
            results = run_hybrid_pipeline(
                agent_openai, agent_gemini,
                target_desc, offering_desc,
                sender_name, sender_company, calendar_link,
                num_companies, niche_mode, email_style,
            )

            if not results:
                st.error("Pipeline failed. Fix the error above.")
                st.stop()       
            
            leads = results.get('leads', [])
            companies = results.get('companies', [])
            research = results.get('research', [])
            emails = results.get('emails', [])
            rejected_companies = results.get('rejected_companies', [])
        
            # FIX #6: Mode-aware metrics
            pipeline_mode = st.session_state.get('pipeline_mode_type', 'FIND_MY_CLIENTS')
            
            if pipeline_mode == 'FIND_MY_CLIENTS':
                # Agency Mode Metrics
                st.subheader("📊 Agency Discovery Results")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Agencies Discovered", len(companies))
                with col2:
                    st.metric("Founders Identified", len(leads))
                with col3:
                    manual_count = sum(1 for l in leads if l.get('manual_lookup_required'))
                    st.metric("Manual Lookup Needed", manual_count)
                
                # Geographic distribution
                with st.expander("📍 Geographic Distribution"):
                    geo_dist = {}
                    for company in companies:
                        geo = company.get('discovered_geo', 'unknown')
                        geo_dist[geo] = geo_dist.get(geo, 0) + 1
                    for geo, count in geo_dist.items():
                        st.write(f"- {geo.title()}: **{count}** agencies")
                
                # Next steps for agency mode
                st.subheader("🎯 Next Steps")
                st.info("""
                **What to do now:**
                1. **Manual research** - Check each agency's LinkedIn and website
                2. **Find founder contact** - Use LinkedIn or Hunter.io
                3. **Personalize outreach** - Reference their specific work/clients
                4. **Send 1-2 per day** - Quality over volume
                5. **Track what works** - Note which agency types respond best
                
                **Expected timeline:**
                - Day 1-3: Send personalized messages
                - Day 4-7: First replies come in
                - Day 10-14: Follow up with non-responders
                
                **Success looks like:**
                - 10-20% reply rate (agencies are more responsive than enterprises)
                - 2-3 conversations per 10 outreach attempts
                - Learning which agency types need your help most
                """)
            
            else:
                # Client Mode Metrics
                st.subheader("📊 Campaign Insights")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Companies Found", len(companies))
                    st.metric("Leads Generated", len(leads))
                with col2:
                    tier1_count = sum(1 for c in companies if c.get('signal_tier') == 'TIER1')
                    tier2_count = sum(1 for c in companies if c.get('signal_tier') == 'TIER2')
                    st.metric("TIER1 Signals", tier1_count)
                    st.metric("TIER2 Signals", tier2_count)
                with col3:
                    manual_count = sum(1 for l in leads if l.get('manual_lookup_required'))
                    auto_count = len(leads) - manual_count
                    st.metric("Auto Contacts", auto_count)
                    st.metric("Manual Lookup", manual_count)
                
                # Signal distribution
                with st.expander("🎯 Signal Distribution (What's Working)"):
                    signal_types = {}
                    for company in companies:
                        signal = company.get('signal', 'Unknown')[:50]
                        signal_types[signal] = signal_types.get(signal, 0) + 1
                    st.write("**Top Signals Found:**")
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
                
                # Next steps for client mode
                st.subheader("🎯 Next Steps")
                st.info("""
                **What to do now:**
                1. **Review the leads** - Focus on TIER1 signals first
                2. **Customize if needed** - AI wrote 80%, you add 20%
                3. **Send emails** - Use your email tool or Gmail
                4. **Track responses** - Note which signals get replies
                5. **Follow up** - Use the 3 follow-up angles provided
                
                **Expected timeline:**
                - Day 1-2: Replies start coming in
                - Day 3-5: Peak response window
                - Day 7-10: Send first follow-up
                - Day 14-17: Send second follow-up
                - Day 21: Send breakup email
                
                **Success looks like:**
                - 5-10% reply rate (1-2 replies per 20 emails)
                - 1-2 meetings booked per 20 emails
                - Clear learning about which signals work
                
                ❌ **NOT success:**
                - Zero replies = messaging/targeting issue
                - High opens, no replies = weak CTA or value prop
                - No opens = deliverability issue
                """)
            
            progress.progress(100)

                
        # ========================================================================
        # FIX #9: EXPECTATION MANAGEMENT DISCLAIMER (MANDATORY)
        # ========================================================================

        st.divider()

        # Get mode for context
        mode_pipeline = st.session_state.get('pipeline_mode_type', 'FIND_CLIENTS_FOR_CUSTOMER')

        # Universal disclaimer (applies to ALL modes)
        st.warning("""
        ### ⚠️ Important: What This Output Represents

        **This output indicates opportunity signals, not guaranteed intent.**

        #### What you're getting:
        - ✅ Companies with observable changes (signals)
        - ✅ Interpretation of what those changes might mean
        - ✅ Suggested outreach angles based on inference
        - ✅ Identified decision makers (or lookup guidance)

        #### What you're NOT getting:
        - ❌ Guaranteed meetings or responses
        - ❌ Confirmed buying intent
        - ❌ Ready-to-close opportunities
        - ❌ "Hot leads" expecting your call

        ---

        **Your goal:** Start conversations and learn from the market.

        **Success metric:** Reply rate and conversation quality, not instant meetings.

        **Realistic expectations:**
        - 📧 **Email reply rate:** 5-15% (industry standard for cold outreach)
        - 📞 **Meeting booking rate:** 1-5% (from total sent)
        - 💬 **Conversation quality:** High (because signals are real)

        ---
        """)

        # Mode-specific guidance
        if mode_pipeline == 'FIND_MY_CLIENTS':
            st.info("""
            ### 🎯 Agency Mode: Next Steps

            **Recommended approach:**
            1. **Review each lead manually** - Read signal interpretation carefully
            2. **LinkedIn research first** - Check founder's recent posts/activity
            3. **Personalize messaging** - Reference their specific situation
            4. **Send 1-2 per day max** - Quality conversations > volume
            5. **Track what works** - Note which signals get best responses

            **Remember:** You're messaging fellow founders. Respect their time.
            """)
        else:
            st.info("""
            ### 🏢 Client Campaign: Delivery Guidance

            **Before delivering to client:**
            1. ✅ Review each company's signal interpretation
            2. ✅ Verify contact info looks reasonable (check email patterns)
            3. ✅ Read "rejection_risk" founders notes for each lead
            4. ✅ Explain the signal-based approach to your client

            **Set client expectations:**
            - This is intelligence, not guaranteed intent
            - Goal is starting conversations, not instant closes
            - Some contacts may not respond (normal for outbound)
            - Best results come from thoughtful, personalized follow-up

            **Your value:** Quality targeting + interpretation + suggested angles
            """)

        # Quality indicator
        num_leads = len(st.session_state.get('leads', []))

        if num_leads == 0:
            st.error("""
            ### 🚫 No Leads Generated

            **This happened because:**
            - All companies were rejected by quality filters (by design)
            - Signals were too weak or vague
            - No clear pain owners identified

            **What to do:**
            1. Try different target criteria
            2. Adjust your offering to match stronger signals
            3. Consider if your ICP has observable triggers

            **This is normal:** 60-70% rejection rate is expected. Sometimes it's 100%.
            """)
        elif num_leads <= 2:
            st.warning("""
            ### ⚠️ Low Output Volume

            **This is by design, not a bug.**

            Most companies were rejected because:
            - Signals were too weak to justify outreach
            - No clear pain owner identified
            - Timing not urgent enough

            **Low volume = higher quality.** These leads passed aggressive filters.
            """)
        else:
            st.success(f"""
            ### ✅ {num_leads} Qualified Leads Generated

            **Quality indicators:**
            - All passed ICP enforcement
            - All have interpretable signals
            - All have identified decision makers
            - All passed 60-70% rejection filters

            **These are conversation starters, not guaranteed meetings.**
            """)

        st.divider()

                
        # Display basic metrics
        metadata = results.get('metadata', {})
        
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Found", metadata.get('total_companies_found', 0))
        with metric_cols[1]:
            st.metric("Cleaned", metadata.get('companies_after_cleaning', 0))
        with metric_cols[2]:
            st.metric("Strong Signals", metadata.get('companies_with_strong_signals', 0))
        with metric_cols[3]:
            st.metric("Emails", metadata.get('total_emails', 0))
        
        # Show cost savings if hybrid
        if mode == 'hybrid' and metadata.get('local_stages_used', 0) > 0:
            st.info(f"💰 Used {metadata['local_stages_used']} FREE local stages + {metadata['cloud_stages_used']} cloud stages")
        
        st.divider()
        
        # ================================================================
        # UPGRADE 4: CAMPAIGN READINESS GATE
        # =============================================================        
        # FIX #5: Campaign Readiness (skip in agency mode)
        pipeline_mode = st.session_state.get('pipeline_mode_type', 'FIND_MY_CLIENTS')

        if pipeline_mode == 'FIND_MY_CLIENTS':
            st.subheader("🛡️ Campaign Readiness")
            st.info("""
            ℹ️ **Campaign Readiness skipped in Agency Mode**

            You're prospecting for your own clients, not delivering a paid campaign.

            **Why this is skipped:**
            - ❌ ROI checks don't apply (you're not selling yet, just starting conversations)
            - ❌ ICP strictness is too rigid (you're in exploration mode)
            - ❌ Fatal objections are irrelevant (low-risk outreach)

            **What matters instead:**
            - ✅ Quality of agencies found
            - ✅ Reachability of founders
            - ✅ Clarity of your value proposition
            """)
            st.divider()
        else:
            # Client mode: Show full campaign readiness
            try:
                st.subheader("🛡️ Campaign Readiness Report")
                readiness = evaluate_campaign_readiness(
                    offering_desc, target_desc, sender_name, sender_company
                )

                readiness_col1, readiness_col2, readiness_col3 = st.columns(3)
                with readiness_col1:
                    if readiness['readiness'] == 'READY':
                        st.success(f"✅ {readiness['recommendation']}")
                    elif readiness['readiness'] == 'WARNING':
                        st.warning(f"⚠️ {readiness['recommendation']}")
                    else:
                        st.error(f"🚫 {readiness['recommendation']}")
                with readiness_col2:
                    st.metric("Offer Score", f"{readiness['offer_score']}/10")
                with readiness_col3:
                    st.metric("ICP Score", f"{readiness['icp_score']}/10")

                # Show issues if any
                if readiness['offer_issues'] or readiness['icp_issues']:
                    with st.expander("⚠️ Issues Found - Click to See Details"):
                        if readiness['offer_issues']:
                            st.write("**Offer Issues:**")
                            for issue in readiness['offer_issues']:
                                st.write(f"- {issue}")
                        if readiness['icp_issues']:
                            st.write("**ICP Issues:**")
                            for issue in readiness['icp_issues']:
                                st.write(f"- {issue}")
                        if readiness['improvements']:
                            st.write("**Suggested Improvements:**")
                            for key, value in readiness['improvements'].items():
                                st.info(value)

                if readiness['fatal_objections']:
                    st.error("**Fatal Objections:**")
                    for obj in readiness['fatal_objections']:
                        st.write(f"- {obj}")
                st.divider()

            except ImportError:
                st.warning("⚠️ Campaign readiness module not found - skipping validation")

        # ================================================================
        # UPGRADE 5: POST-CAMPAIGN INSIGHTS (Anti-Churn)
        # =============================================================        
        try:
            from utils.campaign_insights import generate_campaign_insights, format_insights_for_export        
            st.header("📊 Campaign Insights & Market Intelligence")
            insights = generate_campaign_insights(results)
            # Executive Summary
            with st.expander("📈 Executive Summary", expanded=True):
                exec_sum = insights['executive_summary']
                sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
                with sum_col1:
                    st.metric("Total Discovered", exec_sum['total_companies_discovered'])
                with sum_col2:
                    st.metric("Quality Passed", exec_sum['companies_passed_quality_filter'])
                with sum_col3:
                    st.metric("Rejection Rate", exec_sum['rejection_rate'])
                with sum_col4:
                    st.metric("Avg Confidence", f"{exec_sum['avg_confidence_score']:.0f}")
                st.write("")
                st.write(f"**High-Confidence Leads (80%+):** {exec_sum['high_confidence_leads']}")
                st.write(f"**Total Outreach Sequences:** {exec_sum['total_outreach_sequences']}")
            # Signal Performance Analysis
            with st.expander("🎯 Which Signals Worked (Market Intelligence)"):
                sig_perf = insights['signal_performance']
                st.success(f"✅ **Best Performing Signal:** {sig_perf['best_performing_signal']}")
                st.error(f"⚠️ **Worst Performing Signal:** {sig_perf['worst_performing_signal']}")
                st.write("")
                st.write("**Signal Performance Breakdown:*")
                for sig_type, data in sig_perf['performance_by_type'].items():
                    conf = data['avg_confidence']
                    emoji = "🟢" if conf >= 80 else "🟡" if conf >= 60 else "🔴"
                    st.write(f"{emoji} **{sig_type}**: {data['count']} companies | "
                            f"{conf:.0f}% confidence → {data['recommendation']}")
                st.write("")
                st.write("**Urgency Distribution:**")
                for urgency, count in sig_perf['urgency_distribution'].items():
                    st.write(f"- {urgency}: {count} companie")
            # Title Analysis
            with st.expander("👥 Which Titles To Target"):
                title_analysis = insights['title_analysi']
                st.info(f"**Recommendation:** {title_analysis['recommendation']}")
                st.write("")
                st.write("**Most Common Decision Maker Titles:**")
                for title, count in title_analysis['most_common_titles'].items():
                    st.write(f"- **{title}**: {count} contact")
                if title_analysis['problem_owner_titles']:
                    st.write("")
                    st.write("**Confirmed Problem Owners:**")
                    for title in title_analysis['problem_owner_titles']:
                        st.write(f"- {title}")
            # Rejection Learnings
            with st.expander("🔴 What Didn't Work (Learning Opportunities)"):
                rejection = insights['rejection_learning']
                st.write(f"**Total Rejected:** {rejection['total_rejected']} companie")
                st.write("")
                st.write("**Top Rejection Reasons:**")
                for reason, count in rejection['top_rejection_reasons'].items():
                    st.write(f"- {reason}: {count} companie")
                if rejection['key_learnings']:
                    st.write("")
                    st.write("**Key Learnings for Next Campaign:**")
                    for learning in rejection['key_learnings']:
                        st.warning(learning)
            # Next Steps (Most Important)
            with st.expander("🚀 What To Do Next (Actionable)", expanded=True):
                st.write("**Your Next Steps:**")
                for i, step in enumerate(insights['next_steps'], 1):
                    st.write(f"{i}. {step}")
            st.divider()
            # Export Options with Insights
            st.subheader("📥 Export Campaign Results")
            export_col1, export_col2, export_col3 = st.columns(3)
            
            with export_col1:
                st.download_button(
                    "⬇️ Download Leads CSV",
                    csv_data,
                    file_name=f"leads_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )
            with export_col2:
                insights_report = format_insights_for_export(insights)
                st.download_button(
                    "📊 Download Insights Report",
                    insights_report,
                    file_name=f"insights_{time.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with export_col3:
                full_export = {
                    'campaign': {
                        'target': target_desc,
                        'offering': offering_desc,
                        'sender': f"{sender_name} at {sender_company}",
                        'mode': mode,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    },
                    'results': results,
                    'insights': insights,
                    'readiness': readiness if 'readiness' in locals() else {}
                }
                
                st.download_button(
                    "📦 Download Full Results (JSON)",
                    json.dumps(full_export, indent=2),
                    file_name=f"campaign_full_{time.strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        except ImportError:
            st.warning("⚠️ Campaign insights module not found - showing basic results only")

            # Basic export without insights
            st.subheader("📥 Export Campaign Results")
            st.download_button(
                "⬇️ Download Leads CSV",
                csv_data,
                file_name=f"leads_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
        
    except Exception as e:
        st.error(f"❌ Pipeline failed: {str(e)}")
        import traceback
        with st.expander("🐛 Error Details"):
            st.code(traceback.format_exc())
        st.stop()


# ============================================================================
# DISPLAY DETAILED RESULTS
# ============================================================================

results = st.session_state.get('gtm_results_v2')
leads = st.session_state.get('leads_v2', [])
csv_data = st.session_state.get('csv_v2', '')

if results:
    st.divider()
    st.header("📋 Detailed Campaign Results")
    
    # ========================================================================
    # UPGRADE 1: Show Signal Interpretations
    # ========================================================================
    
    st.subheader("🏢 Companies (With Signal Interpretation)")
    companies = results.get('companies', [])
    
    if companies:
        for idx, c in enumerate(companies, 1):
            signal_interp = c.get('signal_interpretation', {})
            quality_score = c.get('quality_score', 0)
            
            score_color = "🟢" if quality_score >= 80 else "🟡" if quality_score >= 70 else "🔴"
            
            with st.expander(f"{idx}. {c.get('name', 'Unknown')} | {score_color} Quality: {quality_score}/100"):
                st.write(f"**Website:** {c.get('website', 'N/A')}")
                
                # Original signal info
                st.write(f"**🚨 Signal:** {c.get('signal', 'N/A')}")
                st.write(f"**Signal Tier:** {c.get('signal_tier', 'N/A')}")
                st.write(f"**Signal Score:** {c.get('signal_score', 0)}/5")
                
                st.divider()
                
                # Signal Interpretation Layer
                if signal_interp:
                    st.write("### 🔍 Signal Interpretation")
                    st.write(f"**→ What it implies:** {signal_interp.get('operational_implication', 'N/A')}")
                    st.write(f"**→ Who feels pain:** {signal_interp.get('pain_owner_role', 'Unknown')} ({signal_interp.get('pain_owner_department', 'Unknown')})")
                    st.write(f"**→ Outreach angle:** {signal_interp.get('outreach_angle', 'N/A')}")
                    
                    urgency = signal_interp.get('urgency_level', 'LOW')
                    urgency_color = "🔴" if urgency == "CRITICAL" else "🟠" if urgency == "HIGH" else "🟡" if urgency == "MEDIUM" else "⚪"
                    
                    st.write(f"**Urgency:** {urgency_color} {urgency}")
                    st.write(f"**Interpretation Confidence:** {signal_interp.get('interpretation_confidence', 0)}%")
                
                st.divider()
                
                # Other info
                st.write(f"**Why Fit:** {c.get('why_fit', 'N/A')}")
                st.write(f"**Offer Alignment:** {c.get('offer_alignment', 'N/A')}")
    else:
        st.info("No companies found")
    
    # ========================================================================
    # CONTACTS
    # ========================================================================
    
    st.divider()
    st.subheader("👥 Decision Makers")
    contacts = results.get('contacts', [])
    
    if contacts:
        for c in contacts:
            with st.expander(f"{c.get('name', 'Unknown')} ({len(c.get('contacts', []))} contacts)"):
                for p in c.get('contacts', []):
                    is_owner = "🎯 PROBLEM OWNER" if p.get('is_problem_owner') else ""
                    st.write(f"**{p.get('full_name')}** {is_owner}")
                    st.write(f"- {p.get('title')} | {p.get('email')}")
                    st.divider()
    else:
        st.info("No contacts found")
    
    # ========================================================================
    # EMAILS
    # ========================================================================
    
    st.divider()
    st.subheader("📧 Multi-Channel Outreach")
    emails = results.get('emails', [])
    
    if emails:
        for i, e in enumerate(emails, 1):
            conf = e.get('confidence', 0)
            conf_color = "🟢" if conf >= 80 else "🟡" if conf >= 60 else "🔴"
            
            with st.expander(f"#{i}: {e.get('company')} → {e.get('contact')} | {conf_color} {conf}/100"):
                st.write(f"**Subject:** {e.get('subject')}")
                st.text_area("Body", e.get('body', ''), height=200, key=f"email_{i}")
    else:
        st.info("No emails generated")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    pass  # Streamlit runs automatically