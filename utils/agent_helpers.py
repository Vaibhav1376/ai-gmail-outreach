"""
Agent Helper Functions
Handles agent creation, ensemble logic, and response parsing
"""
import json
import time
import re
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.tools.exa import ExaTools
from agno.db.sqlite import SqliteDb


# ============================================================================
# JSON PARSING
# ============================================================================

def remove_emojis(text: str) -> str:
    """Remove emojis from text that might break JSON parsing"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)


def extract_json_or_raise(text: str) -> Dict[str, Any]:
    """
    Extract JSON from a model response.
    Handles markdown code blocks and malformed responses.
    """
    # Remove emojis first
    text = remove_emojis(text)
    if not text or text.strip() == "":
        raise ValueError("Model returned empty response. Check API key and rate limits.")
    
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try to find JSON block between { }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
    
    # Try to extract from markdown code blocks
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0].strip()
        return json.loads(text)
    elif '```' in text:
        text = text.split('```')[1].strip()
        return json.loads(text)
    
    raise ValueError(f"Failed to parse JSON from response: {text[:200]}")


# ============================================================================
# ENSEMBLE LOGIC
# ============================================================================

def run_agent_with_ensemble(
    agent_openai: Optional[Agent],
    agent_gemini: Optional[Agent],
    prompt: str,
    agent_name: str,
    use_ensemble: bool = False
) -> Tuple[str, Dict]:
    """
    Run agent with optional ensemble support
    
    Args:
        agent_openai: OpenAI agent (optional)
        agent_gemini: Gemini agent (optional)
        prompt: Prompt to send
        agent_name: Name for logging
        use_ensemble: Whether to use both models and select best
    
    Returns:
        (response_content, metadata)
    """
    responses = []
    
    # ========================================================================
    # ENSEMBLE MODE: Run both models
    # ========================================================================
    
    if use_ensemble and agent_openai and agent_gemini:
        
        # OpenAI
        try:
            with st.spinner(f"{agent_name} (OpenAI)..."):
                start = time.time()
                resp_openai = agent_openai.run(prompt)
                latency_openai = time.time() - start
                
                responses.append({
                    'content': str(resp_openai.content),
                    'source': f"OpenAI ({agent_openai.model.id})",
                    'latency': latency_openai,
                    'confidence': 0.9  # Default confidence
                })
        except Exception as e:
            st.warning(f"OpenAI {agent_name} failed: {str(e)[:100]}")
        
        # Gemini
        try:
            with st.spinner(f"{agent_name} (Gemini)..."):
                start = time.time()
                resp_gemini = agent_gemini.run(prompt)
                latency_gemini = time.time() - start
                
                responses.append({
                    'content': str(resp_gemini.content),
                    'source': f"Gemini ({agent_gemini.model.id})",
                    'latency': latency_gemini,
                    'confidence': 0.9
                })
        except Exception as e:
            st.warning(f"Gemini {agent_name} failed: {str(e)[:100]}")
        
        # Select best response
        if not responses:
            raise ValueError(f"Both models failed for {agent_name}")
        
        best = select_best_response(responses, method="Quality")
        
        metadata = {
            'ensemble': True,
            'selected_source': best['source'],
            'method': 'Quality',
            'total_responses': len(responses)
        }
        
        return best['content'], metadata
    
    # ========================================================================
    # SINGLE MODEL MODE
    # ========================================================================
    
    agent = agent_openai if agent_openai else agent_gemini
    
    if not agent:
        raise ValueError("No agent available")
    
    with st.spinner(f"{agent_name}..."):
        resp = agent.run(prompt)
    
    source = f"OpenAI ({agent.model.id})" if agent_openai else f"Gemini ({agent.model.id})"
    
    metadata = {
        'source': source,
        'ensemble': False
    }
    
    return str(resp.content), metadata


def select_best_response(responses: List[Dict], method: str = "Quality") -> Dict:
    """
    Select best response from multiple model outputs
    
    Methods:
    - Quality: Most complete JSON
    - Confidence-Based: Highest confidence score
    - Longest: Most tokens
    - Fastest: Lowest latency
    """
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
        # Select response with most complete JSON
        best = responses[0]
        max_items = 0
        
        for r in responses:
            try:
                data = extract_json_or_raise(r['content'])
                items = sum(
                    len(v) if isinstance(v, list) else 1
                    for v in data.values()
                )
                if items > max_items:
                    max_items = items
                    best = r
            except:
                continue
        
        return best
    
    return responses[0]


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_company_finder_agents(
    has_openai: bool,
    has_gemini: bool,
    openai_model: str,
    gemini_model: str
) -> Tuple[Optional[Agent], Optional[Agent]]:
    """
    Create CompanyFinder agents for both providers
    """
    exa_tools = ExaTools(category="company")
    db = SqliteDb(db_file="/tmp/gtm_outreach.db")
    
    # ✅ UPDATED: Much stricter JSON-only instructions
    instructions = [
        "You are a JSON-only API. Return ONLY valid JSON, nothing else.",
        "NO conversational text. NO explanations. NO markdown code blocks.",
        "NO phrases like 'I found', 'Here are', 'Let me', etc.",
        "",
        "RULES:",
        "1. Start response with { and end with }",
        "2. Use double quotes for all strings",
        "3. No text before or after the JSON object",
        "4. If you cannot complete the task, return empty: {\"companies\": []}",
        "",
        "Required JSON structure:",
        '{"companies": [{"name": "...", "website": "...", "why_fit": "..."}]}',
        "",
        "Use ExaTools to search for companies matching the targeting criteria.",
        "Each company must have: name, website, why_fit (1-2 lines).",
        "Prioritize companies that are most likely to benefit from the offering.",
    ]
    
    agent_openai = None
    agent_gemini = None
    
    if has_openai:
        agent_openai = Agent(
            model=OpenAIChat(id=openai_model),
            tools=[exa_tools],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_company_openai",
            instructions=instructions,
            markdown=False,  # ✅ CRITICAL: Disable markdown
        )
    
    if has_gemini:
        agent_gemini = Agent(
            model=Gemini(id=gemini_model),
            tools=[exa_tools],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_company_gemini",
            instructions=instructions,
            markdown=False,  # ✅ CRITICAL: Disable markdown
        )
    
    return agent_openai, agent_gemini



def create_contact_finder_agents(
    has_openai: bool,
    has_gemini: bool,
    openai_model: str,
    gemini_model: str
) -> Tuple[Optional[Agent], Optional[Agent]]:
    """
    Create ContactFinder agents
    """
    exa_tools = ExaTools()
    db = SqliteDb(db_file="/tmp/gtm_outreach.db")
    
    instructions = (
        "You are ContactFinderAgent. Find 2-3 decision makers per company with emails.\n"
        "Prioritize: Founders, GTM/Marketing/Growth, Sales, Partnerships, Product Marketing.\n"
        "If emails not found, infer using common formats and mark 'inferred': true.\n"
        "Return ONLY valid JSON: {companies: [{name, contacts: [{full_name, title, email, inferred}]}]}"
    )
    
    agent_openai = None
    agent_gemini = None
    
    if has_openai:
        agent_openai = Agent(
            model=OpenAIChat(id=openai_model),
            tools=[exa_tools],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_contact_openai",
            instructions=instructions,
        )
    
    if has_gemini:
        agent_gemini = Agent(
            model=Gemini(id=gemini_model),
            tools=[exa_tools],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_contact_gemini",
            instructions=instructions,
        )
    
    return agent_openai, agent_gemini


def create_email_writer_agents(
    has_openai: bool,
    has_gemini: bool,
    openai_model: str,
    gemini_model: str,
    style_key: str = "Professional"
) -> Tuple[Optional[Agent], Optional[Agent]]:
    """
    Create EmailWriter agents
    """
    db = SqliteDb(db_file="/tmp/gtm_outreach.db")
    
    style = get_email_style_instruction(style_key)
    
    instructions = (
        "You are EmailWriterAgent. Write concise, personalized B2B outreach emails.\n"
        f"Style: {style}\n"
        "Length: 120-180 words. Include 2-3 lines of personalization using research insights.\n"
        "Structure: Hook → Value Prop → Personalization → CTA\n"
        "CTA: Suggest a short intro call with calendar link if provided.\n"
        "Return ONLY valid JSON: {emails: [{company, contact, subject, body}]}"
    )
    
    agent_openai = None
    agent_gemini = None
    
    if has_openai:
        agent_openai = Agent(
            model=OpenAIChat(id=openai_model),
            tools=[],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_email_openai",
            instructions=instructions,
        )
    
    if has_gemini:
        agent_gemini = Agent(
            model=Gemini(id=gemini_model),
            tools=[],
            db=db,
            enable_user_memories=True,
            add_history_to_context=True,
            num_history_runs=6,
            session_id="gtm_email_gemini",
            instructions=instructions,
        )
    
    return agent_openai, agent_gemini


def get_email_style_instruction(style_key: str) -> str:
    """Get email style instructions"""
    styles = {
        "Professional": "Professional, clear, respectful tone. Short paragraphs, no slang.",
        "Casual": "Friendly, approachable, first-name basis. Conversational but professional.",
        "Cold": "Strong hook in first 2 lines, tight value prop, clear CTA. No fluff.",
        "Consultative": "Insight-led, frame observed problems, tailored solutions, soft CTA.",
        "Executive": "Brief, strategic, focused on business outcomes. High-level value prop.",
    }
    return styles.get(style_key, styles["Professional"])