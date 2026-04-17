"""
apps/core/views.py
All public-facing page views for Nexura.
Each view's context dict matches the template's variable names exactly.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.http import Http404
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


# ─── Home ─────────────────────────────────────────────────────────────────────

class HomeView(View):
    template_name = 'core/home.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.is_worker:
            return redirect('workers:dashboard')

        ctx = {
            'stats': [
                {'icon': 'fas fa-users',    'value': '1,24,000+', 'label': 'Workers Protected'},
                {'icon': 'fas fa-city',     'value': '7',         'label': 'Cities Covered'},
                {'icon': 'fas fa-bolt',     'value': '<2 hrs',    'label': 'Avg Payout Time'},
                {'icon': 'fas fa-check-circle', 'value': '94%',   'label': 'Auto-Approved Claims'},
            ],
            'plans': [
                {
                    'name': 'Basic Shield',
                    'slug': 'basic',
                    'icon': 'fas fa-shield-alt',
                    'weekly_premium': 29,
                    'weekly_coverage': 500,
                    'recommended': False,
                    'features': [
                        'Up to ₹500 weekly protection',
                        'Auto claim filing',
                        'UPI payout support',
                    ],
                },
                {
                    'name': 'Standard Shield',
                    'slug': 'standard',
                    'icon': 'fas fa-umbrella',
                    'weekly_premium': 49,
                    'weekly_coverage': 1000,
                    'recommended': True,
                    'features': [
                        'Up to ₹1,000 weekly protection',
                        'Priority claim routing',
                        'WhatsApp status alerts',
                    ],
                },
                {
                    'name': 'Premium Shield',
                    'slug': 'premium',
                    'icon': 'fas fa-crown',
                    'weekly_premium': 79,
                    'weekly_coverage': 2000,
                    'recommended': False,
                    'features': [
                        'Up to ₹2,000 weekly protection',
                        'Fast payout queue',
                        'Full disruption coverage',
                    ],
                },
            ],
            'testimonials': [
                {
                    'name':     'Ramesh Kumar',
                    'platform': 'Zomato Delivery Partner · Mumbai',
                    'text':     'Jab baarish mein order nahi mila, Nexura ne 45 minute mein ₹1,000 bhej diya. Ek bhi form nahi bhara!',
                    'stars':    5,
                    'img':      'testimonial-1.jpg',
                },
                {
                    'name':     'Priya Devi',
                    'platform': 'Swiggy Partner · Bangalore',
                    'text':     'AQI 310 tha, maine kaam band kar diya. Agle ghante mein paise aa gaye. Nexura sach mein kaam karta hai.',
                    'stars':    5,
                    'img':      'testimonial-2.jpg',
                },
                {
                    'name':     'Arjun Singh',
                    'platform': 'Amazon Flex · Delhi',
                    'text':     'Platform down tha 2 ghante, ₹500 automatic credit ho gaya. No waiting, no calls. Magic!',
                    'stars':    5,
                    'img':      'testimonial-3.jpg',
                },
            ],
            'platforms': [
                {'name': 'Zomato'}, {'name': 'Swiggy'}, {'name': 'Amazon'},
                {'name': 'Zepto'}, {'name': 'Blinkit'}, {'name': 'Dunzo'},
            ],
            'triggers': [
                {
                    'icon': 'fas fa-cloud-showers-heavy',
                    'name': 'Heavy Rain',
                    'description': 'Rainfall above threshold in your active zone.',
                    'threshold': '> 35 mm/hr',
                    'color': 'text-primary',
                    'bg': 'bg-white',
                },
                {
                    'icon': 'fas fa-thermometer-full',
                    'name': 'Extreme Heat',
                    'description': 'Heat stress event confirmed via weather feed.',
                    'threshold': '> 42°C',
                    'color': 'text-danger',
                    'bg': 'bg-white',
                },
                {
                    'icon': 'fas fa-smog',
                    'name': 'Severe AQI',
                    'description': 'Air quality spike crosses safe working limits.',
                    'threshold': '> AQI 300',
                    'color': 'text-warning',
                    'bg': 'bg-white',
                },
                {
                    'icon': 'fas fa-water',
                    'name': 'Flash Flood',
                    'description': 'Official flood warning for your mapped service area.',
                    'threshold': 'Official IMD alert',
                    'color': 'text-info',
                    'bg': 'bg-white',
                },
                {
                    'icon': 'fas fa-ban',
                    'name': 'Curfew / Strike',
                    'description': 'Government order or city shutdown blocks operations.',
                    'threshold': 'Verified civic order',
                    'color': 'text-secondary',
                    'bg': 'bg-white',
                },
                {
                    'icon': 'fas fa-server',
                    'name': 'App Downtime',
                    'description': 'Delivery partner app outage detected and validated.',
                    'threshold': '> 30 minutes',
                    'color': 'text-dark',
                    'bg': 'bg-white',
                },
            ],
        }
        return render(request, self.template_name, ctx)


# ─── About ────────────────────────────────────────────────────────────────────

class AboutView(View):
    template_name = 'core/about.html'

    def get(self, request):
        return render(request, self.template_name)


# ─── How It Works ─────────────────────────────────────────────────────────────

class HowItWorksView(View):
    template_name = 'core/how_it_works.html'

    def get(self, request):
        # step.color used as Bootstrap colour name (primary/success/warning/danger/info/dark)
        # step.description (NOT step.desc) — matches template {{ step.description }}
        ctx = {
            'steps': [
                {
                    'number':      '01',
                    'icon':        'fas fa-user-plus',
                    'color':       'primary',
                    'title':       'Register in 2 Minutes',
                    'description': 'Sign up with your mobile number. Verify via OTP. Link your UPI ID and delivery platform. Complete Aadhaar / DigiLocker KYC.',
                },
                {
                    'number':      '02',
                    'icon':        'fas fa-shield-alt',
                    'color':       'success',
                    'title':       'Choose Your Shield',
                    'description': 'Pick Basic (₹29/wk), Standard (₹49/wk), or Premium (₹79/wk). Set up Razorpay Autopay once — premium is deducted every Monday.',
                },
                {
                    'number':      '03',
                    'icon':        'fas fa-satellite-dish',
                    'color':       'info',
                    'title':       'AI Monitors 24/7',
                    'description': 'Our system polls OpenWeatherMap every 15 min, WAQI every 30 min, and platform status every 10 min. No action needed from you.',
                },
                {
                    'number':      '04',
                    'icon':        'fas fa-bolt',
                    'color':       'warning',
                    'title':       'Disruption Detected',
                    'description': 'When a qualifying event hits your zone — heavy rain, heat, AQI, flood, curfew, or platform crash — a claim is automatically created.',
                },
                {
                    'number':      '05',
                    'icon':        'fas fa-robot',
                    'color':       'danger',
                    'title':       'AI Fraud Check (6 Layers)',
                    'description': 'Parametric gate → duplicate check → GPS zone validation → Isolation Forest ML score → routing (<0.50 approve / >0.70 reject) → nightly rescan.',
                },
                {
                    'number':      '06',
                    'icon':        'fas fa-rupee-sign',
                    'color':       'success',
                    'title':       'UPI Payout < 2 Hours',
                    'description': 'Approved claims trigger Razorpay Payouts API. Money lands in your UPI within 2 hours. WhatsApp notification includes UTR reference.',
                },
            ],
        }
        return render(request, self.template_name, ctx)


# ─── Features ─────────────────────────────────────────────────────────────────

class FeaturesView(View):
    """Features page is fully hardcoded in the template — no context needed."""
    template_name = 'core/features.html'

    def get(self, request):
        return render(request, self.template_name)


# ─── FAQ ──────────────────────────────────────────────────────────────────────

class FAQView(View):
    template_name = 'core/faq.html'

    def get(self, request):
        # Template iterates: {% for category, faq_list in grouped_faqs.items %}
        # Each item in faq_list needs 'question' and 'answer' keys
        grouped_faqs = {
            'Getting Started': [
                {
                    'question': 'Who can use Nexura?',
                    'answer':   'Any gig delivery worker on Zomato, Swiggy, Amazon Flex, Zepto, Blinkit, or Dunzo in Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Kolkata, or Pune.',
                },
                {
                    'question': 'How do I register?',
                    'answer':   'Visit nexaura.in or open the app. Enter your mobile number, verify via OTP, add your UPI ID, select your delivery platform, and choose a plan. Under 2 minutes.',
                },
                {
                    'question': 'What documents do I need?',
                    'answer':   'Just your Aadhaar number for OTP-based KYC, or link DigiLocker for faster verification. No physical documents, no branch visits.',
                },
                {
                    'question': 'Is there a waiting period?',
                    'answer':   'No. Coverage begins the moment your first weekly premium is collected. Immediate protection.',
                },
            ],
            'Coverage & Claims': [
                {
                    'question': 'What triggers a claim?',
                    'answer':   'Six event types: Heavy Rain (>35mm/hr), Extreme Heat (>42°C), Severe AQI (>300), Flash Flood (IMD alert), Curfew/Strike (govt order), Platform Downtime (>30 minutes).',
                },
                {
                    'question': 'Do I need to file a claim manually?',
                    'answer':   'No. Zero action required from you. The entire pipeline — detection, claim creation, fraud check, payout — is fully automated.',
                },
                {
                    'question': 'How fast is the payout?',
                    'answer':   'Under 2 hours for auto-approved claims. Claims held for manual review may take up to 24 hours. You get a WhatsApp notification with UTR reference.',
                },
                {
                    'question': 'What if I was not in the affected zone?',
                    'answer':   'GPS zone validation is part of the AI pipeline. If your last location was outside the disruption zone, the claim is flagged for manual review.',
                },
                {
                    'question': 'Can I get multiple payouts in a week?',
                    'answer':   'Yes — one payout per qualifying disruption event. If two separate events occur in a week, each generates its own claim, up to your weekly coverage cap.',
                },
            ],
            'Plans & Payments': [
                {
                    'question': 'How does the weekly premium work?',
                    'answer':   'You set up a Razorpay Autopay mandate once during registration. Every Monday at midnight, the premium (₹29, ₹49, or ₹79) is auto-debited. No manual payment needed.',
                },
                {
                    'question': 'Can I change my plan?',
                    'answer':   'Yes, from your dashboard at any time. The new plan takes effect from the next Monday.',
                },
                {
                    'question': 'What happens if the auto-debit fails?',
                    'answer':   'You get a 48-hour grace period with WhatsApp reminders. After 2 failures, the policy pauses. You get 1 grace token per year for genuine bank failures.',
                },
                {
                    'question': 'Is my UPI ID safe?',
                    'answer':   'Yes. We store only your Razorpay contact ID and fund account ID — never the raw UPI string. All transactions go through Razorpay\'s PCI-DSS compliant infrastructure.',
                },
            ],
            'AI & Technology': [
                {
                    'question': 'How does the fraud detection work?',
                    'answer':   '6 layers: (1) Parametric gate — was there a verified event? (2) Duplicate prevention. (3) GPS zone check. (4) Isolation Forest ML score 0–1. (5) Score routing. (6) Nightly batch rescan at 2 AM.',
                },
                {
                    'question': 'What is dynamic risk pricing?',
                    'answer':   'Every Sunday, a trained XGBoost model recalculates your weekly premium using 44 features: your zone\'s disruption rate, your claim history, season, city risk multiplier, and more.',
                },
                {
                    'question': 'What is the weekly forecast?',
                    'answer':   'Every Sunday at 9 PM, 28 pre-trained Facebook Prophet models predict next week\'s rain, heat, AQI, and disruption probability for all 7 cities. Delivered to you via WhatsApp.',
                },
                {
                    'question': 'What is IncomeDNA?',
                    'answer':   'A cryptographically signed PDF that certifies your earnings history as a gig worker. Useful for bank loan applications and MSME credit access. Generated on request from your dashboard.',
                },
            ],
        }
        return render(request, self.template_name, {'grouped_faqs': grouped_faqs})


# ─── Blog ─────────────────────────────────────────────────────────────────────

class BlogView(View):
    template_name = 'core/blog.html'

    def get(self, request):
        from .models import BlogPost
        
        posts = BlogPost.objects.filter(published_at__isnull=False).select_related()[:6]
        
        # Fallback hardcoded posts if none exist in DB
        if not posts.exists():
            class FakePost:
                def __init__(self, title, category_display, author_name, date_str, excerpt, slug):
                    self.title = title
                    self.get_category_display = lambda: category_display
                    self.author_name = author_name  
                    self.date_str = date_str
                    self.excerpt = excerpt
                    self.slug = slug
                    self.cover_image = None
                    self.published_at = None
                    
            posts = [
                FakePost('How Parametric Insurance Protects Gig Workers', 'Education', 'Nexura Team', '10 Mar 2026', 
                        'Traditional insurance requires proof of loss...', 'how-parametric-insurance-works'),
                FakePost('Mumbai Monsoon 2025: How Nexura Paid ₹4.2 Crore', 'Case Study', 'Nexura Team', '28 Feb 2026',
                        'During the July 2025 Mumbai floods...', 'mumbai-monsoon-case-study'),
            ]
        
        return render(request, self.template_name, {'posts': posts})

        posts = [
            FakePost(
                title='How Parametric Insurance Protects Gig Workers',
                category_display='Education',
                author_name='Nexura Team',
                date_str='10 Mar 2026',
                excerpt='Traditional insurance requires proof of loss. Parametric insurance pays automatically when a pre-defined trigger occurs. Here\'s why this matters for India\'s 11 million delivery workers.',
                slug='how-parametric-insurance-works',
                fallback_img='blog-1.png',
            ),
            FakePost(
                title='Mumbai Monsoon 2025: How Nexura Paid ₹4.2 Crore',
                category_display='Case Study',
                author_name='Nexura Team',
                date_str='28 Feb 2026',
                excerpt='During the July 2025 Mumbai floods, 8,400 delivery workers received automatic payouts within 90 minutes. Here\'s how the system performed under real conditions.',
                slug='mumbai-monsoon-case-study',
                fallback_img='blog-2.png',
            ),
            FakePost(
                title='The IncomeDNA Report: Your Earnings, Certified',
                category_display='Product',
                author_name='Nexura Team',
                date_str='15 Feb 2026',
                excerpt='Gig workers are often denied bank loans because they lack income proof. IncomeDNA is a cryptographically RSA-signed PDF that certifies your earnings for credit applications.',
                slug='income-dna-report',
                fallback_img='blog-3.png',
            ),
        ]
        return render(request, self.template_name, {'posts': posts})


class BlogPostView(View):
    template_name = 'core/blog_post.html'

    def get(self, request, slug):
        from .models import BlogPost
        
        class FakePost:
            def __init__(self, title, category, category_display, author_name, published_at, excerpt, content, slug):
                self.title = title
                self.category = category
                self._category_display = category_display
                self.author_name = author_name
                self.published_at = published_at
                self.excerpt = excerpt
                self.content = content
                self.slug = slug
                self.cover_image = None
            def get_category_display(self):
                return self._category_display
        
        class RelatedFakePost:
            def __init__(self, title, category_display, author_name, excerpt, slug):
                self.title = title
                self._category_display = category_display
                self.author_name = author_name
                self.excerpt = excerpt
                self.slug = slug
            def get_category_display(self):
                return self._category_display
        
        post = BlogPost.objects.filter(slug=slug, published_at__isnull=False).first()
        
        fallback_posts = {
            'how-parametric-insurance-works': FakePost(
                title='How Parametric Insurance Protects Gig Workers',
                category='education',
                category_display='Education',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 3, 10, tzinfo=timezone.utc),
                excerpt="Traditional insurance requires proof of loss. Parametric insurance pays automatically when a pre-defined trigger occurs. Here's why this matters for India's 11 million delivery workers.",
                content="""What is Parametric Insurance?

Traditional insurance requires you to prove loss. Parametric insurance pays automatically when a pre-defined trigger is met — rain > 35mm/hr, temperature > 42°C, AQI > 300, etc.

Why Gig Workers Need It

11 million delivery workers lose income during disruptions. Manual claims take 7-14 days. Parametric payouts happen in <2 hours.

6 Triggers: Heavy Rain, Heatwave, Pollution, Floods, Curfew, Platform Downtime.

Nexura's Innovation
Zone-Precise: GPS validates your location
AI Fraud Check: 6-layer ML pipeline
Zero Paper: UPI direct, no forms

Sign up today. Protect your weekly earnings automatically.""",
                slug='how-parametric-insurance-works'
            ),
            'mumbai-monsoon-case-study': FakePost(
                title='Mumbai Monsoon 2025: How Nexura Paid ₹4.2 Crore',
                category='case-study',
                category_display='Case Study',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 2, 28, tzinfo=timezone.utc),
                excerpt="During the July 2025 Mumbai floods, 8,400 delivery workers received automatic payouts within 90 minutes. Here's how the system performed under real conditions.",
                content="""The Event: 120mm in 3 Hours

July 17, 2025, 4PM: IMD issues red alert. Mumbai receives 120mm in 3 hours. Zomato/Swiggy orders halt. 8,400 workers affected.

Nexura Response
Trigger Hit: Rainfall >35mm/hr in 12 zones
Claims Created: 8,400 auto-generated
Fraud Check: 94% passed AI gate (6 layers)
Payouts: ₹4.2 Cr via Razorpay UPI (<90 min avg)

Lessons Learned
Scale testing passed. ML models accurate. Zone validation prevented abuse.""",
                slug='mumbai-monsoon-case-study'
            ),
            'income-dna-report': FakePost(
                title='The IncomeDNA Report: Your Earnings, Certified',
                category='product',
                category_display='Product',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 2, 15, tzinfo=timezone.utc),
                excerpt="Gig workers are often denied bank loans because they lack income proof. IncomeDNA is a cryptographically RSA-signed PDF that certifies your earnings for credit applications.",
                content="""The Problem
Banks reject gig workers: "Show salary slips" — but Zomato/Swiggy give statements, not slips.

IncomeDNA Solution
6 Months Earnings: Total, monthly avg, peak day
RSA Signed PDF: Bank-verifiable, tamper-proof
Zero Cost: Generate anytime from dashboard
Loan Ready: HDFC, ICICI, MSME schemes accept

How to Get Yours
Dashboard → Reports → Generate IncomeDNA → Download PDF → Apply for loan.""",
                slug='income-dna-report'
            )
        }
        
        if not post:
            post = fallback_posts.get(slug)
        
        if not post:
            raise Http404("Blog post not found")
        
        # Related posts
        related = list(BlogPost.objects.filter(published_at__isnull=False).exclude(slug=slug)[:3])
        if len(related) == 0:
            other_slugs = ['mumbai-monsoon-case-study', 'income-dna-report', 'how-parametric-insurance-works']
            other_slugs = [s for s in other_slugs if s != slug][:3]
            related = [fallback_posts[s] for s in other_slugs]
        
        return render(request, self.template_name, {'post': post, 'related': related})
        
        class FakePost:
            def __init__(self, title, category_display, author_name, excerpt, slug):
                self.title = title
                self.get_category_display = lambda: category_display
                self.author_name = author_name
                self.excerpt = excerpt
                self.slug = slug
        
        # Related posts - fallback or query
        related = BlogPost.objects.filter(published_at__isnull=False).exclude(slug=slug)[:3]
        if related.count() == 0:
            related = [
                FakePost('Mumbai Monsoon 2025: How Nexura Paid ₹4.2 Crore', 'Case Study', 'Nexura Team', 'During the July 2025 Mumbai floods...', 'mumbai-monsoon-case-study'),
                FakePost('The IncomeDNA Report: Your Earnings, Certified', 'Product', 'Nexura Team', 'Gig workers are often denied bank loans...', 'income-dna-report'),
            ]
        
        return render(request, self.template_name, {'post': post, 'related': related})
        
        fallback_posts = {
            'how-parametric-insurance-works': FakePost(
                title='How Parametric Insurance Protects Gig Workers',
                category='education',
                category_display='Education',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 3, 10, tzinfo=timezone.utc),
                excerpt="Traditional insurance requires proof of loss. Parametric insurance pays automatically when a pre-defined trigger occurs. Here's why this matters for India's 11 million delivery workers.",
                content="""
<h2>What is Parametric Insurance?</h2>
<p>Traditional insurance requires you to prove loss. Parametric insurance pays automatically when a pre-defined trigger is met — rain > 35mm/hr, temperature > 42°C, AQI > 300, etc.</p>

<h2>Why Gig Workers Need It</h2>
<p>11 million delivery workers lose income during disruptions. Manual claims take 7-14 days. Parametric payouts happen in <2 hours.</p>

<p><strong>6 Triggers:</strong> Heavy Rain, Heatwave, Pollution, Floods, Curfew, Platform Downtime.</p>

<h2>Nexura's Innovation</h2>
<ul>
<li><strong>Zone-Precise:</strong> GPS validates your location</li>
<li><strong>AI Fraud Check:</strong> 6-layer ML pipeline</li>
<li><strong>Zero Paper:</strong> UPI direct, no forms</li>
</ul>

<p>Sign up today. Protect your weekly earnings automatically.</p>
""",
                slug=slug
            ),
            'mumbai-monsoon-case-study': FakePost(
                title='Mumbai Monsoon 2025: How Nexura Paid ₹4.2 Crore',
                category='case-study',
                category_display='Case Study',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 2, 28, tzinfo=timezone.utc),
                excerpt="During the July 2025 Mumbai floods, 8,400 delivery workers received automatic payouts within 90 minutes. Here's how the system performed under real conditions.",
                content="""
<h2>The Event: 120mm in 3 Hours</h2>
<p>July 17, 2025, 4PM: IMD issues red alert. Mumbai receives 120mm in 3 hours. Zomato/Swiggy orders halt. 8,400 workers affected.</p>

<h2>Nexura Response</h2>
<ul>
<li><strong>Trigger Hit:</strong> Rainfall >35mm/hr in 12 zones</li>
<li><strong>Claims Created:</strong> 8,400 auto-generated</li>
<li><strong>Fraud Check:</strong> 94% passed AI gate (6 layers)</li>
<li><strong>Payouts:</strong> ₹4.2 Cr via Razorpay UPI (<90 min avg)</li>
</ul>

<h2>Lessons Learned</h2>
<p>Scale testing passed. ML models accurate. Zone validation prevented abuse.</p>
""",
                slug=slug
            ),
            'income-dna-report': FakePost(
                title='The IncomeDNA Report: Your Earnings, Certified',
                category='product',
                category_display='Product',
                author_name='Nexura Team',
                published_at=timezone.datetime(2026, 2, 15, tzinfo=timezone.utc),
                excerpt="Gig workers are often denied bank loans because they lack income proof. IncomeDNA is a cryptographically RSA-signed PDF that certifies your earnings for credit applications.",
                content="""
<h2>The Problem</h2>
<p>Banks reject gig workers: "Show salary slips" — but Zomato/Swiggy give statements, not slips.</p>

<h2>IncomeDNA Solution</h2>
<ul>
<li><strong>6 Months Earnings:</strong> Total, monthly avg, peak day</li>
<li><strong>RSA Signed PDF:</strong> Bank-verifiable, tamper-proof</li>
<li><strong>Zero Cost:</strong> Generate anytime from dashboard</li>
<li><strong>Loan Ready:</strong> HDFC, ICICI, MSME schemes accept</li>
</ul>

<h2>How to Get Yours</h2>
<p>Dashboard → Reports → Generate IncomeDNA → Download PDF → Apply for loan.</p>
""",
                slug=slug
            )
        }
        post = fallback_posts.get(slug)
        if not post:
            raise Http404("Blog post not found")
        
        # Related posts
        related = []
        other_slugs = [s for s in fallback_posts if s != slug][:3]
        for s in other_slugs:
            fp = fallback_posts[s]
            related.append(fp)
        
        return render(request, self.template_name, {'post': post, 'related': related})


# ─── Contact ──────────────────────────────────────────────────────────────────

class ContactView(View):
    template_name = 'core/contact.html'

    def get(self, request):
        ctx = {
            'offices': [
                {
                    'city':    'Headquarters — Vadodara',
                    'address': 'Parul University, Waghodia Road, Vadodara, Gujarat 391760',
                    'icon':    'fas fa-map-marker-alt',
                },
            ],
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        name    = request.POST.get('full_name', '').strip()
        email   = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not all([name, email, subject, message]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, self.template_name, {'offices': []})

        from .models import ContactMessage
        ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
        # TODO Step 16: send email via SendGrid
        logger.info('Contact form: %s (%s) — %s', name, email, subject)
        messages.success(
            request,
            f'Thank you {name}! We\'ve received your message and will reply within 24 hours.',
        )
        return redirect('core:contact')


# ─── Cities ───────────────────────────────────────────────────────────────────

class CitiesView(View):
    template_name = 'core/cities.html'

    def get(self, request):
        # Template uses: city.name, city.state, city.description, city.zones (count int),
        #                city.color (Bootstrap color name), city.icon
        cities = [
            {
                'name':        'Mumbai',
                'state':       'Maharashtra',
                'description': 'Highest monsoon disruption risk. Frequent coastal flooding, Kal Baisakhi storms, and AQI spikes post-Diwali.',
                'zones':       12,
                'color':       'primary',
                'icon':        'fas fa-cloud-showers-heavy',
            },
            {
                'name':        'Delhi',
                'state':       'Delhi NCR',
                'description': 'Extreme summer heat (45°C+), severe winter AQI events (AQI 400+), and occasional curfew disruptions.',
                'zones':       14,
                'color':       'danger',
                'icon':        'fas fa-thermometer-full',
            },
            {
                'name':        'Bangalore',
                'state':       'Karnataka',
                'description': 'Unseasonal heavy rain and flash flooding in low-lying areas. Platform downtime common during peak traffic.',
                'zones':       10,
                'color':       'success',
                'icon':        'fas fa-water',
            },
            {
                'name':        'Chennai',
                'state':       'Tamil Nadu',
                'description': 'Cyclone season flooding and extreme coastal weather. Northeast monsoon (Oct–Dec) is the highest-risk period.',
                'zones':       9,
                'color':       'info',
                'icon':        'fas fa-wind',
            },
            {
                'name':        'Hyderabad',
                'state':       'Telangana',
                'description': 'Heavy rainfall causing urban flooding in Hussain Sagar catchment areas during monsoon months.',
                'zones':       8,
                'color':       'warning',
                'icon':        'fas fa-smog',
            },
            {
                'name':        'Kolkata',
                'state':       'West Bengal',
                'description': 'Pre-monsoon thunderstorms (Kal Baisakhi) and post-monsoon cyclone risks from Bay of Bengal.',
                'zones':       9,
                'color':       'primary',
                'icon':        'fas fa-cloud-bolt',
            },
            {
                'name':        'Pune',
                'state':       'Maharashtra',
                'description': 'Ghat road flooding and heavy monsoon disruptions in eastern zones. High platform downtime risk.',
                'zones':       8,
                'color':       'success',
                'icon':        'fas fa-mountain',
            },
        ]
        total_zones = sum(c['zones'] for c in cities)
        return render(request, self.template_name, {
            'cities':      cities,
            'total_zones': total_zones,
        })


# ─── Privacy & Terms ──────────────────────────────────────────────────────────

class PrivacyView(View):
    template_name = 'core/privacy.html'

    def get(self, request):
        return render(request, self.template_name)


class TermsView(View):
    template_name = 'core/terms.html'

    def get(self, request):
        return render(request, self.template_name)


# ─── 404 / 500 handlers ───────────────────────────────────────────────────────

def custom_404(request, exception):
    return render(request, 'core/404.html', status=404)


def custom_500(request):
    return render(request, 'core/500.html', status=500)


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthCheckView(View):
    def get(self, request):
        from django.db import connection
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False

        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 5)
            redis_ok = cache.get('health_check') == 'ok'
        except Exception:
            redis_ok = False

        # ── Celery worker check ───────────────────────────────────────
        celery_ok = False
        try:
            from nexura.celery import app as celery_app
            inspect = celery_app.control.inspect(timeout=2.0)
            ping_result = inspect.ping()
            celery_ok = bool(ping_result)  # Non-empty dict means workers responded
        except Exception as exc:
            logger.warning("[HealthCheck] Celery ping failed: %s", exc)
            celery_ok = False

        all_ok = db_ok and redis_ok and celery_ok
        status = 'ok' if all_ok else 'degraded'
        return JsonResponse({
            'status':  status,
            'db':      'ok' if db_ok     else 'error',
            'cache':   'ok' if redis_ok  else 'error',
            'celery':  'ok' if celery_ok else 'error',
            'app':     'nexura',
            'version': '1.0.0',
        }, status=200 if status == 'ok' else 503)

# ─── Support Tickets ──────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def support_list(request):
    """Worker support ticket list + new ticket form."""
    if not request.user.is_worker and not (request.user.is_admin or request.user.is_staff):
        return redirect('core:home')

    from .models import SupportTicket

    if request.method == 'POST':
        category    = request.POST.get('category', 'other')
        subject     = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        if not subject or not description:
            messages.error(request, 'Subject and description are required.')
        else:
            SupportTicket.objects.create(
                worker=request.user, category=category,
                subject=subject, description=description,
            )
            messages.success(request, '✅ Ticket raised! Our team will respond within 24 hours.')
            return redirect('core:support')

    tickets = SupportTicket.objects.filter(worker=request.user)
    return render(request, 'core/support.html', {
        'tickets':    tickets,
        'categories': SupportTicket.CATEGORY_CHOICES,
    })
