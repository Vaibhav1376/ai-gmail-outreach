"""
Data schemas for GTM Outreach v2
All JSON contracts between agents
UPDATED: Delivery Standard enforced (Fix #8)
"""

from typing import TypedDict, List
from dataclasses import dataclass, field
from typing import List, Optional

# ==========================================================
# Core Entities (UNCHANGED)
# ==========================================================

class Company(TypedDict):
    name: str
    website: str
    why_fit: str
    signal: str                    # Buying signal (hiring, funding, etc.)
    inference: str                 # Why now?
    offer_alignment: str           # How offer matches signal

    # ---- Added (Fix #8, backward-compatible) ----
    company_type: str
    signal_interpretation: dict
    signal_tier: str
    signal_score: int
    quality_score: int


class Contact(TypedDict):
    full_name: str
    title: str
    email: str
    inferred: bool                 # Email inferred or verified
    is_problem_owner: bool         # Owns the problem we solve


class ContactsData(TypedDict):
    name: str                      # Company name
    problem_type: str              # support, growth, infra_cost, hiring, other
    contacts: List[Contact]

    # ---- Added (Fix #8) ----
    manual_lookup_required: bool


class ResearchData(TypedDict):
    name: str                      # Company name
    top_3_pain_hints: List[str]    # 3 pain signals
    growth_narrative: str          # How they talk about growth
    icp_language: List[str]        # Phrases they use for positioning
    public_priorities: List[str]   # What they care about
    positioning_note: str          # Anti-BS insight
    competitors: List[str]         # 2-3 competitors (optional)


class EmailDraft(TypedDict):
    company: str
    contact: str
    subject: str
    body: str
    linkedin_dm: str               # LinkedIn DM draft
    twitter_dm: str                # X/Twitter DM draft
    followup_angles: List[str]     # 3 follow-up angles
    breakup_email: str             # Final breakup email
    confidence: int                # 0-100
    confidence_reason: str         # Why this score


# ==========================================================
# FINAL LEAD SCHEMA (MERGED + FIX #8)
# ==========================================================

class Lead(TypedDict):
    # -------- Company --------
    company: str
    website: str
    company_type: str

    # -------- Signal (MANDATORY – Fix #8) --------
    signal: str
    signal_interpretation: str     # Human-readable interpretation
    signal_tier: str
    signal_score: int

    confidence_score: int = 0  # 0-100
    confidence_reason: str = ""
    rejection_risk: str = ""  # What could go wrong
    risk_factors: List[str] = field(default_factory=list)

    # -------- Contact --------
    contact: str
    role: str
    email: str
    problem_owner: bool
    manual_lookup_required: bool

    # -------- Outreach --------
    email_subject: str
    email_body: str
    linkedin_dm: str
    twitter_dm: str
    outreach_angle: str

    # -------- Follow-up --------
    followup_angle_1: str
    followup_angle_2: str
    followup_angle_3: str
    breakup_email: str

    # -------- Quality (MANDATORY – Fix #8) --------
    confidence: int
    confidence_reason: str
    quality_score: int

    confidence_score: int = 0  # 0-100
    confidence_reason: str = ""
    rejection_risk: str = ""  # What could go wrong
    risk_factors: List[str] = field(default_factory=list)

    # -------- Notes (MANDATORY – Fix #8) --------
    notes: str
    rejection_risk: str

def to_dict(self) -> dict:
        """Convert Lead to dictionary for export"""
        return {
            'company': self.company,
            'website': self.website,
            'company_type': self.company_type,
            'signal': self.signal,
            'signal_interpretation': self.signal_interpretation,
            'signal_tier': self.signal_tier,
            'signal_score': self.signal_score,
            'contact': self.contact,
            'role': self.role,
            'email': self.email,
            'problem_owner': self.problem_owner,
            'manual_lookup_required': self.manual_lookup_required,
            'email_subject': self.email_subject,
            'email_body': self.email_body,
            'linkedin_dm': self.linkedin_dm,
            'twitter_dm': self.twitter_dm,
            'outreach_angle': self.outreach_angle,
            'followup_angle_1': self.followup_angle_1,
            'followup_angle_2': self.followup_angle_2,
            'followup_angle_3': self.followup_angle_3,
            'breakup_email': self.breakup_email,
            'quality_score': self.quality_score,
            'notes': self.notes,
            'confidence_score': self.confidence_score,
            'confidence_reason': self.confidence_reason,
            'rejection_risk': self.rejection_risk,
            'risk_factors': '|'.join(self.risk_factors) if self.risk_factors else ''
        }