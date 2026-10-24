"""
Validation pipeline to filter and score results
"""
import streamlit as st
from typing import List, Dict, Any, Tuple
from utils.business_rules import (
    is_valid_company,
    score_company_signals,
    MIN_SIGNAL_SCORE,
    validate_inference,
    find_problem_owner,
    calculate_contact_confidence,
    MIN_CONTACT_CONFIDENCE,
    validate_email_structure,
    calculate_final_confidence
)


def validate_companies(companies: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Validate companies against business rules
    Returns: (valid_companies, rejected_companies)
    """
    valid = []
    rejected = []
    
    for company in companies:
        # 1. Company eligibility check
        is_eligible, reason = is_valid_company(company)
        if not is_eligible:
            company['rejection_reason'] = f"Eligibility: {reason}"
            rejected.append(company)
            continue
        
        # 2. Signal score check
        signal_score, tiers = score_company_signals(company)
        company['signal_score'] = signal_score
        company['signal_tiers'] = tiers
        
        if signal_score < MIN_SIGNAL_SCORE:
            company['rejection_reason'] = f"Signal score too low: {signal_score} < {MIN_SIGNAL_SCORE}"
            rejected.append(company)
            continue
        
        # 3. Inference validation
        inference_valid, issues = validate_inference(company)
        if not inference_valid:
            company['rejection_reason'] = f"Inference issues: {', '.join(issues)}"
            rejected.append(company)
            continue
        
        # All checks passed
        valid.append(company)
    
    return valid, rejected


def validate_contacts(contacts_data: List[Dict], companies: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Validate contacts and calculate confidence scores
    Returns: (valid_contacts, stats)
    """
    valid_contacts = []
    stats = {
        'total_contacts': 0,
        'valid_contacts': 0,
        'low_confidence': 0,
        'high_confidence': 0
    }
    
    # Build company lookup
    company_map = {c['name']: c for c in companies}
    
    for company_contacts in contacts_data:
        company_name = company_contacts.get('name')
        company = company_map.get(company_name, {})
        problem_type = company_contacts.get('problem_type', 'other')
        
        validated_contacts = []
        
        for contact in company_contacts.get('contacts', []):
            stats['total_contacts'] += 1
            
            # Calculate confidence
            confidence, reasons = calculate_contact_confidence(contact, company)
            contact['confidence'] = confidence
            contact['confidence_reasons'] = reasons
            
            # Filter low confidence
            if confidence < MIN_CONTACT_CONFIDENCE:
                stats['low_confidence'] += 1
                continue
            
            # Check problem owner match
            is_owner = contact.get('is_problem_owner', False)
            if is_owner:
                stats['high_confidence'] += 1
            
            validated_contacts.append(contact)
            stats['valid_contacts'] += 1
        
        if validated_contacts:
            company_contacts['contacts'] = validated_contacts
            valid_contacts.append(company_contacts)
    
    return valid_contacts, stats


def validate_and_score_leads(results: Dict) -> Dict:
    """
    Complete validation and scoring pipeline
    """
    st.info("🔍 Running validation pipeline...")
    
    # Stage 1: Validate companies
    companies = results.get('companies', [])
    valid_companies, rejected_companies = validate_companies(companies)
    
    if rejected_companies:
        st.warning(f"⚠️ Filtered out {len(rejected_companies)} companies")
        with st.expander("🚫 Rejected Companies (Click to see why)"):
            for comp in rejected_companies:
                st.write(f"**{comp.get('name')}**: {comp.get('rejection_reason')}")
    
    # Stage 2: Validate contacts
    contacts_data = results.get('contacts', [])
    valid_contacts, contact_stats = validate_contacts(contacts_data, valid_companies)
    
    st.info(f"✅ {contact_stats['valid_contacts']}/{contact_stats['total_contacts']} contacts passed validation")
    
    # Stage 3: Calculate final scores for emails
    emails = results.get('emails', [])
    scored_emails = []
    
    for email in emails:
        # Find matching company and contact
        company_name = email.get('company_name')
        contact_name = email.get('contact_name')
        
        company = next((c for c in valid_companies if c['name'] == company_name), None)
        if not company:
            continue
        
        # Calculate final confidence
        signal_score = company.get('signal_score', 0)
        contact_confidence = email.get('contact_confidence', 50)
        role_match = email.get('is_problem_owner', False)
        
        final_confidence, explanation = calculate_final_confidence(
            company, 
            email,
            signal_score,
            contact_confidence,
            role_match
        )
        
        email['final_confidence'] = final_confidence
        email['confidence_explanation'] = explanation
        
        # Validate email structure
        email_body = email.get('body', '')
        is_valid_email, email_issues = validate_email_structure(email_body)
        email['email_validation'] = {
            'is_valid': is_valid_email,
            'issues': email_issues
        }
        
        scored_emails.append(email)
    
    # Update results
    results['companies'] = valid_companies
    results['contacts'] = valid_contacts
    results['emails'] = scored_emails
    results['validation_stats'] = {
        'companies_rejected': len(rejected_companies),
        'companies_valid': len(valid_companies),
        'contacts_stats': contact_stats
    }
    
    return results
