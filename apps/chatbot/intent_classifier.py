"""
apps/chatbot/intent_classifier.py

Two-stage intent classification:
  Stage 1 — Rule-based regex tree   (fast, deterministic, high precision)
  Stage 2 — LLM fallback            (for ambiguous / novel inputs)

Intent taxonomy (banking/insurance domain):
    ACCOUNT         check_balance, get_statement, update_profile
    CLAIM           check_claim_status, file_claim, claim_documents
    POLICY          check_policy, renew_policy, policy_coverage
    PAYMENT         make_payment, payment_history, emi_details
    PAYOUT          check_payout, payout_timeline
    LOAN            loan_enquiry, loan_status, loan_emi
    SUPPORT         report_problem, escalate_agent, track_ticket
    GENERAL         greet, farewell, get_help, thanks, chitchat
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    intent:     str
    confidence: float
    lang_hint:  str       = 'en'
    slots:      dict      = field(default_factory=dict)
    via_llm:    bool      = False
    raw_text:   str       = ''


# ─── Rule Tree ────────────────────────────────────────────────────────────────
# Each entry: (intent_name, [regex_patterns...], base_confidence)
# Patterns cover English, Hindi Devanagari, and Hinglish (Roman Hindi).

RULE_TREE = [

    # ── Greetings ──────────────────────────────────────────────────────────
    ('greet', [
        r'\b(hi+|hello+|hey+|howdy|good\s*(morning|afternoon|evening|day))\b',
        r'(नमस्ते|नमस्कार|हेलो|हाय|सुप्रभात)',
        r'\b(namaste|namaskar|helo|haay|jai\s*hind|ram\s*ram)\b',
    ], 0.92),

    # ── Farewell / Thanks ──────────────────────────────────────────────────
    ('farewell', [
        r'\b(bye|goodbye|see\s*ya|ciao|take\s*care|good\s*night|gn)\b',
        r'(अलविदा|बाय|शुभ\s*रात्रि)',
        r'\b(alvida|bye\s*bye|tata|ok\s*bye|chalo\s*bye)\b',
    ], 0.90),

    ('thanks', [
        r'\b(thank\s*you|thanks|thx|ty|much\s*appreciated|great|perfect|awesome)\b',
        r'(धन्यवाद|शुक्रिया|बहुत\s*अच्छा|थैंक्स)',
        r'\b(dhanyawad|shukriya|bahut\s*accha|shukriya\s*bhai)\b',
    ], 0.90),

    # ── Balance ────────────────────────────────────────────────────────────
    ('check_balance', [
        r'\b(balance|account\s*balance|check\s*balance|current\s*balance|available\s*balance|how\s*much.*balance|wallet)\b',
        r'(बैलेंस|शेष\s*राशि|खाता\s*शेष|बचत|पैसे\s*कितने)',
        r'\b(balance\s*(batao|check|dekho|dikhao|bata|kya\s*hai)|mera\s*balance|bakaya|paisa\s*(kitna|batao|hai))\b',
    ], 0.96),

    # ── Statement ──────────────────────────────────────────────────────────
    ('get_statement', [
        r'\b(statement|account\s*statement|passbook|transaction\s*history|mini\s*statement|last\s*\d+\s*transactions?)\b',
        r'(स्टेटमेंट|पासबुक|लेनदेन|खाता\s*विवरण|ट्रांजेक्शन)',
        r'\b(statement\s*(chahiye|bhejo|do|send)|passbook|transaction\s*(dikhao|batao|history))\b',
    ], 0.91),

    # ── Claim ─────────────────────────────────────────────────────────────
    ('check_claim_status', [
        r'\b(claim\s*status|my\s*claim|claim\s*update|insurance\s*claim|claim\s*progress|claim\s*(approved|rejected|pending))\b',
        r'(क्लेम\s*स्थिति|दावे\s*की\s*स्थिति|क्लेम\s*अपडेट|मेरा\s*क्लेम)',
        r'\b(claim\s*(status|kab|kaise|kya\s*hua|update|batao|dekho|approved|mila)|mera\s*claim\s*(kya|kab))\b',
    ], 0.95),

    ('file_claim', [
        r'\b(file\s*claim|new\s*claim|submit\s*claim|raise\s*claim|make\s*a\s*claim|claim\s*karna)\b',
        r'(क्लेम\s*दर्ज|नया\s*दावा|क्लेम\s*करना)',
        r'\b(claim\s*(karna|file|submit|lagana|dalna)|naya\s*claim)\b',
    ], 0.93),

    # ── Policy ────────────────────────────────────────────────────────────
    ('check_policy', [
        r'\b(policy|my\s*policy|policy\s*details|insurance\s*policy|coverage|policy\s*number|plan\s*details)\b',
        r'(पॉलिसी|नीति|बीमा|कवरेज|प्लान)',
        r'\b(policy\s*(details|batao|dekho|kya\s*hai|number)|meri\s*policy|bima\s*(kya|batao))\b',
    ], 0.93),

    ('renew_policy', [
        r'\b(renew|renewal|extend\s*policy|policy\s*renew|policy\s*expire|policy\s*expiry)\b',
        r'(नवीनीकरण|पॉलिसी\s*रिन्यू|पॉलिसी\s*बढ़ाएं)',
        r'\b(policy\s*(renew|badha|extend)|renew\s*karna)\b',
    ], 0.91),

    # ── Payment ───────────────────────────────────────────────────────────
    ('make_payment', [
        r'\b(pay|payment|make\s*payment|pay\s*premium|pay\s*now|pay\s*emi|due\s*amount|pay\s*bill)\b',
        r'(भुगतान|प्रीमियम\s*भरें|ईएमआई\s*भरें|पेमेंट\s*करें)',
        r'\b(payment\s*(karna|kar|karo)|premium\s*(bharo|bharna|pay)|emi\s*(bhar|kab|pay))\b',
    ], 0.93),

    ('payment_history', [
        r'\b(payment\s*history|past\s*payments|previous\s*payment|paid\s*amount|payment\s*record)\b',
        r'(भुगतान\s*इतिहास|पुराने\s*भुगतान)',
        r'\b(payment\s*(history|record|purane)|purane\s*payment)\b',
    ], 0.89),

    # ── Payout ────────────────────────────────────────────────────────────
    ('check_payout', [
        r'\b(payout|disbursement|when.*paid|money\s*received|payment\s*received|payout\s*status)\b',
        r'(पेआउट|भुगतान\s*कब|पैसे\s*कब\s*मिलेंगे|राशि\s*कब)',
        r'\b(payout\s*(kab|status|batao|milega)|paisa\s*(kab|aayega|mila)|transfer\s*(kab|hua))\b',
    ], 0.93),

    # ── Loan ──────────────────────────────────────────────────────────────
    ('loan_enquiry', [
        r'\b(loan|borrow|lending|credit|personal\s*loan|business\s*loan|loan\s*eligib)\b',
        r'(लोन|ऋण|उधार|कर्ज|व्यक्तिगत\s*ऋण)',
        r'\b(loan\s*(chahiye|lena|batao|kaise|milega)|udhar\s*(chahiye|do|milega))\b',
    ], 0.91),

    ('loan_status', [
        r'\b(loan\s*status|my\s*loan|loan\s*balance|remaining\s*loan|loan\s*emi|outstanding\s*loan)\b',
        r'(लोन\s*स्थिति|मेरा\s*लोन|लोन\s*बकाया)',
        r'\b(mera\s*loan|loan\s*(status|kya\s*hua|batao|kitna\s*bacha))\b',
    ], 0.91),

    # ── Support / Escalation ──────────────────────────────────────────────
    ('report_problem', [
        r'\b(problem|issue|complaint|not\s*working|error|wrong|incorrect|bug|glitch|failed)\b',
        r'(समस्या|शिकायत|परेशानी|दिक्कत|गलती|त्रुटि)',
        r'\b(problem\s*(hai|hua|bata)|dikkat|pareshani|complaint\s*(karna|hai|dena))\b',
    ], 0.88),

    ('escalate_agent', [
        r'\b(human|agent|speak\s*to\s*someone|talk\s*to\s*person|customer\s*care|representative|live\s*agent|call\s*me)\b',
        r'(इंसान|एजेंट|कस्टमर\s*केयर|प्रतिनिधि)',
        r'\b(agent\s*(chahiye|se\s*baat)|human\s*(se\s*baat|chahiye)|customer\s*care)\b',
    ], 0.94),

    # ── Help / Menu ───────────────────────────────────────────────────────
    ('get_help', [
        r'\b(help|menu|options|what\s*can\s*you\s*do|services|start|commands|show\s*options)\b',
        r'(मदद|सहायता|विकल्प|मेनू|सेवाएं)',
        r'\b(help\s*(chahiye|karo)|madad|kya\s*kar\s*sakte|option\s*(batao|dikhao))\b',
    ], 0.85),
]


def classify_intent(text: str, lang_code: str = 'en') -> IntentResult:
    """
    Stage 1: Rule-based classification.
    Returns IntentResult(intent='unknown') if no rule matches.
    """
    if not text or not text.strip():
        return IntentResult(intent='get_help', confidence=0.5, lang_hint=lang_code)

    normalized = text.lower().strip()
    best: Optional[IntentResult] = None

    for intent_name, patterns, base_conf in RULE_TREE:
        for pattern in patterns:
            try:
                if re.search(pattern, normalized, re.UNICODE):
                    if best is None or base_conf > best.confidence:
                        best = IntentResult(
                            intent=intent_name,
                            confidence=base_conf,
                            lang_hint=lang_code,
                            raw_text=text,
                        )
                    break
            except re.error as e:
                logger.warning("Regex error in pattern %r: %s", pattern, e)

    return best or IntentResult(intent='unknown', confidence=0.0, lang_hint=lang_code, raw_text=text)
