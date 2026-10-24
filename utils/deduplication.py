"""
Deduplication system to prevent duplicate companies
"""
import re
from typing import List, Dict, Set
from urllib.parse import urlparse

def normalize_domain(url: str) -> str:
    """Extract and normalize domain from URL"""
    try:
        parsed = urlparse(url if url.startswith('http') else f'https://{url}')
        domain = parsed.netloc or parsed.path
        domain = domain.replace('www.', '').lower().strip()
        return domain
    except:
        return url.lower().strip()

def normalize_company_name(name: str) -> str:
    """Normalize company name for matching"""
    name = name.lower().strip()
    # Remove common suffixes
    name = re.sub(r'\b(pvt|ltd|llc|inc|corp|limited|private)\b', '', name)
    # Remove special characters
    name = re.sub(r'[^\w\s]', '', name)
    # Remove extra spaces
    name = ' '.join(name.split())
    return name

def deduplicate_companies(
    companies: List[Dict],
    seen_log_path: str = "tmp/seen_companies.txt"
) -> tuple[List[Dict], List[Dict], Dict]:
    """
    Deduplicate companies by domain, name, and LinkedIn
    
    Returns:
        unique_companies, duplicates, stats
    """
    import os
    
    # Load seen companies log
    seen_domains: Set[str] = set()
    seen_names: Set[str] = set()
    
    if os.path.exists(seen_log_path):
        with open(seen_log_path, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 2:
                    seen_domains.add(parts[0])
                    seen_names.add(parts[1])
    
    unique = []
    duplicates = []
    current_run_domains = set()
    current_run_names = set()
    
    for company in companies:
        domain = normalize_domain(company.get('website', ''))
        name = normalize_company_name(company.get('name', ''))
        
        # Check for duplicates
        is_duplicate = False
        reason = []
        
        if domain in seen_domains or domain in current_run_domains:
            is_duplicate = True
            reason.append(f"Domain seen: {domain}")
        
        if name in seen_names or name in current_run_names:
            is_duplicate = True
            reason.append(f"Name seen: {name}")
        
        if is_duplicate:
            company['duplicate_reason'] = ' | '.join(reason)
            duplicates.append(company)
        else:
            unique.append(company)
            current_run_domains.add(domain)
            current_run_names.add(name)
    
    # Append to seen log
    os.makedirs(os.path.dirname(seen_log_path), exist_ok=True)
    with open(seen_log_path, 'a') as f:
        for company in unique:
            domain = normalize_domain(company.get('website', ''))
            name = normalize_company_name(company.get('name', ''))
            f.write(f"{domain}|{name}|{company.get('name', 'Unknown')}\n")
    
    stats = {
        'total_input': len(companies),
        'unique': len(unique),
        'duplicates': len(duplicates),
        'dedup_rate': f"{(len(duplicates) / len(companies) * 100):.1f}%" if companies else "0%"
    }
    
    return unique, duplicates, stats
