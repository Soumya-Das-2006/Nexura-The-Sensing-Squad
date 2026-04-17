"""
apps/chatbot/response_engine.py

Hybrid response engine:
  1. Rule-based templates  — fast, deterministic, always-on
  2. LLM enrichment        — activated for complex/ambiguous queries
  3. DB context injection  — real user data from Nexura DB

Decision logic:
    intent.confidence >= 0.88 AND intent not 'unknown'
        → rule-based template (instant)
    intent.confidence < 0.88 OR intent == 'unknown'
        → LLM with conversation history + system context
    LLM unavailable
        → graceful rule-based fallback
"""

import logging
from typing import Optional
from django.utils import timezone

from .llm_provider import get_llm_response, is_llm_configured
from .intent_classifier import IntentResult

logger = logging.getLogger(__name__)

# Threshold: above this → use rules, below → use LLM
RULE_CONFIDENCE_THRESHOLD = 0.88


# ─── Multilingual Response Templates ──────────────────────────────────────────

TEMPLATES: dict[str, dict[str, str]] = {

    "greet": {
        "en": (
            "👋 Hi {name}! Welcome to *Nexura Support*.\n\n"
            "I can help you with:\n"
            "• 💰 Balance & Statement\n"
            "• 📋 Claims & Policy\n"
            "• 💸 Payments & Payouts\n"
            "• 🏦 Loans\n"
            "• 🔧 Report a Problem\n\n"
            "What can I help you with today?"
        ),
        "hi": (
            "👋 नमस्ते {name}! *Nexura Support* में आपका स्वागत है।\n\n"
            "मैं इनमें मदद कर सकता हूँ:\n"
            "• 💰 बैलेंस और स्टेटमेंट\n"
            "• 📋 क्लेम और पॉलिसी\n"
            "• 💸 पेमेंट और पेआउट\n"
            "• 🏦 लोन\n"
            "• 🔧 समस्या रिपोर्ट करें\n\n"
            "आज मैं आपकी कैसे मदद करूं?"
        ),
        "gu": (
            "👋 નમસ્તે {name}! *Nexura Support* માં આપનું સ્વાગત છે।\n\n"
            "હું આ બાબતોમાં મદદ કરી શકું:\n"
            "• 💰 બેલેન્સ અને સ્ટેટમેન્ટ\n"
            "• 📋 ક્લેઇમ અને પોલિસી\n"
            "• 💸 ચુકવણી અને પેઆઉટ\n"
            "• 🏦 લોન\n"
            "• 🔧 સમસ્યા નોંધો\n\n"
            "આજે હું આપની કેવી રીતે મદદ કરી શકું?"
        ),
    },

    "check_balance": {
        "en": "💰 *Your Account Balance*\n\nHi {name}, your current balance is *₹{balance}*.\n\nNeed a detailed statement? Just ask!",
        "hi": "💰 *आपका खाता बैलेंस*\n\nनमस्ते {name}, आपका वर्तमान बैलेंस *₹{balance}* है।\n\nविस्तृत स्टेटमेंट चाहिए? बस बताएं!",
        "gu": "💰 *આપનો ખાતા બેલેન્સ*\n\nનમસ્તે {name}, આपनो વર્તમાન બેલેન્સ *₹{balance}* છે।\n\nવિગતવાર સ્ટેટમેન્ટ જોઈએ? બસ પૂછો!",
    },

    "check_claim_status": {
        "en": "📋 *Claim Status*\n\nClaim ID: *#{claim_id}*\nStatus: *{claim_status}*\nLast updated: {updated}\n\nOur team will contact you within 24 hours. Need help with anything else?",
        "hi": "📋 *क्लेम स्थिति*\n\nक्लेम ID: *#{claim_id}*\nस्थिति: *{claim_status}*\nअंतिम अपडेट: {updated}\n\nहमारी टीम 24 घंटे में संपर्क करेगी। कुछ और मदद चाहिए?",
        "gu": "📋 *ક્લેઇમ સ્ટેટસ*\n\nક્લેઇમ ID: *#{claim_id}*\nસ્ટેટસ: *{claim_status}*\nછેલ્લો અપડેટ: {updated}\n\nઅમારી ટીમ 24 કલાકમાં સંપર્ક કરશે। બીજી કોઈ મદદ?",
    },

    "check_policy": {
        "en": "📄 *Policy Details*\n\nPolicy No: *{policy_no}*\nCoverage: *₹{coverage}*\nStatus: *{policy_status}*\nNext Premium: *₹{premium}* due {due_date}\n\nAnything else you'd like to know?",
        "hi": "📄 *पॉलिसी विवरण*\n\nपॉलिसी नं: *{policy_no}*\nकवरेज: *₹{coverage}*\nस्थिति: *{policy_status}*\nअगला प्रीमियम: *₹{premium}* {due_date} को\n\nकुछ और जानना है?",
        "gu": "📄 *પોલિસી વિગતો*\n\nપોલિસી નં: *{policy_no}*\nકવરેજ: *₹{coverage}*\nસ્ટેટસ: *{policy_status}*\nઆગળનું પ્રીમિયમ: *₹{premium}* {due_date}\n\nબીજું કંઈ જાણવું છે?",
    },

    "check_payout": {
        "en": "💸 *Payout Details*\n\nAmount: *₹{payout_amount}*\nExpected: *{payout_date}*\nUPI: *{upi_id}*\n\nPayouts are processed within 3 working days after claim approval.",
        "hi": "💸 *पेआउट विवरण*\n\nराशि: *₹{payout_amount}*\nअपेक्षित: *{payout_date}*\nUPI: *{upi_id}*\n\nक्लेम स्वीकृति के 3 कार्य दिवसों में भुगतान होता है।",
        "gu": "💸 *પેઆઉટ વિગતો*\n\nરકમ: *₹{payout_amount}*\nઅપેક્ષિત: *{payout_date}*\nUPI: *{upi_id}*\n\nક્લેઇમ મંજૂરી પછી 3 કાર્ય દિવસોમાં ચુકવણી થાય.",
    },

    "make_payment": {
        "en": "💳 *Payment Due*\n\nAmount: *₹{amount}*\nDue Date: *{due_date}*\n\nPay via:\n• UPI: nexura@ybl\n• Link: nexura.in/pay\n\nNeed help with payment?",
        "hi": "💳 *भुगतान देय*\n\nराशि: *₹{amount}*\nदेय तिथि: *{due_date}*\n\nभुगतान करें:\n• UPI: nexura@ybl\n• लिंक: nexura.in/pay\n\nभुगतान में मदद चाहिए?",
        "gu": "💳 *ચુકવણી બાકી*\n\nરકમ: *₹{amount}*\nનિયત તારીખ: *{due_date}*\n\nચૂકવો:\n• UPI: nexura@ybl\n• લિંક: nexura.in/pay\n\nચુકવણીમાં મદદ?",
    },

    "get_statement": {
        "en": "📊 *Account Statement*\n\nYour last 3 months statement has been sent to *{email}*.\n\nOr download: nexura.in/statement\n\nAnything else?",
        "hi": "📊 *खाता विवरण*\n\nपिछले 3 महीने का स्टेटमेंट *{email}* पर भेजा गया है।\n\nया डाउनलोड करें: nexura.in/statement\n\nकुछ और?",
        "gu": "📊 *ખાતા વિવરણ*\n\nછેલ્લા 3 મહિનાનું સ્ટેટમેન્ટ *{email}* પર મોકલ્યું.\n\nઅથવા ડાઉનલોડ: nexura.in/statement\n\nબીજું?",
    },

    "get_help": {
        "en": (
            "ℹ️ *Nexura Help*\n\nType any of these:\n"
            "• *balance* — Account balance\n"
            "• *claim* — Claim status\n"
            "• *policy* — Policy details\n"
            "• *pay* — Make payment\n"
            "• *payout* — Payout status\n"
            "• *loan* — Loan info\n"
            "• *agent* — Talk to human\n\n"
            "Helpline: 1800-XXX-XXXX (24×7)"
        ),
        "hi": (
            "ℹ️ *Nexura सहायता*\n\nये टाइप करें:\n"
            "• *balance* — खाता बैलेंस\n"
            "• *claim* — क्लेम स्थिति\n"
            "• *policy* — पॉलिसी\n"
            "• *pay* — भुगतान\n"
            "• *payout* — पेआउट\n"
            "• *loan* — लोन जानकारी\n"
            "• *agent* — इंसान से बात\n\n"
            "हेल्पलाइन: 1800-XXX-XXXX"
        ),
        "gu": (
            "ℹ️ *Nexura સહાય*\n\nઆ ટાઇપ કરો:\n"
            "• *balance* — બેલેન્સ\n"
            "• *claim* — ક્લેઇમ\n"
            "• *policy* — પોલિસી\n"
            "• *pay* — ચુકવણી\n"
            "• *payout* — પેઆઉટ\n"
            "• *loan* — લોન\n"
            "• *agent* — માણસ સાથે વાત\n\n"
            "હેલ્પ: 1800-XXX-XXXX"
        ),
    },

    "escalate_agent": {
        "en": "🔗 *Connecting you to a human agent...*\n\nYou're #3 in queue. Expected wait: *~5 minutes*.\n\nOr call directly: *1800-XXX-XXXX* (24×7 Toll Free)",
        "hi": "🔗 *आपको एजेंट से जोड़ रहे हैं...*\n\nआप कतार में #3 हैं। अनुमानित प्रतीक्षा: *~5 मिनट*।\n\nया सीधे कॉल करें: *1800-XXX-XXXX*",
        "gu": "🔗 *એજન્ટ સાથે જોડ઼ી રહ્યા છીએ...*\n\nઆप ક્યૂ #3 પર છો. અંદાજ: *~5 મિનિટ*।\n\nઅથવા સીધો ફોન: *1800-XXX-XXXX*",
    },

    "report_problem": {
        "en": "🔧 *Problem Report*\n\nSorry you're facing an issue! 😔\n\nPlease describe your problem in detail and I'll escalate it immediately.\n\nOr call: *1800-XXX-XXXX* (24×7)",
        "hi": "🔧 *समस्या रिपोर्ट*\n\nसमस्या के लिए खेद है! 😔\n\nसमस्या विस्तार से बताएं, मैं तुरंत एस्केलेट करूंगा।\n\nया कॉल करें: *1800-XXX-XXXX*",
        "gu": "🔧 *સમસ્યા રિપોર્ટ*\n\nસમસ્યા માટે ખેદ! 😔\n\nવિગતવાર સમસ્યા જણાવો, હું તરત escalate કરીશ।\n\nફોન: *1800-XXX-XXXX*",
    },

    "farewell": {
        "en": "👍 Thank you {name}! Have a great day. Stay protected with Nexura! 🙏",
        "hi": "👍 धन्यवाद {name}! आपका दिन शुभ हो। Nexura के साथ सुरक्षित रहें! 🙏",
        "gu": "👍 આભાર {name}! સારો દિવસ. Nexura સાથે સુરક્ષિત! 🙏",
    },

    "thanks": {
        "en": "😊 You're welcome! Is there anything else I can help you with?",
        "hi": "😊 कोई बात नहीं! क्या मैं कुछ और मदद कर सकता हूँ?",
        "gu": "😊 આભાર! બીજી કોઈ મદદ?",
    },

    "unknown": {
        "en": "🤔 I'm not sure I understood that. Could you rephrase?\n\nType *help* to see what I can do, or say *agent* to speak with someone.",
        "hi": "🤔 मुझे समझ नहीं आया। क्या आप दोबारा बता सकते हैं?\n\n*help* टाइप करें, या *agent* कहें।",
        "gu": "🤔 સમજ ન પડ્યું. ફરી જણાવો?\n\n*help* ટાઇપ કરો, અથવા *agent* કહો.",
    },

    "ask_slot_incident_description": {
        "en": "📝 To file your claim, please describe the incident briefly.\n\n*Example: My bike was stolen on April 10 near MG Road.*",
        "hi": "📝 क्लेम दर्ज करने के लिए, घटना का संक्षिप्त विवरण दें।\n\n*उदाहरण: 10 अप्रैल को MG Road पर मेरी बाइक चोरी हुई।*",
        "gu": "📝 ક્લેઇમ ફાઇલ કરવા, ઘટનાનું ટૂંકું વર્ણન કરો।",
    },

    "ask_slot_problem_description": {
        "en": "📝 Please describe your problem in detail so I can help better.",
        "hi": "📝 अपनी समस्या विस्तार से बताएं ताकि मैं बेहतर मदद कर सकूं।",
        "gu": "📝 તમારી સમસ્યા વિગતવાર જણાવો.",
    },
}


# ─── DB Context Fetchers ──────────────────────────────────────────────────────

def _fmt(val, prefix='₹') -> str:
    try:
        return f"{float(val):,.2f}"
    except (TypeError, ValueError):
        return '—'

def _date(val) -> str:
    if val is None:
        return '—'
    try:
        return val.strftime('%d %b %Y') if hasattr(val, 'strftime') else str(val)
    except Exception:
        return '—'


def _get_context_for_intent(intent_name: str, user) -> dict:
    ctx = {'name': 'Friend', 'email': '—'}
    if user:
        ctx['name']  = user.first_name or 'Friend'
        ctx['email'] = user.email or '—'

    if intent_name == 'check_balance' and user:
        try:
            ctx['balance'] = _fmt(user.workerprofile.wallet_balance)
        except Exception:
            ctx['balance'] = '—'

    elif intent_name == 'check_claim_status' and user:
        try:
            from apps.claims.models import Claim
            c = Claim.objects.filter(worker=user).order_by('-created_at').first()
            if c:
                ctx.update({
                    'claim_id':     str(c.pk),
                    'claim_status': c.get_status_display() if hasattr(c, 'get_status_display') else c.status,
                    'updated':      _date(c.updated_at if hasattr(c, 'updated_at') else c.created_at),
                })
            else:
                ctx.update({'claim_id': 'N/A', 'claim_status': 'No claim found', 'updated': '—'})
        except Exception:
            ctx.update({'claim_id': '—', 'claim_status': '—', 'updated': '—'})

    elif intent_name == 'check_policy' and user:
        try:
            from apps.policies.models import Policy
            p = Policy.objects.filter(worker=user, is_active=True).order_by('-created_at').first()
            if p:
                ctx.update({
                    'policy_no':     getattr(p, 'policy_number', str(p.pk)),
                    'coverage':      _fmt(getattr(p, 'coverage_amount', 0)),
                    'policy_status': 'Active',
                    'premium':       _fmt(getattr(p, 'premium_amount', 0)),
                    'due_date':      _date(getattr(p, 'next_due_date', None)),
                })
            else:
                ctx.update({'policy_no': 'N/A', 'coverage': '—', 'policy_status': 'No policy', 'premium': '—', 'due_date': '—'})
        except Exception:
            ctx.update({'policy_no': '—', 'coverage': '—', 'policy_status': '—', 'premium': '—', 'due_date': '—'})

    elif intent_name == 'check_payout' and user:
        try:
            from apps.payouts.models import Payout
            p = Payout.objects.filter(worker=user).order_by('-created_at').first()
            if p:
                ctx.update({
                    'payout_amount': _fmt(getattr(p, 'amount', 0)),
                    'payout_date':   _date(getattr(p, 'expected_date', None) or getattr(p, 'created_at', None)),
                    'upi_id':        getattr(user.workerprofile, 'upi_id', '—') if hasattr(user, 'workerprofile') else '—',
                })
            else:
                ctx.update({'payout_amount': '—', 'payout_date': '—', 'upi_id': '—'})
        except Exception:
            ctx.update({'payout_amount': '—', 'payout_date': '—', 'upi_id': '—'})

    elif intent_name == 'make_payment' and user:
        try:
            from apps.policies.models import Policy
            p = Policy.objects.filter(worker=user, is_active=True).order_by('-created_at').first()
            ctx.update({
                'amount':   _fmt(getattr(p, 'premium_amount', 0)) if p else '—',
                'due_date': _date(getattr(p, 'next_due_date', None)) if p else '—',
            })
        except Exception:
            ctx.update({'amount': '—', 'due_date': '—'})

    return ctx


# ─── Main Response Function ───────────────────────────────────────────────────

def generate_response(
    intent:           IntentResult,
    lang:             str,
    user,
    conversation_history: list,
    session_context:  dict,
) -> tuple[str, bool, int, int]:
    """
    Generate the best possible response for the given intent.

    Returns
    -------
    (response_text, llm_used, tokens_used, latency_ms)
    """
    intent_name = intent.intent
    confidence  = intent.confidence

    # ── Slot collection prompts ──────────────────────────────────────────
    if intent_name.startswith('ask_slot_'):
        tmpl = TEMPLATES.get(intent_name, TEMPLATES['unknown'])
        return tmpl.get(lang, tmpl['en']), False, 0, 0

    # ── Rule-based (high confidence) ────────────────────────────────────
    if confidence >= RULE_CONFIDENCE_THRESHOLD and intent_name != 'unknown':
        ctx  = _get_context_for_intent(intent_name, user)
        tmpl = TEMPLATES.get(intent_name, TEMPLATES['unknown'])
        text = tmpl.get(lang, tmpl.get('en', ''))
        try:
            return text.format(**ctx), False, 0, 0
        except KeyError as e:
            logger.warning("Template KeyError for %s: %s", intent_name, e)
            return text, False, 0, 0

    # ── LLM enrichment (low confidence or unknown) ───────────────────────
    if is_llm_configured():
        try:
            # Build rich context string to inject into LLM
            ctx         = _get_context_for_intent(intent_name, user)
            ctx_lines   = '\n'.join(f"{k}: {v}" for k, v in ctx.items() if v and v != '—')
            system_note = f"\n\nUser account context (use if relevant):\n{ctx_lines}" if ctx_lines else ''

            from .llm_provider import build_system_prompt
            system = build_system_prompt(lang) + system_note

            text, tokens, latency = get_llm_response(
                messages=conversation_history,
                system=system,
                lang=lang,
            )
            if text:
                return text, True, tokens, latency
        except Exception as e:
            logger.error("[ResponseEngine] LLM error: %s", e, exc_info=True)

    # ── Final fallback ───────────────────────────────────────────────────
    tmpl = TEMPLATES.get(intent_name, TEMPLATES['unknown'])
    ctx  = _get_context_for_intent(intent_name, user)
    text = tmpl.get(lang, tmpl.get('en', ''))
    try:
        return text.format(**ctx), False, 0, 0
    except KeyError:
        return text, False, 0, 0
