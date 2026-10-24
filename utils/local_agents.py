"""
Local Ollama agents for cost-free operations
Used in hybrid pipeline for cleaning and validation
"""
import subprocess
import time
from typing import Optional
from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.db.sqlite import SqliteDb


# ============================================================================
# OLLAMA AVAILABILITY CHECK
# ============================================================================

def check_local_available() -> bool:
    """
    Check if Ollama is installed and running
    
    Returns:
        True if Ollama is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_local_data_cleaner(model_id: str = "llama3.2:3b") -> Agent:
    """
    FREE agent for data cleaning and filtering
    
    Args:
        model_id: Ollama model to use (default: llama3.2:3b - fast and small)
    
    Returns:
        Agent configured for data cleaning
    """
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    
    instructions = [
        "You are DataCleanerAgent - efficient data processor.",
        "",
        "HARD FILTERS (AUTO-REJECT):",
        "❌ VC firms, investment funds, capital firms",
        "❌ Agencies (marketing, consulting, etc.)",
        "❌ Blogs, media companies, publications",
        "❌ Communities, newsletters, networks",
        "❌ Universities, schools, nonprofits",
        "❌ Non-B2B companies (consumer, B2C)",
        "",
        "TASKS:",
        "1. Remove rejected company types",
        "2. Normalize company names (trim, capitalize properly)",
        "3. Validate URLs (must be valid domains)",
        "4. Remove exact duplicates (by website or name)",
        "5. Clean special characters and emojis",
        "6. Ensure all required fields present (name, website, signal)",
        "",
        "VALIDATION RULES:",
        "✅ Must have valid website (real domain)",
        "✅ Must have signal (not empty)",
        "✅ Must be B2B SaaS or software company",
        "",
        "OUTPUT RULES:",
        "✅ Return ONLY valid JSON",
        "✅ Only include B2B SaaS companies",
        "❌ NO explanations or commentary",
        "❌ NO markdown code blocks",
        "",
        '{"companies": [...]} ← Exact format',
    ]
    
    return Agent(
        model=Ollama(id=model_id),
        tools=[],
        db=db,
        instructions=instructions,
        markdown=False  # ✅ Important: No markdown formatting
    )


def create_local_json_validator(model_id: str = "qwen2.5:7b") -> Agent:
    """
    FREE agent for JSON validation and repair
    
    Args:
        model_id: Ollama model to use (default: qwen2.5:7b - best for JSON)
    
    Returns:
        Agent configured for JSON validation
    """
    db = SqliteDb(db_file="tmp/gtm_outreach.db")
    
    instructions = [
        "You are JSONValidatorAgent - validates and fixes JSON.",
        "",
        "TASKS:",
        "1. Validate JSON structure",
        "2. Fix common errors:",
        "   - Trailing commas",
        "   - Missing closing brackets",
        "   - Unclosed strings",
        "   - Invalid escape characters",
        "   - Malformed arrays/objects",
        "3. Ensure all required fields present",
        "4. Remove emojis and special unicode",
        "5. Validate email addresses (must contain @)",
        "6. Ensure all arrays have correct length",
        "",
        "OUTPUT RULES:",
        "✅ Return ONLY fixed, valid JSON",
        "✅ Complete all arrays and objects",
        "✅ Preserve all data (don't remove fields)",
        "❌ NO explanations",
        "❌ NO markdown code blocks",
        "",
        "If JSON is valid, return it unchanged.",
        "If JSON is broken, fix and return corrected version.",
    ]
    
    return Agent(
        model=Ollama(id=model_id),
        tools=[],
        db=db,
        instructions=instructions,
        markdown=False  # ✅ Important: No markdown formatting
    )


def create_local_validator(model_id: str = "qwen2.5:7b") -> Agent:
    """
    Alias for create_local_json_validator (backward compatibility)
    """
    return create_local_json_validator(model_id)


# ============================================================================
# AGENT EXECUTION
# ============================================================================

def run_local_agent(agent: Agent, prompt: str, max_retries: int = 2) -> str:
    """
    Run local agent with simple retry
    Local is fast, so we can retry quickly
    
    Args:
        agent: The local agent to run
        prompt: The prompt/task to send
        max_retries: Number of retry attempts (default: 2)
    
    Returns:
        Agent response as string
    
    Raises:
        Exception: If all retry attempts fail
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = agent.run(prompt)
            content = str(resp.content)
            
            # Clean response (remove markdown if present)
            # FIX: SyntaxError in original code (missing quotes/colon)
            if content.startswith('```'):
                # Extract JSON from markdown code block
                lines = content.split('\n')
                # Assumes ``` is on the first and last lines
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
            
            return content
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(1)  # Quick retry for local models
                continue
    
    raise Exception(f"Local agent failed after {max_retries} attempts: {str(last_error)}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_installed_models() -> list:
    """
    Get list of installed Ollama models
    
    Returns:
        List of model names (e.g., ['llama3.2:3b', 'qwen2.5:7b'])
    """
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return []
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        models = []
        
        for line in lines[1:]:  # Skip header
            if line.strip():
                # FIX: Original code returned full line split list, causing
                # is_model_installed checks to fail. We need just the name (index 0).
                model_name = line.split()[0]
                models.append(model_name)
        
        return models
        
    except Exception:
        return []


def is_model_installed(model_name: str) -> bool:
    """
    Check if a specific model is installed
    
    Args:
        model_name: Model name (e.g., 'llama3.2:3b')
    
    Returns:
        True if model is installed, False otherwise
    """
    installed = get_installed_models()
    return model_name in installed


def install_model(model_name: str, timeout: int = 300) -> bool:
    """
    Install an Ollama model
    
    Args:
        model_name: Model to install (e.g., 'llama3.2:3b')
        timeout: Max wait time in seconds (default: 300 = 5 minutes)
    
    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            ['ollama', 'pull', model_name],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception:
        return False