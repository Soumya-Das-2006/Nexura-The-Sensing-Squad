"""
apps/chatbot/llm_provider.py

Unified LLM provider abstraction supporting:
    - Anthropic Claude (claude-sonnet-4-20250514)
    - OpenAI GPT-4o
    - Google Gemini 1.5 Flash

Provider is selected via settings.CHATBOT_LLM_PROVIDER.
Falls back gracefully: Anthropic → OpenAI → Gemini → Rule-based.

Usage:
    from apps.chatbot.llm_provider import get_llm_response
    reply = get_llm_response(messages, system_prompt, lang='hi')
"""

import logging
import time
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── System Prompt Template ───────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are Nexura Assistant — a helpful, professional banking and insurance support chatbot for Nexura, an Indian gig-worker insurance platform.

Your personality:
- Warm, clear, concise — like a knowledgeable bank employee
- Never robotic. Use natural phrasing.
- For Indian users, it is perfectly fine to mix Hindi words naturally in English responses

Your rules:
1. ALWAYS respond in the SAME language the user writes in:
   - If user writes in Hindi (Devanagari) → reply in Hindi
   - If user writes in Hinglish (Roman Hindi) → reply in Hindi
   - If user writes in English → reply in English
   - If user writes in Gujarati → reply in Gujarati
2. NEVER invent account details, balances, or claim statuses — say you're fetching them
3. For sensitive actions (large transfers, claim filing) — always confirm before proceeding
4. If you cannot help, offer to escalate to a human agent
5. Keep replies SHORT — max 4-5 lines. Use bullet points only when listing multiple items.
6. Always end with a helpful follow-up question or next step

Domain knowledge:
- Nexura provides micro-insurance for gig workers (delivery, cab drivers etc.)
- Products: Accident cover, health cover, income protection
- Claims are processed in 3-5 business days
- Payouts go to registered UPI/bank account
- Premium is weekly, auto-deducted

Current language instruction: {lang_instruction}
"""

LANG_INSTRUCTIONS = {
    'en': "Respond in clear, friendly English.",
    'hi': "हमेशा हिंदी में जवाब दें। देवनागरी लिपि का उपयोग करें। सरल और स्पष्ट भाषा में लिखें।",
    'gu': "હંમેશા ગુજરાતીમાં જવાબ આપો। ગુજરાતી લિપિ વાપરો। સ્પષ્ટ અને સરળ ભાષામાં લખો।",
}


def build_system_prompt(lang: str = 'en') -> str:
    lang_instr = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS['en'])
    return BASE_SYSTEM_PROMPT.format(lang_instruction=lang_instr)


# ─── Provider Implementations ─────────────────────────────────────────────────

def _call_anthropic(messages: list, system: str, max_tokens: int = 400) -> tuple[str, int]:
    """Call Anthropic Claude API. Returns (text, tokens_used)."""
    import anthropic
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    text   = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return text, tokens


def _call_openai(messages: list, system: str, max_tokens: int = 400) -> tuple[str, int]:
    """Call OpenAI GPT-4o API. Returns (text, tokens_used)."""
    from openai import OpenAI
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    full_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    text   = response.choices[0].message.content
    tokens = response.usage.total_tokens
    return text, tokens


def _call_gemini(messages: list, system: str, max_tokens: int = 400) -> tuple[str, int]:
    """Call Google Gemini API. Returns (text, tokens_used)."""
    import google.generativeai as genai
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        system_instruction=system,
    )
    # Convert messages to Gemini format
    history = []
    for m in messages[:-1]:
        role = 'user' if m['role'] == 'user' else 'model'
        history.append({'role': role, 'parts': [m['content']]})

    chat     = model.start_chat(history=history)
    response = chat.send_message(messages[-1]['content'])
    text     = response.text
    tokens   = getattr(response.usage_metadata, 'total_token_count', 0)
    return text, tokens


# ─── Unified Interface ────────────────────────────────────────────────────────

PROVIDER_MAP = {
    'anthropic': _call_anthropic,
    'openai':    _call_openai,
    'gemini':    _call_gemini,
}


def get_llm_response(
    messages:   list,
    system:     Optional[str] = None,
    lang:       str = 'en',
    max_tokens: int = 400,
) -> tuple[str, int, int]:
    """
    Call the configured LLM provider.

    Parameters
    ----------
    messages   : List of {"role": "user"|"assistant", "content": str}
    system     : System prompt override (uses base prompt if None)
    lang       : Language code for system prompt injection
    max_tokens : Max response tokens

    Returns
    -------
    (response_text, tokens_used, latency_ms)
    """
    provider_name = getattr(settings, 'CHATBOT_LLM_PROVIDER', 'anthropic').lower()
    system_prompt = system or build_system_prompt(lang)

    # Try configured provider, then fallback order
    order = [provider_name] + [p for p in ['anthropic', 'openai', 'gemini'] if p != provider_name]

    for provider in order:
        fn = PROVIDER_MAP.get(provider)
        if fn is None:
            continue
        try:
            t0              = time.monotonic()
            text, tokens    = fn(messages, system_prompt, max_tokens)
            latency_ms      = int((time.monotonic() - t0) * 1000)
            logger.info("[LLM:%s] tokens=%d latency=%dms", provider, tokens, latency_ms)
            return text.strip(), tokens, latency_ms
        except ValueError as e:
            # Missing API key — skip to next provider silently
            logger.debug("[LLM:%s] Skipping: %s", provider, e)
        except Exception as e:
            logger.error("[LLM:%s] Error: %s", provider, e, exc_info=True)

    # All providers failed / no keys configured — return fallback
    logger.warning("[LLM] All providers failed. Using rule-based fallback.")
    return '', 0, 0


def is_llm_configured() -> bool:
    """Returns True if at least one LLM API key is set."""
    return any([
        getattr(settings, 'ANTHROPIC_API_KEY', ''),
        getattr(settings, 'OPENAI_API_KEY', ''),
        getattr(settings, 'GEMINI_API_KEY', ''),
    ])
