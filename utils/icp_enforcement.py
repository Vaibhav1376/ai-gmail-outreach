"""
ICP ENFORCEMENT GATE - HARD FILTER
Prevents pipeline drift into wrong company types
"""
from typing import Dict, List, Tuple


def get_allowed_company_types(mode: str) -> List[str]:
    """
    Define allowed company types per mode
    """
    if mode == "FIND_MY_CLIENTS":
        # Finding agencies as YOUR clients
        return [
            "Marketing Agency",
            "Digital Agency",
            "Web Development Agency",
            "Growth Agency",
            "SEO Agency",
            "Content Marketing Agency",
            "Performance Marketing Agency",
            "Branding Agency",
            "Creative Agency",
            "Consulting Firm",
            "Fractional CMO Service",
            "Lead Generation Agency",
        ]
    
    elif mode == "FIND_CLIENTS_FOR_CUSTOMER":
        # Finding companies for your client
        # More flexible - defined by client's ICP
        return [
            "B2B SaaS",
            "Software Company",
            "Tech Company",
            "E-commerce",
            "Fintech",
            "Healthcare Tech",
            "EdTech",
            # Add more as needed
        ]
    
    return []


def enforce_icp_gate(
    company: Dict,
    mode: str,
    custom_icp_types: List[str] = None
) -> Tuple[bool, str]:
    """
    HARD ICP GATE - Reject companies that don't match
    
    Returns: (should_accept, rejection_reason)
    """
    company_type = company.get('company_type', '').strip()
    company_name = company.get('name', '')
    website = company.get('website', '').lower()
    
    # Get allowed types for this mode
    if custom_icp_types:
        allowed_types = custom_icp_types
    else:
        allowed_types = get_allowed_company_types(mode)
    
    # ========================================================================
    # MODE: FIND_MY_CLIENTS (Agency-finding mode)
    # ========================================================================
    
    if mode == "FIND_MY_CLIENTS":
        
        # HARD REJECT: B2B SaaS / Product Companies
        product_keywords = [
            'saas', 'software', 'platform', 'tool', 'app',
            'product', 'api', 'infrastructure', 'cloud'
        ]
        
        if any(kw in company_type.lower() for kw in product_keywords):
            return False, f"REJECT: {company_type} is a product company, not a service provider"
        
        if any(kw in company_name.lower() or kw in website for kw in ['saas', 'software', 'app']):
            return False, f"REJECT: {company_name} appears to be a product company (website/name contains product keywords)"
        
        # HARD REJECT: Does not sell services
        service_indicators = ['agency', 'consulting', 'services', 'marketing', 'growth', 'digital']
        has_service_indicator = any(
            kw in company_type.lower() or kw in company_name.lower() or kw in website
            for kw in service_indicators
        )
        
        if not has_service_indicator:
            return False, f"REJECT: {company_name} does not appear to sell services"
        
        # CHECK: Must be in allowed agency types
        is_allowed_type = any(allowed in company_type for allowed in allowed_types)
        
        if not is_allowed_type:
            return False, f"REJECT: {company_type} not in allowed agency types. Allowed: {', '.join(allowed_types[:3])}..."
        
        # PASS
        return True, "PASS: Valid agency/service provider"
    
    # ========================================================================
    # MODE: FIND_CLIENTS_FOR_CUSTOMER
    # ========================================================================
    
    elif mode == "FIND_CLIENTS_FOR_CUSTOMER":
        
        # More flexible - use client's ICP definition
        if allowed_types:
            is_allowed = any(
                allowed.lower() in company_type.lower()
                for allowed in allowed_types
            )
            
            if not is_allowed:
                return False, f"REJECT: {company_type} not in client's ICP types"
        
        # PASS
        return True, "PASS: Matches client ICP"
    
    # Default reject
    return False, "REJECT: Unknown mode or no ICP match"


def apply_icp_gate_to_companies(
    companies: List[Dict],
    mode: str,
    custom_icp_types: List[str] = None
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Apply ICP gate to all companies
    Returns: (accepted, rejected, stats)
    """
    accepted = []
    rejected = []
    
    for company in companies:
        should_accept, reason = enforce_icp_gate(company, mode, custom_icp_types)
        
        company['icp_gate_result'] = reason
        
        if should_accept:
            accepted.append(company)
        else:
            rejected.append(company)
    
    stats = {
        'total': len(companies),
        'accepted': len(accepted),
        'rejected': len(rejected),
        'rejection_rate': (len(rejected) / len(companies) * 100) if companies else 0
    }
    
    return accepted, rejected, stats
