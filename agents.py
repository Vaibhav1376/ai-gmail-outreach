"""
Agent factories with dual-model ensemble support
Core workflow patterns from reference file + Tier A/B/C enhancements
"""
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from agno.agent import Agent  # ✅ CORRECT IMPORT
from agno.db.sqlite import SqliteDb  # ✅ CORRECT IMPORT
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.tools.exa import ExaTools

from config.prompts import (
    get_company_finder_instructions,
    get_contact_finder_instructions,
    get_research_instructions,
    get_email_writer_instructions,
)


# ============================================================================
# CONFIGURATION & UTILITIES
# ============================================================================

def get_ai_config() -> Dict[str, Any]:
    """Get AI provider configuration from session state"""
    return st.session_state.get('ai_config', {
        'has_gemini': False,
        'has_openai': False,
        'use_ensemble': False,
        'ensemble_method': 'Quality',
        'gemini_model': 'gemini-2.5-flash',
        'openai_model': 'gpt-4o',
        'temperature': 0.7,
        'max_tokens': 2048
    })


# ============================================================================
# ENSEMBLE LOGIC
# ============================================================================

def select_best_response(responses: List[Dict], method: str) -> Dict:
    """Select best response based on ensemble method"""
    if not responses:
        raise ValueError("No responses to select from")
    if len(responses) == 1:
        return responses[0]
    
    if method == "Confidence-Based":
        return max(responses, key=lambda x: x.get('confidence', 0))
    elif method == "Longest":
        return max(responses, key=lambda x: len(x.get('content', '')))
    elif method == "Fastest":
        return min(responses, key=lambda x: x.get('latency', float('inf')))
    elif method == "Quality":
        # Select most complete JSON response
        best = responses[0]
        max_items = 0
        for r in responses:
            try:
                content = r.get('content', '')
                if content.count('{') > 0 and content.count('}') > 0:
                    items = len(content)
                    if items > max_items:
                        max_items = items
                        best = r
            except:
                continue
        return best
    
    return responses[0]


def run_agent_with_ensemble(
    agent_openai: Optional[Agent],
    agent_gemini: Optional[Agent],
    prompt: str,
    agent_name: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Run agent with ensemble support + retry logic
    """
    config = get_ai_config()
    responses = []
    errors = []
    
    def run_with_retry(agent, model_name: str, max_attempts: int = 3):
        """Run agent with exponential backoff retry"""
        for attempt in range(1, max_attempts + 1):
            try:
                start = time.time()
                resp = agent.run(prompt)
                latency = time.time() - start
                
                content = str(resp.content)
                
                # Validate JSON presence
                if "{" not in content or "}" not in content:
                    if attempt < max_attempts:
                        st.warning(f"⚠️ {model_name} non-JSON response. Retry {attempt}/{max_attempts}")
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError(f"No JSON after {max_attempts} attempts")
                
                return {
                    'content': content,
                    'source': model_name,
                    'latency': latency,
                    'confidence': 0.9
                }
            
            except Exception as e:
                error_msg = str(e)
                
                # Rate limit handling
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    if attempt < max_attempts:
                        wait_time = (10 * (2 ** (attempt - 1)))
                        st.warning(f"⏳ {model_name} rate limit. Wait {wait_time}s ({attempt}/{max_attempts})")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded: {error_msg}")
                
                # JSON errors
                if "JSON" in error_msg or "parse" in error_msg.lower():
                    if attempt < max_attempts:
                        st.warning(f"⚠️ {model_name} invalid JSON. Retry {attempt}/{max_attempts}")
                        time.sleep(2)
                        continue
                    else:
                        raise Exception(f"Invalid JSON: {error_msg}")
                
                # Other errors
                raise Exception(f"{model_name} error: {error_msg}")
        
        raise Exception(f"{model_name} failed after {max_attempts} retries")
    
    # Ensemble mode
    if config['use_ensemble'] and agent_openai and agent_gemini:
        # Try OpenAI
        if agent_openai:
            try:
                with st.spinner(f"🟢 {agent_name} (OpenAI)..."):
                    response = run_with_retry(agent_openai, f"OpenAI ({config['openai_model']})")
                    responses.append(response)
            except Exception as e:
                error_detail = str(e)[:300]
                st.error(f"❌ OpenAI: {error_detail}")
                errors.append(f"OpenAI: {error_detail}")
        
        # Delay between providers
        if responses and agent_gemini:
            time.sleep(3)
        
        # Try Gemini
        if agent_gemini:
            try:
                with st.spinner(f"🔷 {agent_name} (Gemini)..."):
                    response = run_with_retry(agent_gemini, f"Gemini ({config['gemini_model']})")
                    responses.append(response)
            except Exception as e:
                error_detail = str(e)[:300]
                st.error(f"❌ Gemini: {error_detail}")
                errors.append(f"Gemini: {error_detail}")
        
        # Check if we got any responses
        if not responses:
            error_summary = "\n".join(errors)
            raise ValueError(
                f"❌ Both models failed for {agent_name}\n\n"
                f"Errors:\n{error_summary}\n\n"
                f"💡 Try: Use single model or wait 60s"
            )
        
        best = select_best_response(responses, config['ensemble_method'])
        metadata = {
            'ensemble': True,
            'selected_source': best['source'],
            'method': config['ensemble_method'],
            'total_responses': len(responses),
            'errors': errors if errors else None
        }
        return best['content'], metadata
    
    # Single model mode
    agent = agent_openai if agent_openai else agent_gemini
    if not agent:
        raise ValueError("❌ No agent available. Configure at least one AI provider.")
    
    model_name = f"OpenAI ({config['openai_model']})" if agent_openai else f"Gemini ({config['gemini_model']})"
    
    try:
        with st.spinner(f"🤖 {agent_name} ({model_name})..."):
            response = run_with_retry(agent, model_name)
            metadata = {'source': model_name, 'ensemble': False}
            return response['content'], metadata
    except Exception as e:
        error_detail = str(e)[:500]
        st.error(f"❌ {agent_name} failed: {error_detail}")
        raise ValueError(
            f"❌ {agent_name} failed with {model_name}\n\n"
            f"Error: {error_detail}\n\n"
            f"💡 Solutions:\n"
            f"1. Wait 60 seconds\n"
            f"2. Switch model\n"
            f"3. Reduce company count\n"
            f"4. Check API key"
        )


# ============================================================================
# AGENT FACTORIES (ALL 4 REQUIRED)
# ============================================================================

def create_company_finder_agents(niche_mode: str) -> Tuple[Optional[Agent], Optional[Agent]]:
    """Create company finder agents"""
    config = get_ai_config()
    exa_tools = ExaTools()
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    instructions = get_company_finder_instructions(niche_mode)
    
    agent_openai = None
    agent_gemini = None
    
    # OpenAI
    if config['has_openai']:
        try:
            agent_openai = Agent(
                model=OpenAIChat(
                    id=config['openai_model'],
                    api_key=os.environ.get('OPENAI_API_KEY'),
                    response_format={"type": "json_object"}
                ),
                tools=[exa_tools],
                db=db,
                enable_user_memories=True,
                add_history_to_context=True,
                num_history_runs=6,
                session_id="gtm_company_openai_v2",
                instructions=instructions,
            )
        except Exception as e:
            st.warning(f"OpenAI CompanyFinder: {str(e)[:100]}")
            agent_openai = None
    
    # Gemini
    if config['has_gemini'] and (config['use_ensemble'] or not agent_openai):
        try:
            gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
            if gemini_key:
                gemini_model = config['gemini_model']
                is_lite = "lite" in gemini_model.lower() or "8b" in gemini_model.lower()
                
                if not is_lite:
                    model = Gemini(
                        id=gemini_model,
                        api_key=gemini_key,
                        generation_config={"response_mime_type": "application/json"}
                    )
                else:
                    model = Gemini(id=gemini_model, api_key=gemini_key)
                
                agent_gemini = Agent(
                    model=model,
                    tools=[exa_tools],
                    db=db,
                    enable_user_memories=True,
                    add_history_to_context=True,
                    num_history_runs=6,
                    session_id="gtm_company_gemini_v2",
                    instructions=instructions,
                )
        except Exception as e:
            st.warning(f"Gemini CompanyFinder: {str(e)[:100]}")
            agent_gemini = None
    
    return agent_openai, agent_gemini


def create_contact_finder_agents() -> Tuple[Optional[Agent], Optional[Agent]]:
    """Create contact finder agents"""
    config = get_ai_config()
    exa_tools = ExaTools()
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    instructions = get_contact_finder_instructions()
    
    agent_openai = None
    agent_gemini = None
    
    # OpenAI
    if config['has_openai']:
        try:
            agent_openai = Agent(
                model=OpenAIChat(
                    id=config['openai_model'],
                    api_key=os.environ.get('OPENAI_API_KEY'),
                    response_format={"type": "json_object"}
                ),
                tools=[exa_tools],
                db=db,
                enable_user_memories=True,
                add_history_to_context=True,
                num_history_runs=6,
                session_id="gtm_contact_openai_v2",
                instructions=instructions,
            )
        except Exception as e:
            st.warning(f"OpenAI ContactFinder: {str(e)[:100]}")
            agent_openai = None
    
    # Gemini
    if config['has_gemini'] and (config['use_ensemble'] or not agent_openai):
        try:
            gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
            if gemini_key:
                gemini_model = config['gemini_model']
                is_lite = "lite" in gemini_model.lower() or "8b" in gemini_model.lower()
                
                if not is_lite:
                    model = Gemini(
                        id=gemini_model,
                        api_key=gemini_key,
                        generation_config={"response_mime_type": "application/json"}
                    )
                else:
                    model = Gemini(id=gemini_model, api_key=gemini_key)
                
                agent_gemini = Agent(
                    model=model,
                    tools=[exa_tools],
                    db=db,
                    enable_user_memories=True,
                    add_history_to_context=True,
                    num_history_runs=6,
                    session_id="gtm_contact_gemini_v2",
                    instructions=instructions,
                )
        except Exception as e:
            st.warning(f"Gemini ContactFinder: {str(e)[:100]}")
            agent_gemini = None
    
    return agent_openai, agent_gemini


def create_research_agents(niche_mode: str) -> Tuple[Optional[Agent], Optional[Agent]]:
    """Create research agents"""
    config = get_ai_config()
    exa_tools = ExaTools()
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    instructions = get_research_instructions(niche_mode)
    
    agent_openai = None
    agent_gemini = None
    
    # OpenAI
    if config['has_openai']:
        try:
            agent_openai = Agent(
                model=OpenAIChat(
                    id=config['openai_model'],
                    api_key=os.environ.get('OPENAI_API_KEY'),
                    response_format={"type": "json_object"}
                ),
                tools=[exa_tools],
                db=db,
                enable_user_memories=True,
                add_history_to_context=True,
                num_history_runs=6,
                session_id="gtm_research_openai_v2",
                instructions=instructions,
            )
        except Exception as e:
            st.warning(f"OpenAI Research: {str(e)[:100]}")
            agent_openai = None
    
    # Gemini
    if config['has_gemini'] and (config['use_ensemble'] or not agent_openai):
        try:
            gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
            if gemini_key:
                gemini_model = config['gemini_model']
                is_lite = "lite" in gemini_model.lower() or "8b" in gemini_model.lower()
                
                if not is_lite:
                    model = Gemini(
                        id=gemini_model,
                        api_key=gemini_key,
                        generation_config={"response_mime_type": "application/json"}
                    )
                else:
                    model = Gemini(id=gemini_model, api_key=gemini_key)
                
                agent_gemini = Agent(
                    model=model,
                    tools=[exa_tools],
                    db=db,
                    enable_user_memories=True,
                    add_history_to_context=True,
                    num_history_runs=6,
                    session_id="gtm_research_gemini_v2",
                    instructions=instructions,
                )
        except Exception as e:
            st.warning(f"Gemini Research: {str(e)[:100]}")
            agent_gemini = None
    
    return agent_openai, agent_gemini


def create_email_writer_agents(style_key: str, niche_mode: str) -> Tuple[Optional[Agent], Optional[Agent]]:
    """Create email writer agents"""
    config = get_ai_config()
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    instructions = get_email_writer_instructions(style_key, niche_mode)
    
    agent_openai = None
    agent_gemini = None
    
    # OpenAI
    if config['has_openai']:
        try:
            agent_openai = Agent(
                model=OpenAIChat(
                    id=config['openai_model'],
                    api_key=os.environ.get('OPENAI_API_KEY'),
                    response_format={"type": "json_object"}
                ),
                tools=[],
                db=db,
                enable_user_memories=True,
                add_history_to_context=True,
                num_history_runs=6,
                session_id="gtm_email_openai_v2",
                instructions=instructions,
            )
        except Exception as e:
            st.warning(f"OpenAI EmailWriter: {str(e)[:100]}")
            agent_openai = None
    
    # Gemini
    if config['has_gemini'] and (config['use_ensemble'] or not agent_openai):
        try:
            gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
            if gemini_key:
                gemini_model = config['gemini_model']
                is_lite = "lite" in gemini_model.lower() or "8b" in gemini_model.lower()
                
                if not is_lite:
                    model = Gemini(
                        id=gemini_model,
                        api_key=gemini_key,
                        generation_config={"response_mime_type": "application/json"}
                    )
                else:
                    model = Gemini(id=gemini_model, api_key=gemini_key)
                
                agent_gemini = Agent(
                    model=model,
                    tools=[],
                    db=db,
                    enable_user_memories=True,
                    add_history_to_context=True,
                    num_history_runs=6,
                    session_id="gtm_email_gemini_v2",
                    instructions=instructions,
                )
        except Exception as e:
            st.warning(f"Gemini EmailWriter: {str(e)[:100]}")
            agent_gemini = None
    
    return agent_openai, agent_gemini
