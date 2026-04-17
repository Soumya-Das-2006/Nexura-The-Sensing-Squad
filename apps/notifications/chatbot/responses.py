"""
apps/notifications/chatbot/responses.py

Multilingual response catalogue for Nexura banking/insurance chatbot.

Structure:
    RESPONSES = {
        "intent_name": {
            "en": "English response",
            "hi": "Hindi response (Devanagari)",
            "gu": "Gujarati response (Gujarati script)",
        }
    }

All responses use {placeholder} style formatting so they can be
personalized with real user data from the DB.

Supported placeholders:
    {name}          — worker's first name
    {balance}       — account balance (₹ formatted)
    {claim_id}      — claim reference number
    {claim_status}  — claim status string
    {policy_no}     — policy number
    {coverage}      — coverage amount
    {payout_amount} — payout amount
    {payout_date}   — expected payout date
    {due_date}      — EMI / premium due date
    {amount}        — generic amount
"""

RESPONSES: dict[str, dict[str, str]] = {

    # ── Greeting ──────────────────────────────────────────────────────────────
    "greet": {
        "en": (
            "👋 Hello {name}! Welcome to Nexura.\n\n"
            "I can help you with:\n"
            "1️⃣ Check Balance\n"
            "2️⃣ Claim Status\n"
            "3️⃣ Policy Details\n"
            "4️⃣ Payout Status\n"
            "5️⃣ Make Payment\n"
            "6️⃣ Account Statement\n\n"
            "Type a number or just ask me anything! 😊"
        ),
        "hi": (
            "👋 नमस्ते {name}! Nexura में आपका स्वागत है।\n\n"
            "मैं आपकी इन सेवाओं में मदद कर सकता हूँ:\n"
            "1️⃣ बैलेंस जाँचें\n"
            "2️⃣ क्लेम की स्थिति\n"
            "3️⃣ पॉलिसी विवरण\n"
            "4️⃣ पेआउट स्थिति\n"
            "5️⃣ भुगतान करें\n"
            "6️⃣ खाता विवरण\n\n"
            "कोई नंबर टाइप करें या सीधे पूछें! 😊"
        ),
        "gu": (
            "👋 નમસ્તે {name}! Nexura માં આપનું સ્વાગત છે।\n\n"
            "હું આ સેવાઓમાં મદદ કરી શકું છું:\n"
            "1️⃣ બેલેન્સ તપાસો\n"
            "2️⃣ ક્લેઇમ સ્ટેટસ\n"
            "3️⃣ પોલિસી વિગતો\n"
            "4️⃣ પેઆઉટ સ્ટેટસ\n"
            "5️⃣ ચુકવણી કરો\n"
            "6️⃣ ખાતા વિવરણ\n\n"
            "નંબર ટાઇપ કરો અથવા સીધું પૂછો! 😊"
        ),
    },

    # ── Balance ───────────────────────────────────────────────────────────────
    "check_balance": {
        "en": (
            "💰 *Account Balance*\n\n"
            "Hi {name}, your current balance is:\n"
            "*₹{balance}*\n\n"
            "For detailed statement, type *statement*."
        ),
        "hi": (
            "💰 *खाता बैलेंस*\n\n"
            "नमस्ते {name}, आपका वर्तमान बैलेंस:\n"
            "*₹{balance}*\n\n"
            "विस्तृत विवरण के लिए *statement* टाइप करें।"
        ),
        "gu": (
            "💰 *ખાતા બેલેન્સ*\n\n"
            "નમસ્તે {name}, આપનો વર્તમાન બેલેન્સ:\n"
            "*₹{balance}*\n\n"
            "વિગતવાર વિવરણ માટે *statement* ટાઇપ કરો।"
        ),
    },

    # ── Claim Status ─────────────────────────────────────────────────────────
    "check_claim_status": {
        "en": (
            "📋 *Claim Status*\n\n"
            "Claim ID: *{claim_id}*\n"
            "Status: *{claim_status}*\n\n"
            "For updates, our team will contact you within 24 hours.\n"
            "Helpline: 1800-XXX-XXXX (toll free)"
        ),
        "hi": (
            "📋 *क्लेम स्थिति*\n\n"
            "क्लेम ID: *{claim_id}*\n"
            "स्थिति: *{claim_status}*\n\n"
            "हमारी टीम 24 घंटे में संपर्क करेगी।\n"
            "हेल्पलाइन: 1800-XXX-XXXX (टोल फ्री)"
        ),
        "gu": (
            "📋 *ક્લેઇમ સ્ટેટસ*\n\n"
            "ક્લેઇમ ID: *{claim_id}*\n"
            "સ્ટેટસ: *{claim_status}*\n\n"
            "અમારી ટીમ 24 કલાકમાં સંપર્ક કરશે।\n"
            "હેલ્પલાઇન: 1800-XXX-XXXX (ટોલ ફ્રી)"
        ),
    },

    # ── Policy Details ────────────────────────────────────────────────────────
    "check_policy": {
        "en": (
            "📄 *Policy Details*\n\n"
            "Policy No: *{policy_no}*\n"
            "Coverage: *₹{coverage}*\n\n"
            "For full policy document, visit nexura.in/policy"
        ),
        "hi": (
            "📄 *पॉलिसी विवरण*\n\n"
            "पॉलिसी नं: *{policy_no}*\n"
            "कवरेज: *₹{coverage}*\n\n"
            "पूर्ण दस्तावेज़ के लिए nexura.in/policy पर जाएं।"
        ),
        "gu": (
            "📄 *પોલિસી વિગતો*\n\n"
            "પોલિસી નં: *{policy_no}*\n"
            "કવરેજ: *₹{coverage}*\n\n"
            "સંપૂર્ણ દસ્તાવેજ માટે nexura.in/policy પર જાઓ।"
        ),
    },

    # ── Payout Status ─────────────────────────────────────────────────────────
    "check_payout": {
        "en": (
            "💸 *Payout Status*\n\n"
            "Amount: *₹{payout_amount}*\n"
            "Expected Date: *{payout_date}*\n\n"
            "Payouts are processed within 3 working days."
        ),
        "hi": (
            "💸 *पेआउट स्थिति*\n\n"
            "राशि: *₹{payout_amount}*\n"
            "अपेक्षित तिथि: *{payout_date}*\n\n"
            "भुगतान 3 कार्य दिवसों में प्रोसेस होता है।"
        ),
        "gu": (
            "💸 *પેઆઉટ સ્ટેટસ*\n\n"
            "રકમ: *₹{payout_amount}*\n"
            "અપેક્ષિત તારીખ: *{payout_date}*\n\n"
            "ચુકવણી 3 કાર્ય દિવસોમાં પ્રક્રિયા થાય છે।"
        ),
    },

    # ── Payment ───────────────────────────────────────────────────────────────
    "make_payment": {
        "en": (
            "💳 *Payment*\n\n"
            "Due Amount: *₹{amount}*\n"
            "Due Date: *{due_date}*\n\n"
            "Pay now: nexura.in/pay\n"
            "UPI: nexura@ybl"
        ),
        "hi": (
            "💳 *भुगतान*\n\n"
            "देय राशि: *₹{amount}*\n"
            "देय तिथि: *{due_date}*\n\n"
            "अभी भुगतान करें: nexura.in/pay\n"
            "UPI: nexura@ybl"
        ),
        "gu": (
            "💳 *ચુકવણી*\n\n"
            "બાકી રકમ: *₹{amount}*\n"
            "નિયત તારીખ: *{due_date}*\n\n"
            "હમણાં ચૂકવો: nexura.in/pay\n"
            "UPI: nexura@ybl"
        ),
    },

    # ── Statement ─────────────────────────────────────────────────────────────
    "get_statement": {
        "en": (
            "📊 *Account Statement*\n\n"
            "Your last 3 months statement has been sent to your registered email.\n\n"
            "Or download from: nexura.in/statement"
        ),
        "hi": (
            "📊 *खाता विवरण*\n\n"
            "पिछले 3 महीने का विवरण आपके पंजीकृत ईमेल पर भेजा गया है।\n\n"
            "या यहाँ से डाउनलोड करें: nexura.in/statement"
        ),
        "gu": (
            "📊 *ખાતા વિવરણ*\n\n"
            "છેલ્લા 3 મહિનાનું વિવરણ આપના નોંધાયેલ ઈ-મેઇલ પર મોકલ્યું છે।\n\n"
            "અથવા ડાઉનલોડ કરો: nexura.in/statement"
        ),
    },

    # ── Problem / Complaint ────────────────────────────────────────────────────
    "report_problem": {
        "en": (
            "🔧 *Report a Problem*\n\n"
            "Sorry to hear you're facing an issue! 😔\n\n"
            "Please describe your problem and we'll connect you with our support team.\n"
            "Or call: 1800-XXX-XXXX (24×7 Toll Free)"
        ),
        "hi": (
            "🔧 *समस्या रिपोर्ट करें*\n\n"
            "आपको समस्या हो रही है, हमें खेद है! 😔\n\n"
            "अपनी समस्या बताएं, हम आपको सहायता टीम से जोड़ेंगे।\n"
            "या कॉल करें: 1800-XXX-XXXX (24×7 टोल फ्री)"
        ),
        "gu": (
            "🔧 *સમસ્યા નોંધો*\n\n"
            "તમને સમસ્યા થઈ રહી છે, અમને ખેદ છે! 😔\n\n"
            "તમારી સમસ્યા જણાવો, અમે તમને સહાય ટીમ સાથે જોડીશું।\n"
            "અથવા કૉલ કરો: 1800-XXX-XXXX (24×7 ટોલ ફ્રી)"
        ),
    },

    # ── Help / Menu ───────────────────────────────────────────────────────────
    "get_help": {
        "en": (
            "ℹ️ *Nexura Help Menu*\n\n"
            "Type any of these:\n"
            "• *balance* — Check account balance\n"
            "• *claim* — Claim status\n"
            "• *policy* — Policy details\n"
            "• *payout* — Payout status\n"
            "• *pay* — Make a payment\n"
            "• *statement* — Account statement\n\n"
            "Helpline: 1800-XXX-XXXX"
        ),
        "hi": (
            "ℹ️ *Nexura सहायता मेनू*\n\n"
            "इनमें से कुछ टाइप करें:\n"
            "• *balance* — बैलेंस जाँचें\n"
            "• *claim* — क्लेम स्थिति\n"
            "• *policy* — पॉलिसी विवरण\n"
            "• *payout* — पेआउट स्थिति\n"
            "• *pay* — भुगतान करें\n"
            "• *statement* — खाता विवरण\n\n"
            "हेल्पलाइन: 1800-XXX-XXXX"
        ),
        "gu": (
            "ℹ️ *Nexura સહાય મેનૂ*\n\n"
            "આ ટાઇપ કરો:\n"
            "• *balance* — બેલેન્સ તપાસો\n"
            "• *claim* — ક્લેઇમ સ્ટેટસ\n"
            "• *policy* — પોલિસી વિગતો\n"
            "• *payout* — પેઆઉટ સ્ટેટસ\n"
            "• *pay* — ચૂકવણી કરો\n"
            "• *statement* — ખાતા વિવરણ\n\n"
            "હેલ્પલાઇન: 1800-XXX-XXXX"
        ),
    },

    # ── Farewell ──────────────────────────────────────────────────────────────
    "farewell": {
        "en": "👍 Thank you {name}! Have a great day. Stay safe with Nexura! 🙏",
        "hi": "👍 धन्यवाद {name}! आपका दिन शुभ हो। Nexura के साथ सुरक्षित रहें! 🙏",
        "gu": "👍 આભાર {name}! આપનો દિવસ શુભ રહે। Nexura સાથે સુરક્ષિત રહો! 🙏",
    },

    # ── Unknown / Fallback ────────────────────────────────────────────────────
    "unknown": {
        "en": (
            "🤔 Sorry, I didn't understand that.\n\n"
            "Type *help* to see what I can do, or call 1800-XXX-XXXX."
        ),
        "hi": (
            "🤔 माफ़ करें, मैं समझ नहीं पाया।\n\n"
            "मदद के लिए *help* टाइप करें, या 1800-XXX-XXXX पर कॉल करें।"
        ),
        "gu": (
            "🤔 માફ કરો, હું સમજ્યો નહીં।\n\n"
            "મદદ માટે *help* ટાઇપ કરો, અથવા 1800-XXX-XXXX પર કૉલ કરો।"
        ),
    },
}


def get_response(intent_name: str, lang: str, **kwargs) -> str:
    """
    Retrieve and format a response for the given intent and language.

    Parameters
    ----------
    intent_name : Intent string (e.g. 'check_balance')
    lang        : Language code 'en' | 'hi' | 'gu'
    **kwargs    : Placeholder values for string formatting

    Returns
    -------
    Formatted response string ready to send via WhatsApp.
    """
    intent_responses = RESPONSES.get(intent_name, RESPONSES['unknown'])
    # Fallback: if lang not in catalogue, use English
    template = intent_responses.get(lang) or intent_responses.get('en', '')

    try:
        return template.format(**kwargs)
    except KeyError:
        # Missing placeholder — return template as-is
        return template
