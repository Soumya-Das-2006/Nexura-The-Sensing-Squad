"""
apps/core/context_processors.py

Injects a `nexura` dict into every template context.
Access in templates as: {{ nexura.site_name }}, {{ nexura.current_year }}, etc.
"""
from datetime import date


def nexura_globals(request):
    """
    Global template context for every Nexura page.
    Available in templates as {{ nexura.* }}
    """
    return {
        'nexura': {
            # ── Branding ──────────────────────────────────────────────────
            'site_name':     'Nexura',
            'tagline':       'Income Protection for India\'s Gig Workers',
            'support_email': 'support@nexaura.in',
            'whatsapp_number': '918000000000',   # no + for wa.me links
            'phone':         '+91 80000 00000',
            'current_year':  date.today().year,

            # ── Plans (for footer / nav quick-access) ─────────────────────
            'plans': [
                {
                    'name':     'Basic Shield',
                    'premium':  29,
                    'coverage': 500,
                    'slug':     'basic',
                },
                {
                    'name':     'Standard Shield',
                    'premium':  49,
                    'coverage': 1000,
                    'slug':     'standard',
                },
                {
                    'name':     'Premium Shield',
                    'premium':  79,
                    'coverage': 2000,
                    'slug':     'premium',
                },
            ],

            # ── Cities ────────────────────────────────────────────────────
            'covered_cities': [
                'Mumbai', 'Delhi', 'Bangalore',
                'Chennai', 'Hyderabad', 'Kolkata', 'Pune',
            ],

            # ── Platforms ─────────────────────────────────────────────────
            'supported_platforms': [
                'Zomato', 'Swiggy', 'Amazon', 'Zepto', 'Blinkit', 'Dunzo',
            ],

            # ── Trigger thresholds (for info pages) ───────────────────────
            'triggers': {
                'rain_mm_hr':   35,
                'heat_celsius': 42,
                'aqi_value':    300,
                'platform_downtime_min': 30,
            },

            # ── Social links ──────────────────────────────────────────────
            'social': {
                'twitter':   'https://twitter.com/nexaura_in',
                'instagram': 'https://instagram.com/nexaura_in',
                'linkedin':  'https://linkedin.com/company/nexaura',
                'facebook':  'https://facebook.com/nexaura.in',
            },
        }
    }