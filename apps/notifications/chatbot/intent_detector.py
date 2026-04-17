"""
apps/notifications/chatbot/intent_detector.py

Rule-based intent detection with multilingual keyword sets.
No ML model needed — pure regex/keyword matching tuned for banking/insurance.

Supported intents (banking/insurance context):
    check_balance       — balance enquiry
    check_claim_status  — claim status query
    check_policy        — policy details
    check_payout        — payout / disbursement status
    make_payment        — payment request / EMI
    get_statement       — account statement
    report_problem      — complaint / issue
    get_help            — generic help / menu
    greet               — hello / namaste
    farewell            — bye / thank you
    unknown             — fallback

Approach:
    Each intent has keyword sets for: en, hi (Devanagari), hi_en (Hinglish).
    Text is lowercased and matched using regex word-boundaries.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Intent:
    name: str
    confidence: float
    lang_hint: Optional[str] = None      # language detected from matched pattern
    slots: dict = field(default_factory=dict)


# ─── Intent Definitions ────────────────────────────────────────────────────────
# Each entry: (intent_name, list_of_regex_patterns, weight)
# Patterns are checked in order; first match wins within each intent.
# Weights allow scoring when multiple intents partially match.

INTENT_PATTERNS = [

    ('greet', [
        r'\b(hi|hello|hey|good\s*(morning|afternoon|evening))\b',          # en
        r'(नमस्ते|नमस्कार|हेलो|हाय)',                                      # hi
        r'\b(namaste|namaskar|namaskar|helo|haay|jai\s*hind)\b',           # hi_en
    ], 0.9),

    ('farewell', [
        r'\b(bye|goodbye|see\s*you|thank\s*you|thanks|thx)\b',             # en
        r'(धन्यवाद|अलविदा|शुक्रिया|थैंक्स)',                              # hi
        r'\b(dhanyawad|shukriya|alvida|bye\s*bye|tata)\b',                  # hi_en
    ], 0.85),

    ('check_balance', [
        r'\b(balance|account\s*balance|check\s*balance|how\s*much.*balance)\b',
        r'(बैलेंस|बैलन्स|शेष\s*राशि|खाता\s*शेष|कितना\s*पैसा)',
        r'\b(balance\s*(batao|bata|check|dekho|dikhao)|mera\s*balance|bakaya|paisa\s*(kitna|batao))\b',
    ], 0.95),

    ('check_claim_status', [
        r'\b(claim|my\s*claim|claim\s*status|claim\s*update|insurance\s*claim)\b',
        r'(क्लेम|दावा|बीमा\s*दावा|दावे\s*की\s*स्थिति)',
        r'\b(claim\s*(status|kab|kaise|kya\s*hua|update|batao|dekho)|mera\s*claim)\b',
    ], 0.95),

    ('check_policy', [
        r'\b(policy|my\s*policy|policy\s*details|insurance\s*policy|coverage)\b',
        r'(पॉलिसी|नीति|बीमा|कवरेज)',
        r'\b(policy\s*(details|batao|dekho|kya\s*hai)|meri\s*policy|bima)\b',
    ], 0.90),

    ('check_payout', [
        r'\b(payout|disbursement|payment\s*received|money\s*received|when.*paid)\b',
        r'(भुगतान|पेआउट|राशि\s*कब|पैसे\s*कब\s*मिलेंगे)',
        r'\b(payout\s*(kab|status|batao|milega)|paisa\s*(kab|aayega)|transfer\s*(kab|hua))\b',
    ], 0.90),

    ('make_payment', [
        r'\b(pay|payment|make\s*payment|emi|pay\s*premium|pay\s*now)\b',
        r'(भुगतान\s*करें|प्रीमियम\s*भरें|ईएमआई|पेमेंट)',
        r'\b(payment\s*(karna|kar|karo)|premium\s*(bharo|bharna|pay)|emi\s*(kab|bhar))\b',
    ], 0.90),

    ('get_statement', [
        r'\b(statement|account\s*statement|passbook|transaction\s*history|mini\s*statement)\b',
        r'(स्टेटमेंट|पासबुक|लेनदेन|खाता\s*विवरण)',
        r'\b(statement\s*(chahiye|bhejo|send)|passbook|transactions\s*(dikhao|batao))\b',
    ], 0.88),

    ('report_problem', [
        r'\b(problem|issue|complaint|not\s*working|error|wrong|help\s*me|stuck)\b',
        r'(समस्या|शिकायत|परेशानी|दिक्कत|गलती)',
        r'\b(problem\s*(hai|hua|bata)|dikkat|pareshani|complaint\s*(karna|hai))\b',
    ], 0.85),

    ('get_help', [
        r'\b(help|menu|options|what\s*can\s*you\s*do|services|start)\b',
        r'(मदद|सहायता|विकल्प|मेनू|सेवाएं)',
        r'\b(help\s*(chahiye|karo)|madad|kya\s*kar\s*sakte\s*ho|option\s*(batao|dikhao))\b',
    ], 0.80),
]


def detect_intent(text: str, lang_code: str = 'en') -> Intent:
    """
    Detect intent from user message.

    Parameters
    ----------
    text      : Original message text (any script)
    lang_code : Language code from language_detector (for logging/context)

    Returns
    -------
    Intent dataclass with name and confidence
    """
    if not text or not text.strip():
        return Intent(name='unknown', confidence=0.0)

    normalized = text.lower().strip()
    best_intent = None
    best_score = 0.0

    for intent_name, patterns, base_weight in INTENT_PATTERNS:
        for pattern in patterns:
            try:
                if re.search(pattern, normalized):
                    score = base_weight
                    if score > best_score:
                        best_score = score
                        best_intent = intent_name
                    break  # matched this intent — no need to check more patterns
            except re.error:
                continue

    if best_intent:
        return Intent(name=best_intent, confidence=best_score, lang_hint=lang_code)

    return Intent(name='unknown', confidence=0.0, lang_hint=lang_code)
