"""
apps/notifications/chatbot/language_detector.py

Lightweight multilingual language detector for Indian languages.
Works without any external API — uses Unicode script ranges + keyword sets.

Supported languages:
    hi  → Hindi (Devanagari script)
    gu  → Gujarati (Gujarati script)
    en  → English
    hi_en → Hinglish (Roman-script Hindi mixed with English)

Detection pipeline:
    1. Unicode script analysis  (Devanagari / Gujarati / Latin)
    2. Hinglish keyword match   (common Roman-Hindi banking phrases)
    3. English keyword match
    4. Fallback → 'en'
"""

import re
import unicodedata
from typing import Tuple


# ─── Unicode block ranges ──────────────────────────────────────────────────────
# Devanagari: U+0900–U+097F
# Gujarati:   U+0A80–U+0AFF

def _script_ratios(text: str) -> dict:
    """Return fraction of alphabetic chars in each script."""
    total = devanagari = gujarati = latin = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith('L'):          # Letter
            total += 1
            cp = ord(ch)
            if 0x0900 <= cp <= 0x097F:
                devanagari += 1
            elif 0x0A80 <= cp <= 0x0AFF:
                gujarati += 1
            elif ch.isascii():
                latin += 1
    if total == 0:
        return {'devanagari': 0, 'gujarati': 0, 'latin': 0}
    return {
        'devanagari': devanagari / total,
        'gujarati':   gujarati   / total,
        'latin':      latin      / total,
    }


# ─── Hinglish keyword bank ────────────────────────────────────────────────────
# Common Roman-script Hindi words used in banking/insurance conversations.
# Expanded to cover real-world chat patterns.

HINGLISH_KEYWORDS = {
    # Balance / Account
    'balance', 'bakaya', 'paisa', 'paise', 'khata', 'account', 'passbook',
    'batao', 'bata', 'dikhao', 'dikha', 'chahiye', 'chahie',
    'mera', 'meri', 'mujhe', 'hamara', 'hamari', 'apna', 'apni',
    'karo', 'karna', 'kare', 'kar',
    # Claim / Policy
    'claim', 'policy', 'bima', 'insurance', 'bharosa',
    'kab', 'kaise', 'kya', 'kab', 'kitna', 'kitni',
    'dena', 'dedo', 'do', 'milega', 'milegi', 'mila',
    # Payment / Payout
    'payment', 'payout', 'transfer', 'bhejo', 'bhej',
    'rupiya', 'rupiye', 'amount', 'paisa',
    # Loan
    'loan', 'udhar', 'EMI', 'kist', 'byaj', 'interest',
    # Help / Greetings
    'namaste', 'namaskar', 'help', 'madad', 'problem', 'issue',
    'theek', 'sahi', 'nahi', 'haan', 'naa', 'ha', 'na',
    'please', 'plz', 'ple', 'dhanyawad', 'shukriya',
    # Status
    'status', 'check', 'dekho', 'dekhe', 'dekh',
    'pending', 'approved', 'reject', 'rejected',
}

ENGLISH_BANKING_KEYWORDS = {
    'balance', 'account', 'loan', 'emi', 'payment', 'transfer',
    'claim', 'policy', 'insurance', 'payout', 'statement',
    'help', 'support', 'hello', 'hi', 'thanks', 'thank',
    'check', 'status', 'pending', 'approved',
}


def detect_language(text: str) -> Tuple[str, float]:
    """
    Detect language of incoming WhatsApp message.

    Returns
    -------
    (lang_code, confidence)
        lang_code   : 'hi' | 'gu' | 'hi_en' | 'en'
        confidence  : 0.0 – 1.0
    """
    if not text or not text.strip():
        return ('en', 1.0)

    clean = text.strip()
    ratios = _script_ratios(clean)

    # 1. Strong Devanagari signal → Hindi
    if ratios['devanagari'] > 0.40:
        return ('hi', min(0.95, 0.6 + ratios['devanagari']))

    # 2. Strong Gujarati signal → Gujarati
    if ratios['gujarati'] > 0.40:
        return ('gu', min(0.95, 0.6 + ratios['gujarati']))

    # 3. Mixed Devanagari + Latin → treat as Hindi (user mixing scripts)
    if ratios['devanagari'] > 0.10 and ratios['latin'] > 0.10:
        return ('hi', 0.75)

    # 4. Fully Latin text — check for Hinglish keywords
    tokens = set(re.split(r'[\s,.!?]+', clean.lower()))
    hinglish_hits = tokens & HINGLISH_KEYWORDS
    # Exclude pure-English words from the Hinglish set
    non_english_hits = hinglish_hits - ENGLISH_BANKING_KEYWORDS

    if non_english_hits:
        # Strong Hinglish signal
        confidence = min(0.90, 0.50 + len(non_english_hits) * 0.12)
        return ('hi_en', confidence)

    if hinglish_hits:
        # Weak Hinglish — could be English with Indian context
        confidence = min(0.75, 0.40 + len(hinglish_hits) * 0.08)
        return ('hi_en', confidence)

    # 5. Default → English
    return ('en', 0.80)


def normalize_lang(lang_code: str) -> str:
    """
    Map detected code to a canonical response language.
    Hinglish (hi_en) → respond in Hindi (hi).
    """
    mapping = {
        'hi':    'hi',
        'hi_en': 'hi',   # Hinglish → reply in Hindi
        'gu':    'gu',
        'en':    'en',
    }
    return mapping.get(lang_code, 'en')
