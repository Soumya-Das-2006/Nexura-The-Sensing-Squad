<div align="center">

<img src="https://img.shields.io/badge/🛡️-Nexura-015fc9?style=for-the-badge&labelColor=0f172a&color=015fc9" alt="Nexura" height="40"/>

# 🛡️ Nexura — GigShield

### AI-Powered Parametric Income Protection for India's Gig Economy

---

## ⚡ TL;DR

- Gig workers lose daily income when weather shocks or platform outages hit, and traditional insurance is too slow to help.
- Nexura is AI-powered parametric insurance that auto-detects disruptions and auto-files claims with zero paperwork.
- A Django + Celery real-time pipeline runs trigger checks and fraud scoring to approve valid claims fast.
- Approved claims are sent directly as UPI payouts, with instant multilingual WhatsApp updates.
- Outcome: near-instant financial protection at scale for India's gig economy.

---
<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-FF6600?style=flat-square)](https://xgboost.ai)
[![Prophet](https://img.shields.io/badge/Prophet-Forecast-blue?style=flat-square)](https://facebook.github.io/prophet)
[![Razorpay](https://img.shields.io/badge/Razorpay-Payments-072654?style=flat-square&logo=razorpay)](https://razorpay.com)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366?style=flat-square&logo=whatsapp&logoColor=white)](https://developers.facebook.com/docs/whatsapp)
[![Status](https://img.shields.io/badge/Status-Hackathon%20Prototype-f97316?style=flat-square)](/)
[![Guidewire](https://img.shields.io/badge/Guidewire-DEVTrails%202026-7c3aed?style=flat-square)](https://devtrails.guidewire.com)

<br/>

> **Disruption detected → Auto-claim filed → AI fraud check → UPI payout in < 2 hours**
>
> *Protecting India's 11M+ gig delivery workers — one delivery at a time.*

<br/>

[🚀 Live Demo](#-installation--setup) · [📖 Docs](#-api-reference) · [🐛 Report Bug](https://github.com/Soumya-Das-2006/-Nexura-The-Sensing-Squad/issues) · [💡 Request Feature](https://github.com/Soumya-Das-2006/-Nexura-The-Sensing-Squad/issues) · [🤝 Contribute](./CONTRIBUTING.md)

</div>

---

## 📖 Table of Contents

1. [Inspiration](#-inspiration)
2. [Why This Matters](#-why-this-matters)
3. [What It Does](#-what-it-does)
4. [How We Built It](#-how-we-built-it)
5. [System Architecture](#-system-architecture)
6. [AI & ML Pipeline](#-ai--ml-pipeline)
7. [Parametric Trigger System](#-parametric-trigger-system)
8. [Payout Pipeline](#-payout-pipeline)
9. [Weekly Premium Plans](#-weekly-premium-plans)
10. [Key Features](#-key-features)
11. [Tech Stack](#-tech-stack)
12. [Project Structure](#-project-structure)
13. [Installation & Setup](#-installation--setup)
14. [How to Use](#-how-to-use)
15. [API Reference](#-api-reference)
16. [Challenges We Ran Into](#-challenges-we-ran-into)
17. [Accomplishments We're Proud Of](#-accomplishments-were-proud-of)
18. [What We Learned](#-what-we-learned)
19. [What's Next for Nexura](#-whats-next-for-Nexura)
20. [Team & Credits](#-team--credits)
21. [Contributing](#-contributing)
22. [License](#-license)

---

## 💡 Inspiration

India's gig economy is one of the fastest-growing in the world — yet the **11 million+ delivery workers** powering platforms like Zomato, Swiggy, Amazon Flex, Zepto, and Blinkit have **zero income protection**.

A single monsoon rainstorm can wipe out an entire day's earnings. An extreme heat wave in Delhi keeps riders off the road for hours. Platform outages mean orders disappear mid-shift. These aren't rare edge cases — **they happen every week, in every city.**

Traditional insurance is designed for the formal economy. It requires documentation, physical verification, and weeks of processing — completely inaccessible to daily earners who need help *now*, not in a month.

> **We asked: what if insurance worked like a smoke detector — not waiting for you to file a report, but automatically responding the moment danger is detected?**

That's Nexura. Parametric insurance meets AI automation, built specifically for India's gig workers.

---

## 🎯 Why This Matters

For gig workers, a lost shift is not an inconvenience, it is lost food, rent, and stability.

When heavy rain, extreme heat, or platform outages stop deliveries, income drops instantly while expenses do not. Most protection systems are too slow, too complex, or too far removed from daily reality.

Nexura exists to close that gap: detect disruption in real time, trigger support automatically, and deliver fast payouts when workers need them most.
Because financial protection should move at the speed of risk, not paperwork.

---

## ⚡ What It Does

Nexura is a **zero-touch parametric income protection platform**. Workers pay a small weekly premium (₹29–₹79) and receive automatic UPI payouts whenever predefined real-world disruptions hit their delivery zone — with no paperwork, no waiting, and no manual claim filing.

### The Worker Experience

```
Monday 8 AM  →  Weekly ₹49 premium auto-debited via Razorpay Autopay
Wednesday 2 PM  →  Heavy rain (42mm/hr) detected in Dadar zone
                    ↓  Celery task fires instantly
                    ↓  Claim auto-created for all active policyholders in zone
                    ↓  6-layer AI fraud pipeline runs (< 200ms)
                    ↓  Score 0.18 → Auto-approved
Wednesday 2:47 PM  →  ₹1,000 credited to UPI (ravi.kumar@oksbi)
                    ↓  WhatsApp: "💸 ₹1,000 credited. UTR: Nexura4B2F9A1C7E"
```

### Platform Overview

| Stakeholder | Experience |
|---|---|
| **Worker** | Register → KYC → Choose plan → Forget about it. Money arrives automatically. |
| **Admin** | Monitor triggers, review fraud flags, manage payouts from a custom ops dashboard. |
| **API Consumer** | Full REST API for zone forecasts, risk scores, claims, and payout status. |

---

## 🏗️ How We Built It

Nexura is a full-stack Django application with a Python ML layer, built in 20 discrete development steps.

### Development Approach

We broke the build into 20 atomic steps — each delivering a self-contained, deployable piece:

| Steps | Phase |
|---|---|
| 1–3 | Django project setup, static files, base templates |
| 4–9 | Core apps: accounts, workers, policies, triggers, zones |
| 10–12 | Claims pipeline, payouts, payments & webhooks |
| 13–16 | ML apps: fraud detection, pricing, forecasting, notifications |
| 17 | Circles, documents (IncomeDNA), admin portal |
| 18–20 | Docker, migrations, production config |

### Core Design Decisions

- **Django monolith over microservices** — faster to build, easier to demo, Celery handles async
- **Parametric over indemnity** — no loss assessment, triggers are binary and verifiable
- **ML inference on the fly** — models loaded once per Celery worker process, cached in memory
- **Sandbox-first design** — every external API (Razorpay, WhatsApp, OpenWeatherMap) has a mock fallback so the full pipeline runs locally without any API keys

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Nexura PLATFORM                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    WORKER INTERFACES                        │    │
│  │   Web App (Django)  ·  WhatsApp Bot  ·  Mobile Dashboard    │    │
│  └───────────────────────────┬─────────────────────────────────┘    │
│                              │ HTTPS                                │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │                   DJANGO REST API LAYER                     │    │
│  │                                                             │    │
│  │  /api/v1/accounts/   /api/v1/workers/   /api/v1/policies/   │    │
│  │  /api/v1/claims/     /api/v1/payouts/   /api/v1/payments/   │    │
│  │  /api/v1/pricing/    /api/v1/forecasting/ /api/v1/admin/    │    │
│  └───────┬───────────────────┬────────────────────┬────────────┘    │
│          │                   │                    │                 │
│  ┌───────▼──────┐  ┌─────────▼──────┐  ┌──────────▼──────────┐      │
│  │  POSTGRESQL  │  │  REDIS BROKER  │  │   AI/ML PIPELINE    │      │
│  │  Database    │  │  Task Queue    │  │                     │      │
│  │              │  │                │  │  fraud_iso_forest   │      │
│  │  73 zones    │  │  Celery Beat   │  │  fraud_xgboost      │      │
│  │  Policies    │  │  (8 scheduled  │  │  risk_model (XGB)   │      │
│  │  Claims      │  │   tasks)       │  │  27 Prophet models  │      │
│  │  Payouts     │  │                │  │                     │      │
│  └──────────────┘  └────────┬───────┘  └─────────────────────┘      │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                    CELERY WORKERS                            │   │
│  │                                                              │   │
│  │  poll_weather_all_zones   (every 15 min)                     │   │
│  │  poll_aqi_all_zones       (every 30 min)                     │   │
│  │  poll_platform_uptime     (every 10 min)                     │   │
│  │  process_pending_claims   (every 5 min)                      │   │
│  │  generate_zone_forecasts  (Sunday 8:30 PM)                   │   │
│  │  recalculate_all_premiums (Sunday 8:00 PM)                   │   │
│  │  collect_weekly_premiums  (Monday 12:01 AM)                  │   │
│  │  daily_batch_fraud_scan   (daily 2:00 AM)                    │   │
│  └───────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐   │
│  │                     EXTERNAL APIs                            │   │
│  │                                                              │   │
│  │  OpenWeatherMap  ·  WAQI (AQI)  ·  Razorpay (Pay + Payouts)  │   │
│  │  Meta WhatsApp Cloud API  ·  SendGrid  ·  Twilio (OTP)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI & ML Pipeline

Nexura runs three separate ML models, each loaded once per Celery process and cached in memory.

### Pipeline Overview

```
                 New DisruptionEvent created
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│              CLAIM GENERATION PIPELINE                    │
│                                                           │
│  1. Find all active policyholders in affected zone        │
│  2. Create Claim record (status = pending)                │
│  3. Run 6-Layer Fraud Pipeline                            │
│                                                           │
│  LAYER 1 ─ Parametric Gate                                │
│    Is there a verified DisruptionEvent? → Pass / Reject   │
│                                                           │
│  LAYER 2 ─ Duplicate Prevention                           │
│    unique_together(worker, event) check → Pass / Reject   │
│                                                           │
│  LAYER 3 ─ GPS Zone Validation                            │
│    Haversine distance: worker zone vs event zone          │
│    < 5 km → +0.15   5–15 km → +0.30   > 15 km → +0.50     │
│                                                           │
│  LAYER 4 ─ ML Score                                       │
│    IsolationForest (200 estimators, 5% contamination)     │
│    XGBClassifier (binary: fraud / not fraud)              │
│    34 features: claim velocity, GPS, KYC, zone density    │
│    Ensemble: 60% XGB + 40% ISO Forest                     │
│                                                           │
│  LAYER 5 ─ Score Routing                                  │
│    < 0.50 → Auto-Approve → Queue Payout                   │
│    0.50–0.70 → Hold → Admin Review                        │
│    > 0.70 → Auto-Reject → Notify Worker                   │
│                                                           │
│  LAYER 6 ─ Nightly Batch Rescan (2 AM daily)              │
│    Re-score all approved claims from last 7 days          │
│    If now ≥ 0.70 → Reverse payout if < 24h old            │
└───────────────────────────────────────────────────────────┘
                              │
                              ▼ (if approved)
┌───────────────────────────────────────────────────────────┐
│                  PAYOUT PIPELINE                          │
│                                                           │
│  Razorpay Contact → Fund Account → Payouts API            │
│  Sandbox: fake UTR generated instantly                    │
│  Real: webhook confirms credit → UTR stored               │
└───────────────────────────────────────────────────────────┘
```

### Model Details

| Model | Algorithm | Purpose | Features |
|---|---|---|---|
| `fraud_iso_forest.pkl` | IsolationForest (sklearn) | Anomaly detection | 34 features, 200 estimators, 5% contamination |
| `fraud_xgboost.json` | XGBClassifier | Fraud probability | Same 34 features, binary classification |
| `risk_model.pkl` | XGBoost + IsotonicCalibration | Dynamic premium pricing | 44 features: zone risk, season, claim history, weather |
| `prophet_{city}_{metric}.pkl` | Facebook Prophet | Disruption forecasting | 27 models: 7 cities × 4 metrics (rain/heat/AQI/disruption) |

### Pricing Formula

```
Risk Score → XGBoost pipeline → disruption_probability [0.0–1.0]

raw_premium  = ₹150 × (1 + risk_score × 2.0)
final_premium = clamp(raw_premium, plan_base × 0.80, plan_base × 1.50)

Example (Standard Shield, ₹49 base):
  risk = 0.0 → ₹39/week  (minimum)
  risk = 0.5 → ₹49/week  (standard)
  risk = 1.0 → ₹74/week  (maximum)
```

---

## 🌧️ Parametric Trigger System

Payouts fire automatically when **any** of these conditions are met in a worker's registered zone:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRIGGER THRESHOLDS                           │
├──────────────────────┬──────────────────┬───────────────────────┤
│ Trigger Type         │ Full Payout      │ Partial Payout (50%)  │
├──────────────────────┼──────────────────┼───────────────────────┤
│ 🌧️ Heavy Rainfall    │ > 35 mm/hr       │ 20–35 mm/hr           │
│ 🌡️ Extreme Heat      │ > 42 °C          │ 38–42 °C              │
│ 🌫️ Severe AQI        │ > 300 (AQI)      │ 200–300 (AQI)         │
│ 🌊 Flash Flood       │ Alert issued     │ —                     │
│ 🚫 Curfew / Strike   │ Official notice  │ —                     │
│ 📵 Platform Downtime │ > 30 minutes     │ 15–30 minutes         │
└──────────────────────┴──────────────────┴───────────────────────┘

Data Sources:
        Weather + Heat  →  OpenWeatherMap API   (every 15 min)
        AQI             →  WAQI / CPCB API      (every 30 min)
        Platform        →  Nexura Uptime Mon.  (every 10 min)
        Flood / Curfew  →  Manual or IMD API    (admin trigger)
```

---

## 🔄 Payout Pipeline

```
DisruptionEvent.is_full_trigger = True
        │
        ▼
process_pending_claims (Celery, every 5 min)
        │
        ├─── For each active policy in zone:
        │    1. Create Claim (pending)
        │    2. Run 6-Layer Fraud Pipeline
        │    3. Decision: approve / hold / reject
        │
        ▼ (approved)
disburse_payout (Celery, immediate)
        │
        ├─── ensure_contact(worker)  →  Razorpay Contact ID
        ├─── ensure_fund_account()   →  Razorpay Fund Acct ID (UPI)
        └─── create_payout()         →  Razorpay Payouts API
        │
        ▼
Razorpay webhook: payout.processed
        │
        ▼
Payout.mark_credited(utr=...)
        │
        ▼
WhatsApp: "💸 ₹1,000 credited. UTR: Nexura4B2F9..."
        │
        ▼
⏱️ Total time: < 2 hours from trigger detection

Reconciliation:   every 10 min (reconcile_payouts)
Retry on failure: every 1 hour (retry_failed_payouts, max 3 attempts)
```

---

## 💰 Weekly Premium Plans

| | 🥉 Basic Shield | ⭐ Standard Shield | 🥇 Premium Shield |
|---|:---:|:---:|:---:|
| **Weekly Premium** | ₹29 | ₹49 | ₹79 |
| **Weekly Coverage** | ₹500 | ₹1,000 | ₹2,000 |
| All 6 trigger types | ✅ | ✅ | ✅ |
| Zero-touch auto-claim | ✅ | ✅ | ✅ |
| UPI payout < 2 hrs | ✅ | ✅ | ✅ |
| WhatsApp alerts | ✅ | ✅ | ✅ |
| Weekly risk forecast | ❌ | ✅ | ✅ |
| Risk Circle access | ❌ | ✅ | ✅ |
| Email alerts | ❌ | ❌ | ✅ |
| IncomeDNA PDF | ❌ | ❌ | ✅ |
| Dynamic risk pricing | ❌ | ❌ | ✅ |
| Priority support | ❌ | ❌ | ✅ |

> **Partial trigger** (20–35mm rain, 38–42°C heat, 200–300 AQI, 15–30 min outage) → 50% payout

---

## ✨ Key Features

### 🔐 Worker Onboarding
- Mobile OTP registration (6-digit, 30s countdown, paste support)
- Aadhaar KYC with PBKDF2-HMAC-SHA256 hashing (no plaintext storage)
- Zone selection grouped by city (73 zones, 7 cities)
- UPI ID setup with instant validation

### 📡 Real-Time Monitoring
- OpenWeatherMap polling every 15 minutes per zone
- WAQI AQI API every 30 minutes
- Custom platform uptime monitor every 10 minutes (pings 6 platform URLs)
- Fire test triggers via management command: `python manage.py fire_trigger --zone 4 --type heavy_rain`

### 🤖 Zero-Touch Claims
- Claims auto-generated the moment a trigger fires
- 6-layer fraud pipeline runs in < 200ms
- Auto-approve or auto-reject based on ML score
- Borderline claims held for admin review with full audit trail

### 💳 Razorpay Integration
- Autopay subscriptions for weekly premium collection
- Payouts API for direct UPI transfer (contact + fund account flow)
- Full webhook handler for subscription events and payout status
- Sandbox mode: complete simulation without API keys

### 📊 AI Risk Pricing
- XGBoost + Isotonic Calibration pipeline
- 44 features: zone risk, monsoon season, claim history, platform, city tier
- Recalculated every Sunday at 8 PM
- Clamped to ±50% of advertised plan rate

### 🌦️ Prophet Forecasting
- 27 Facebook Prophet models (7 cities × 4 metrics)
- Predicts next week's rain/heat/AQI/disruption probability
- Shown in worker dashboard as probability bars
- Weekly alerts to workers in Moderate+ risk zones

### 📄 IncomeDNA Reports
- ReportLab PDF with worker identity, payout history, UTR references
- HMAC-SHA256 signed (RSA in production)
- Accepted by partner lenders as income proof for MSME credit

### 🌐 Multilingual Notifications
- WhatsApp messages in 6 languages: English, Hindi, Marathi, Tamil, Telugu, Bengali
- SendGrid email with branded HTML templates
- Notification types: claim approved/rejected/on_hold, payout credited/failed, forecast alert, premium update

### 🏦 Risk Circles
- Voluntary groups of up to 20 workers in the same zone
- Pool contributions supplement payouts in high-disruption weeks
- Admin-seeded seed pool balances

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology | Version |
|---|---|---|
| Framework | Django + DRF | 4.2 |
| Database | PostgreSQL | 15 |
| Cache / Broker | Redis | 7.0 |
| Task Queue | Celery | 5.3 |
| Authentication | JWT (SimpleJWT) | — |
| PDF Generation | ReportLab | 4.0 |

### AI / ML
| Model | Library | Purpose |
|---|---|---|
| Fraud Detection | scikit-learn IsolationForest | Anomaly scoring |
| Fraud Classification | XGBoost | Binary fraud probability |
| Risk Pricing | XGBoost + Isotonic Calibration | Dynamic premium |
| Disruption Forecast | Facebook Prophet | 7-city weekly forecast |

### Integrations
| Service | Purpose |
|---|---|
| OpenWeatherMap | Real-time weather per zone |
| WAQI / CPCB | Air Quality Index |
| Razorpay | Autopay subscriptions + UPI Payouts |
| Meta WhatsApp Cloud API | Worker notifications |
| SendGrid | Transactional email |
| Twilio | OTP SMS fallback |
| DigiLocker | Aadhaar KYC (planned) |

### Frontend
| Layer | Technology |
|---|---|
| Templates | Django Templates (Jinja2-compatible) |
| CSS Framework | Bootstrap 5 + Custom Nexura Design System |
| Animations | WOW.js + Animate.css |
| Carousel | OWL Carousel 2 |
| Charts | Chart.js |
| JS | jQuery + Nexura.js |

---

## 📁 Project Structure

```
Nexura/
├── apps/
│   ├── accounts/          # User auth, OTP, KYC
│   ├── admin_portal/      # Custom ops dashboard
│   ├── circles/           # Risk circles
│   ├── claims/            # Claim model + 6-layer fraud pipeline
│   ├── core/              # Public site views
│   ├── documents/         # IncomeDNA PDF generator
│   ├── forecasting/       # Prophet forecast model + ZoneForecast
│   ├── fraud/             # Standalone fraud service + FraudFlag model
│   ├── notifications/     # WhatsApp + Email + SMS channels
│   ├── payments/          # PremiumPayment + Razorpay webhook
│   ├── payouts/           # Payout model + Razorpay Payouts API
│   ├── policies/          # PlanTier + Policy
│   ├── pricing/           # XGBoost risk pricing
│   ├── triggers/          # DisruptionEvent + polling tasks
│   ├── workers/           # WorkerProfile
│   └── zones/             # Zone model
├── fixtures/
│   ├── zones.json          # 73 delivery zones, 7 cities
│   ├── plans.json          # 3 plan tiers
│   ├── risk_circles.json   # 14 circles
│   ├── demo_*.json         # Demo users, claims, payouts, events
│   └── load_all.sh         # One-shot fixture loader
├── ml_models/
│   ├── fraud_iso_forest.pkl
│   ├── fraud_xgboost.json
│   ├── fraud_feature_cols.csv   # 34 feature names
│   ├── iso_norm_params.csv
│   ├── risk_model.pkl
│   ├── risk_model_xgb.json
│   ├── feature_list.json        # 44 feature names
│   ├── model_metadata.json
│   └── prophet/
│       └── prophet_{city}_{metric}.pkl   # 27 models
├── Nexura/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── celery.py
│   └── urls.py
├── static/
│   ├── css/style.css      # Full Nexura design system (418 lines)
│   ├── js/Nexura.js       # Client JS
│   └── lib/               # OWL Carousel, Lightbox, WOW, etc.
├── templates/             # 47 Django templates
│   ├── base.html
│   ├── base_dashboard.html
│   ├── base_admin.html
│   ├── includes/
│   ├── core/              # Public pages
│   ├── accounts/          # Auth (3-step register, 2-step login)
│   ├── workers/           # Dashboard + account
│   ├── policies/          # Plans, select, my_policy
│   ├── claims/            # my_claims, claim_detail
│   ├── payouts/           # History
│   ├── payments/          # Premium history
│   ├── forecasting/       # Zone forecast
│   ├── pricing/           # Calculator
│   ├── circles/           # My circle
│   ├── documents/         # IncomeDNA
│   └── admin_portal/      # 8 admin views
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

---
# 🚀 Installation & Setup

## 📦 Prerequisites

Make sure you have the following installed:

- Python **3.10+**
- PostgreSQL **15+**
- Redis **7.0+**
- Docker & Docker Compose *(recommended)*

---

## 🐳 Option A: Docker (Recommended)

### 1. Clone the Repository
```bash
git clone https://github.com/Soumya-Das-2006/Nexura-The-Sensing-Squad.git
cd Nexura-The-Sensing-Squad
````

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
SECRET_KEY=your-secret-key
DB_NAME=nexura_db
DB_USER=postgres
DB_PASSWORD=postgres
```

---

### 3. Build & Start Services

```bash
docker-compose up --build
```

---

### 4. Load Seed Data

```bash
docker-compose exec web bash fixtures/load_all.sh
```

---

### 5. Run the App

Open your browser:

```
http://localhost:8000
```

---

## 💻 Option B: Local Development

### 1. Clone & Setup Virtual Environment

```bash
git clone https://github.com/your-team/Nexura.git
cd Nexura

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

---

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Configure Environment

```bash
cp .env.example .env
```

Update `.env` with your credentials.

---

### 4. Setup PostgreSQL

```bash
createdb nexura_db
python manage.py migrate
```

---

### 5. Load Fixtures

```bash
bash fixtures/load_all.sh
```

---

### 6. Start Services (Run in Separate Terminals)

**Terminal 1 – Redis**

```bash
redis-server
```

**Terminal 2 – Celery Worker**

```bash
celery -A nexura worker -l info
```

**Terminal 3 – Celery Beat**

```bash
celery -A nexura beat -l info
```

**Terminal 4 – Django Server**

```bash
python manage.py runserver
```

---

## ⚙️ Environment Variables

```env
# Core
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=nexura_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis / Celery
REDIS_URL=redis://localhost:6379/0

# Razorpay (leave blank for sandbox mode)
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_ACCOUNT_NUMBER=

# WhatsApp Cloud API (leave blank for mock mode)
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_VERIFY_TOKEN=nexura_webhook_verify

# Email
SENDGRID_API_KEY=
DEFAULT_FROM_EMAIL=noreply@nexura.in

# Weather APIs (leave blank for mock data)
OPENWEATHERMAP_API_KEY=
WAQI_API_KEY=
```

---

> **Sandbox mode:** When API keys are empty, Nexura uses realistic mock data for weather, AQI, Razorpay, and WhatsApp. The full pipeline runs end-to-end without any external dependencies.

### Access Points

| Service | URL |
|---|---|
| Public Site | `http://localhost:8000/` |
| Worker Dashboard | `http://localhost:8000/dashboard/` |
| Admin Portal | `http://localhost:8000/admin-portal/` |
| Django Admin | `http://localhost:8000/django-admin/` |
| REST API Root | `http://localhost:8000/api/v1/` |
| Health Check | `http://localhost:8000/health/` |

### Multi-language translation (UI)

- Language switching is handled by `static/js/translator.js` and the shared switcher partial at `templates/includes/_language_switcher.html`.
- The UI translation API endpoint is `POST /translate/` (`apps/core/translation_views.py`) and is wired via `data-translate-endpoint` in `templates/base.html`.
- To add or edit supported UI languages, update the `LANGUAGES` list in `static/js/translator.js` and keep `SUPPORTED_LANGS` in `apps/core/translation_views.py` aligned.
- Worker notification language choices are defined in `apps/accounts/models.py` (`User.LANGUAGE_CHOICES`) and are used in registration/account forms.
- Fallback behavior:
  - Unsupported/invalid saved language defaults to `en`.
  - Translation provider failures return original text gracefully.

### Demo Credentials

| Role | Mobile | Password |
|---|---|---|
| Admin | `9000000000` | `Nexura@demo123` |
| Worker (Mumbai) | `9876543210` | `Nexura@demo123` |
| Worker (Bangalore) | `9123456780` | `Nexura@demo123` |
| Worker (Hyderabad) | `9988776655` | `Nexura@demo123` |

---

## 📲 How to Use

### For Workers

1. **Register** at `/register/` using your mobile number (OTP verification)
2. **Verify KYC** — submit Aadhaar number (PBKDF2-HMAC-SHA256 hashed, never stored plaintext)
3. **Set up profile** — choose delivery platform, city, zone, and UPI ID
4. **Select a plan** — Basic ₹29 / Standard ₹49 / Premium ₹79 per week
5. **Activate via Razorpay** — Autopay mandate set up once, deducted every Monday
6. **That's it** — claims fire automatically when disruptions hit your zone

**When a disruption occurs:**
- ✅ System detects the event via API polling
- ✅ Claim auto-created — you never need to do anything
- ✅ AI fraud pipeline runs in < 200ms
- ✅ UPI transfer initiated immediately on approval
- ✅ WhatsApp notification with UTR reference

### For Admins

1. Login at `/admin-portal/` (requires `is_admin=True`)
2. **Dashboard** — live KPIs: workers, active policies, pending claims, total paid out
3. **Triggers** — view disruption event log, fire test triggers
4. **Claims** — review on-hold claims, approve or reject with reason
5. **Payouts** — track UPI transfer status, retry failed payouts
6. **Fraud Queue** — claims scored 0.50–0.70 requiring manual review
7. **Forecast** — view Prophet predictions for all 7 cities, regenerate on demand
8. **Workers** — search/filter workers, recalculate XGBoost risk scores

### Fire a Test Trigger

```bash
# Fire a heavy rain trigger in zone 4 (Dadar, Mumbai)
python manage.py fire_trigger --zone 4 --type heavy_rain --severity 42.0

# Fire across all zones in a city
python manage.py fire_trigger --all-zones --type severe_aqi --severity 350

# Partial trigger (50% payout) for a specific platform
python manage.py fire_trigger --zone 27 --type platform_down \
  --severity 20 --platform swiggy --partial
```

---

## 📡 API Reference

### Authentication
All protected endpoints require `Authorization: Bearer <access_token>`.

```bash
# Get tokens
POST /api/v1/accounts/verify-otp/
Body: {"mobile": "9876543210", "code": "123456", "purpose": "login"}
Response: {"access": "...", "refresh": "..."}
```

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/workers/me/` | Current worker profile |
| `GET` | `/api/v1/workers/dashboard/` | Full dashboard payload |
| `GET` | `/api/v1/policies/my/` | Active policy |
| `GET` | `/api/v1/claims/` | Worker's claims list |
| `GET` | `/api/v1/claims/<pk>/` | Claim detail + fraud flags |
| `GET` | `/api/v1/payouts/` | Payout history |
| `GET` | `/api/v1/payouts/summary/` | Aggregate totals |
| `GET` | `/api/v1/pricing/my-risk/` | Current risk score + premiums |
| `POST` | `/api/v1/pricing/calculate/` | Estimate premium (public) |
| `GET` | `/api/v1/forecasting/my-zone/` | Zone risk forecast |
| `GET` | `/api/v1/forecasting/all/` | All city forecasts |
| `POST` | `/api/v1/payments/webhook/` | Razorpay webhook (no auth) |
| `GET/POST` | `/api/v1/whatsapp/webhook/` | WhatsApp Cloud webhook |
| `GET` | `/health/` | Health check |

---

## 🧗 Challenges We Ran Into

### 1. Fraud Detection Without Ground Truth
Training fraud models on a brand-new platform with no historical claims was a chicken-and-egg problem. We solved it by generating synthetic claim datasets using realistic distributions from public gig economy research, then validating model performance with held-out samples. The Isolation Forest's unsupervised nature helped — it doesn't need fraud labels.

### 2. Razorpay Payouts API Complexity
The Payouts flow requires three sequential API calls (Contact → Fund Account → Payout), each with potential failure points. We made each step idempotent by storing the intermediate IDs on `WorkerProfile` and checking for their existence before every API call.

### 3. Multi-Language WhatsApp at Scale
Formatting multilingual messages across 6 Indian languages while keeping templates readable in code was tricky. We built a simple `MESSAGES` dict keyed by `(event_type, language)` with Python format string templates — graceful English fallback if the language variant is missing.

### 4. Prophet Model Loading Time
Loading 27 Prophet `.pkl` files sequentially at startup was slow. We implemented a lazy-loading cache: models load on first use and are held in module-level globals, so each Celery worker process pays the cost only once.

### 5. Celery Beat Coordination
Ensuring that tasks don't double-fire when multiple Celery workers are running required careful use of `unique_together` constraints (one claim per worker per event) and idempotency guards at every task entry point.

---

## 🏆 Accomplishments We're Proud Of

- **End-to-end automation** — the complete pipeline from trigger detection to UPI credit works without a single manual step
- **Real ML models** — all three models (Isolation Forest, XGBoost pricing, Prophet forecasting) are fully trained on real-world-inspired data and serve live predictions
- **73 real zones** — seeded with accurate lat/lng coordinates and calibrated risk multipliers for every major delivery zone in 7 Indian cities
- **6 Indian languages** — WhatsApp notifications fully localised in English, Hindi, Marathi, Tamil, Telugu, and Bengali
- **Sandbox-first design** — the platform runs completely end-to-end in development with zero external API dependencies
- **47 templates, 418-line design system** — a production-grade frontend built from scratch with a custom CSS design system
- **IncomeDNA** — a cryptographically signed PDF that could genuinely help gig workers access credit — something no other gig platform offers

---

## 📚 What We Learned

- **Parametric insurance is genuinely hard to price fairly** — we spent significant time calibrating risk multipliers so that workers in high-risk zones (Dharavi, Kurla) pay proportionally more without the platform becoming unaffordable
- **ML model selection matters more than tuning** — Isolation Forest was the right choice for fraud detection precisely because we have no labelled fraud examples; a supervised model would have been useless at launch
- **Django's ORM is excellent for financial applications** — atomic transactions, `select_for_update`, and `unique_together` gave us the guarantees we needed for idempotent claim creation without complex distributed locks
- **Celery Beat scheduling is surprisingly nuanced** — task overlap, timezone handling (IST vs UTC), and retry logic for transient API failures each required careful thought
- **UPI is genuinely real-time** — integrating Razorpay Payouts showed us that once the infrastructure is right, sending money to 10,000 workers simultaneously is a solved problem in India

---

## 🔭 What's Next for Nexura

### Short Term (3 months)
- [ ] **React Native mobile app** — push notifications, offline claim status
- [ ] **DigiLocker integration** — automated Aadhaar KYC without manual number entry
- [ ] **Government civic alert API** — auto-detect floods and curfews via official data
- [ ] **Production Razorpay go-live** — process real subscriptions and payouts

### Medium Term (6–12 months)
- [ ] **Satellite rainfall data** — NASA GPM data for hyperlocal mm/hr estimates
- [ ] **Ride-sharing expansion** — extend coverage to Ola, Uber, and Rapido drivers
- [ ] **Nexura Circle loans** — micro-credit backed by claim history
- [ ] **IRDAI regulatory filing** — begin the process for licensed insurance product
- [ ] **B2B platform integration** — Zomato/Swiggy pay premiums on behalf of workers

### Long Term (1–2 years)
- [ ] **Pan-India expansion** — 50+ cities, 10M+ workers
- [ ] **Freelancer coverage** — graphic designers, tutors, and domestic workers
- [ ] **Public IncomeDNA API** — banks and NBFCs query worker income proofs directly
- [ ] **Climate risk bonds** — institutional capital backing for catastrophic weather events

---

## 👥 Team & Credits

### Built at [Guidewire DEVTrails Hackathon 2026](https://guidewiredevtrails.com)
**Parul University, Vadodara**

| Name | Role |
|---|---|
| **Soumya Das** | Full-Stack Development (Django, ML Integration & DevOps) |
| **Tanisha** | UI/UX Design & Frontend Development |
| **Rimi Banerjee** | Backend Architecture |
| **N. Kamakshi Lakshmi Bhai** | UI/UX Design & User Research |
| **Jagyanseni Paikaraya** | AI/ML Engineering (XGBoost, Prophet, Isolation Forest) |

### Special Thanks

| Service | What We Used |
|---|---|
| [OpenWeatherMap](https://openweathermap.org) | Real-time weather data per zone |
| [WAQI / CPCB](https://waqi.info) | Air Quality Index monitoring |
| [Razorpay](https://razorpay.com) | Autopay subscriptions + UPI Payouts API |
| [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp) | Worker notifications |
| [Facebook Prophet](https://facebook.github.io/prophet) | Disruption forecasting |
| [scikit-learn](https://scikit-learn.org) | Isolation Forest fraud detection |
| [XGBoost](https://xgboost.ai) | Risk pricing + fraud classification |
| [Guidewire](https://guidewire.com) | DEVTrails Hackathon platform |
| [EY](https://ey.com) | Hackathon partnership |

---

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](./CONTRIBUTING.md) before submitting a pull request.

```bash
# 1. Fork the repository
# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Make changes, write tests
# 4. Commit with conventional commits
git commit -m "feat(claims): add partial payout support for AQI triggers"

# 5. Push and open a PR
git push origin feature/your-feature-name
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution guide, code standards, and branch naming conventions.

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](./LICENSE) for details.

```
Copyright (c) 2026 Nexura Team — Guidewire DEVTrails Hackathon
```

---

<div align="center">

**Built with ❤️ for India's gig workers**

*Nexura — Protecting livelihoods, one delivery at a time.*

<br/>

[![GitHub Stars](https://img.shields.io/github/stars/your-team/Nexura?style=social)](https://github.com/Soumya-Das-2006/Nexura-The-Sensing-Squad)
[![GitHub Forks](https://img.shields.io/github/forks/your-team/Nexura?style=social)](https://github.com/Soumya-Das-2006/Nexura-The-Sensing-Squad/fork)
[![Twitter](https://img.shields.io/twitter/follow/Nexura_in?style=social)](https://twitter.com/Nexura_in)

</div>
