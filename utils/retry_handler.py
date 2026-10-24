"""
Retry handler with exponential backoff for API calls
"""
import time
import streamlit as st
from typing import Callable, Any, Optional
from functools import wraps


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    stage_name: str = "Operation"
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        stage_name: Name of stage for logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Show retry status
                    if attempt > 0:
                        st.warning(f"🔄 {stage_name} - Retry {attempt}/{max_retries-1}")
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Success
                    if attempt > 0:
                        st.success(f"✅ {stage_name} succeeded after {attempt} retries")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # Check if it's a rate limit error
                    is_rate_limit = any(x in error_msg.lower() for x in [
                        'rate limit', 'quota', '429', 'too many requests'
                    ])
                    
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        
                        # If rate limit, use suggested retry time if available
                        if is_rate_limit and 'retry in' in error_msg.lower():
                            import re
                            match = re.search(r'retry in (\d+)', error_msg.lower())
                            if match:
                                delay = float(match.group(1)) + 1  # Add 1 sec buffer
                        
                        st.warning(f"""
                        ⚠️ {stage_name} failed (attempt {attempt + 1}/{max_retries})
                        Error: {error_msg[:150]}
                        Waiting {delay:.0f}s before retry...
                        """)
                        
                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        st.error(f"❌ {stage_name} failed after {max_retries} attempts")
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def run_with_failsoft(
    func: Callable,
    fallback_value: Any,
    stage_name: str,
    *args,
    **kwargs
) -> tuple[Any, bool]:
    """
    Run function with fail-soft behavior
    
    Returns:
        (result, success_flag)
    """
    try:
        result = func(*args, **kwargs)
        return result, True
    except Exception as e:
        st.error(f"""
        ❌ {stage_name} failed: {str(e)[:200]}
        ✅ Continuing with fallback value
        """)
        return fallback_value, False
