"""
Hybrid pipeline configuration
UPDATED: Mode-aware configuration
"""
from typing import Dict, Any, List


def get_pipeline_mode_config(mode: str) -> Dict[str, Any]:
    """
    Get configuration for specific pipeline mode
    
    Modes:
    - FIND_MY_CLIENTS: Finding agencies as YOUR clients
    - FIND_CLIENTS_FOR_CUSTOMER: Finding companies for client campaigns
    """
    
    if mode == "FIND_MY_CLIENTS":
        return {
            'mode': mode,
            'target_type': 'agencies',
            'max_companies': 5,  # Very low volume
            'target_rejection_rate': 70,  # Aggressive filtering
            'min_signal_score': 4,  # Higher bar
            
            # Agency-specific signals
            'priority_signals': [
                'referral_dependency',
                'lead_flow_pressure',
                'hiring_sales_team',
                'expanding_services',
                'losing_clients',
                'founder_overwhelmed'
            ],
            
            # Agency-specific decision makers
            'target_roles': [
                'Founder',
                'Owner',
                'Managing Partner',
                'CEO (small agency)'
            ],
            
            # Agency-specific pain points
            'pain_points': [
                'Inconsistent lead flow',
                'Too dependent on referrals',
                'Founder doing all sales',
                'Can\'t scale beyond current clients',
                'Low close rates'
            ]
        }
    
    elif mode == "FIND_CLIENTS_FOR_CUSTOMER":
        return {
            'mode': mode,
            'target_type': 'client_icp',
            'max_companies': 20,  # Client-defined
            'target_rejection_rate': 60,
            'min_signal_score': 3,
            
            # Standard B2B signals
            'priority_signals': [
                'hiring_expansion',
                'funding_rounds',
                'product_launches',
                'market_expansion',
                'rapid_growth'
            ],
            
            # Problem owner mapping
            'target_roles': [
                'problem_owner_dynamic'  # Varies by signal
            ],
            
            # Generic B2B pain points
            'pain_points': [
                'Scaling challenges',
                'Operational inefficiency',
                'Growth constraints'
            ]
        }
    
    # Default fallback
    return get_pipeline_mode_config("FIND_CLIENTS_FOR_CUSTOMER")


def get_hybrid_config() -> Dict[str, Any]:
    """
    Returns hybrid pipeline configuration
    UPDATED: Now mode-aware
    """
    return {
        # Local models (FREE)
        'local_cleaner': 'tinyllama:latest',
        'local_validator': 'qwen2.5:7b',
        
        # Cloud models (PAID)
        'cloud_discovery': 'gemini-2.5-flash',
        'cloud_inference': 'gemini-2.5-flash',
        'cloud_contacts': 'gemini-2.5-flash',
        'cloud_emails': 'gpt-4o-mini',
        
        # Timeouts & retries
        'local_timeout': 30,
        'cloud_timeout': 60,
        'max_retries': 1,  # UPDATED: Only retry once (Fix #7)
        
        # Rate limiting
        'delay_between_stages': 25,
        'delay_between_retries': 15,
        
        # Signal requirements (mode-specific now)
        'min_signal_score': 3,  # Overridden by mode config
        'require_hiring_signal': False,
        'require_funding_signal': False,
        
        # UPDATED: Fail-soft behavior (Fix #5)
        'fail_soft_on_contact_error': True,
        'fail_soft_on_cleaning_error': True,
    }


# Signal tier definitions remain the same
def get_signal_tiers() -> Dict[str, Any]:
    """
    Signal tier definitions for 100% signal-based filtering
    """
    return {
        'TIER_1': {
            'weight': 5,
            'signals': [
                'hiring_head_of_support',
                'hiring_customer_success',
                'support_job_spike_3plus',
                'recent_funding_with_hiring',
                'multiple_exec_hires',
                'rapid_headcount_growth',
                # Agency-specific (for FIND_MY_CLIENTS mode)
                'referral_dependency_mentioned',
                'lead_flow_complaints',
                'founder_doing_all_sales',
            ],
            'description': 'Operational Pain - Active Now'
        },
        'TIER_2': {
            'weight': 3,
            'signals': [
                'pricing_page_update',
                'product_launch_recent',
                'plg_strategy_shift',
                'rapid_feature_releases',
                'new_market_expansion',
                'api_documentation_overhaul',
                # Agency-specific
                'service_expansion',
                'team_growth',
            ],
            'description': 'Product/Market Changes - Near-term Pain'
        },
        'TIER_3': {
            'weight': 1,
            'signals': [
                'blog_post_about_scaling',
                'values_page_mentions_growth',
                'social_media_activity',
                'conference_sponsorship'
            ],
            'description': 'Soft Signals - AUTO REJECT'
        }
    }
