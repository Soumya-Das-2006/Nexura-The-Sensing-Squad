"""
apps/chatbot/language_detector.py

Lightweight multilingual language detector — no external API.
Uses Unicode script ranges + curated Hinglish keyword bank.

Supported:
    en    → English
    hi    → Hindi (Devanagari script)
    hi_en → Hinglish (Roman-script Hindi)
    gu    → Gujarati
"""

import re
import unicodedata
from typing import Tuple


def _script_ratios(text: str) -> dict:
    total = devanagari = gujarati = latin = 0
    for ch in text:
        if unicodedata.category(ch).startswith('L'):
            total += 1
            cp = ord(ch)
            if 0x0900 <= cp <= 0x097F:
                devanagari += 1
            elif 0x0A80 <= cp <= 0x0AFF:
                gujarati += 1
            elif ch.isascii():
                latin += 1
    if total == 0:
        return {'devanagari': 0.0, 'gujarati': 0.0, 'latin': 0.0}
    return {
        'devanagari': devanagari / total,
        'gujarati':   gujarati   / total,
        'latin':      latin      / total,
    }


HINGLISH_EXCLUSIVE = {
    'batao','bata','bataiye','dikhao','dikha','chahiye','chahie',
    'mera','meri','mujhe','hamara','tumhara','apna','apni',
    'karo','karna','kare','kar','kab','kaise','kitna','kitni',
    'milega','milegi','dena','dedo','aayega','hua','hai',
    'nahi','haan','theek','sahi','accha','acha',
    'namaste','namaskar','dhanyawad','shukriya',
    'paisa','paise','rupiya','rupiye','bakaya','khata',
    'madad','pareshani','dikkat','samasya',
    'dekho','dekhe','bhejo','bhej','lena','lelo',
}

HINGLISH_SHARED = {
    'balance','claim','policy','payment','transfer','loan',
    'account','help','status','check','pending','approved',
}


def detect_language(text: str) -> Tuple[str, float]:
    """
    Returns (lang_code, confidence) where lang_code in {'en','hi','hi_en','gu'}.
    """
    if not text or not text.strip():
        return ('en', 1.0)

    ratios = _script_ratios(text)

    if ratios['devanagari'] > 0.40:
        return ('hi', min(0.97, 0.65 + ratios['devanagari']))
    if ratios['gujarati'] > 0.40:
        return ('gu', min(0.97, 0.65 + ratios['gujarati']))
    if ratios['devanagari'] > 0.10 and ratios['latin'] > 0.10:
        return ('hi', 0.78)

    tokens = set(re.split(r'[\s,.!?;:]+', text.lower()))
    exclusive_hits = tokens & HINGLISH_EXCLUSIVE
    shared_hits    = tokens & HINGLISH_SHARED

    if exclusive_hits:
        conf = min(0.92, 0.55 + len(exclusive_hits) * 0.12)
        return ('hi_en', conf)
    if len(shared_hits) >= 2:
        return ('hi_en', 0.60)

    return ('en', 0.82)


def normalize_lang(lang_code: str) -> str:
    """Map detected code → canonical response language."""
    return {'hi': 'hi', 'hi_en': 'hi', 'gu': 'gu', 'en': 'en'}.get(lang_code, 'en')
