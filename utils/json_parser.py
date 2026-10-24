import json
import re
from typing import Dict, Any


def remove_emojis(text: str) -> str:
    """Remove emojis and special unicode characters"""
    # Emoji pattern (covers most emojis)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)


def extract_json_or_raise(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response with emoji removal and repair
    """
    # STEP 1: Remove emojis FIRST
    text = remove_emojis(text)
    
    # STEP 2: Direct parse attempt
    try:
        return json.loads(text)
    except:
        pass
    
    # STEP 3: Find JSON object with regex
    try:
        pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            for match in sorted(matches, key=len, reverse=True):
                try:
                    return json.loads(match)
                except:
                    continue
    except:
        pass
    
    # STEP 4: Extract from code blocks
    try:
        if "```json" in text:
            # Fixed: split on closing backticks, not empty string
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in text:
            parts = text.split("```")
            for i in range(1, len(parts), 2):
                try:
                    # Strip language identifier if present (e.g., "json\n")
                    content = parts[i].strip()
                    # Remove language identifier from first line if present
                    if '\n' in content:
                        first_line = content.split('\n')[0].strip()
                        if first_line.isalpha() and len(first_line) < 20:
                            content = '\n'.join(content.split('\n')[1:])
                    return json.loads(content)
                except:
                    continue
    except:
        pass
    
    # STEP 5: Truncation repair (MOST IMPORTANT FOR YOUR ISSUE)
    try:
        # Find last valid closing brace
        last_brace = text.rfind("}")
        if last_brace != -1:
            truncated = text[:last_brace + 1]
            return json.loads(truncated)
    except:
        pass
    
    # STEP 6: Aggressive repair - find first { to last }
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            return json.loads(candidate)
    except:
        pass
    
    # STEP 7: Try fixing common issues
    try:
        cleaned = text.strip()
        
        # Remove common prefixes
        prefixes = ["Here is the JSON:", "Here's the JSON:", "JSON:", "Result:", "Output:"]
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove trailing commas before } or ]
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return json.loads(cleaned)
    except:
        pass
    
    # All strategies failed
    raise ValueError(
        f"Failed to parse JSON after all repair attempts.\n"
        f"Response preview (first 500 chars):\n{text[:500]}\n\n"
        f"Response length: {len(text)} characters"
    )


def safe_extract_json(text: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract JSON with fallback to default"""
    try:
        return extract_json_or_raise(text)
    except Exception as e:
        print(f"JSON extraction failed: {e}")
        return default or {}