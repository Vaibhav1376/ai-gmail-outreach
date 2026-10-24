"""
Advanced JSON repair utilities for LLM outputs
"""
import json
import re
from typing import Dict, Any, Optional


def repair_truncated_json(text: str) -> Optional[str]:
    """
    Repair JSON that was truncated mid-response
    """
    # Strategy 1: Find last complete object
    last_brace = text.rfind("}")
    if last_brace != -1:
        candidate = text[:last_brace + 1]
        
        # Count braces to ensure balance
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")
        
        if open_braces == close_braces:
            return candidate
    
    # Strategy 2: Balance brackets by adding missing ones
    open_braces = text.count("{")
    close_braces = text.count("}")
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    
    repaired = text
    
    # Add missing closing brackets
    if close_brackets < open_brackets:
        repaired += "]" * (open_brackets - close_brackets)
    
    # Add missing closing braces
    if close_braces < open_braces:
        repaired += "}" * (open_braces - close_braces)
    
    return repaired


def fix_common_json_errors(text: str) -> str:
    """
    Fix common JSON syntax errors
    """
    # Remove trailing commas
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix unescaped quotes in strings (common error)
    # This is tricky, so we'll be conservative
    
    # Remove multiple consecutive commas
    text = re.sub(r',+', ',', text)
    
    # Remove commas before closing braces/brackets
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text


def extract_json_with_repair(text: str, max_attempts: int = 5) -> Dict[str, Any]:
    """
    Multi-strategy JSON extraction and repair
    """
    # Remove emojis first
    from utils.json_parser import remove_emojis
    text = remove_emojis(text)
    
    attempts = []
    
    # Attempt 1: Direct parse
    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError as e:
        attempts.append(f"Direct parse failed: {str(e)[:100]}")
    
    # Attempt 2: Truncation repair
    try:
        repaired = repair_truncated_json(text)
        if repaired:
            result = json.loads(repaired)
            print("✅ JSON repaired: Truncation fixed")
            return result
    except json.JSONDecodeError as e:
        attempts.append(f"Truncation repair failed: {str(e)[:100]}")
    
    # Attempt 3: Common error fixes
    try:
        fixed = fix_common_json_errors(text)
        result = json.loads(fixed)
        print("✅ JSON repaired: Common errors fixed")
        return result
    except json.JSONDecodeError as e:
        attempts.append(f"Error fix failed: {str(e)[:100]}")
    
    # Attempt 4: Extract first complete object
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            candidate = text[start:end + 1]
            result = json.loads(candidate)
            print("✅ JSON repaired: Extracted object")
            return result
    except json.JSONDecodeError as e:
        attempts.append(f"Object extraction failed: {str(e)[:100]}")
    
    # Attempt 5: Aggressive repair with balance
    try:
        aggressive = repair_truncated_json(text)
        if aggressive:
            fixed = fix_common_json_errors(aggressive)
            result = json.loads(fixed)
            print("✅ JSON repaired: Aggressive repair successful")
            return result
    except json.JSONDecodeError as e:
        attempts.append(f"Aggressive repair failed: {str(e)[:100]}")
    
    # All failed
    error_msg = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(attempts))
    raise ValueError(
        f"❌ JSON repair failed after {len(attempts)} attempts:\n{error_msg}\n\n"
        f"Original text (first 500 chars):\n{text[:500]}"
    )
