# 🤝 Contributing to Nexura

Thank you for your interest in contributing to Nexura! This document provides guidelines for contributing to this project — built at the Guidewire DEVTrails 2026 Hackathon.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Development Setup](#development-setup)
4. [Branch Naming Conventions](#branch-naming-conventions)
5. [Commit Message Format](#commit-message-format)
6. [Pull Request Process](#pull-request-process)
7. [Code Style Guidelines](#code-style-guidelines)
8. [Testing Requirements](#testing-requirements)
9. [Project Architecture Notes](#project-architecture-notes)
10. [Where to Get Help](#where-to-get-help)

---

## Code of Conduct

This project follows a simple principle: **be respectful, be helpful, be constructive**. We are all here to build something meaningful for India's gig workers.

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community and the workers we serve

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating a bug report, please check if the issue already exists. When creating a bug report, include:

- **Clear title** — what went wrong
- **Steps to reproduce** — exact sequence of actions
- **Expected behaviour** — what you expected to happen
- **Actual behaviour** — what actually happened
- **Environment** — Python version, OS, Django version
- **Logs** — relevant Celery or Django error logs

**Open a bug report:** [GitHub Issues → Bug Report](https://github.com/Soumya-Das-2006/Nexura-The-Sensing-Squad/issues/new?template=bug_report.md)

### 💡 Suggesting Features

We especially welcome ideas around:

- New disruption trigger types (air quality alerts, cyclone warnings)
- Additional ML features or model improvements
- New cities / zones
- Additional language support for WhatsApp notifications
- Accessibility improvements

**Open a feature request:** [GitHub Issues → Feature Request](https://github.com/Soumya-Das-2006/Nexura-The-Sensing-Squad/issues/new?template=feature_request.md)

### 🔧 Code Contributions

The areas where we most need help:

| Area | Priority | Skills |
|---|---|---|
| React Native mobile app | 🔴 High | React Native, Expo |
| More ML features | 🔴 High | scikit-learn, XGBoost |
| Test coverage | 🔴 High | Django TestCase, pytest |
| New city zones | 🟡 Medium | Geographic data |
| More trigger types | 🟡 Medium | API integration |
| Performance optimisation | 🟢 Low | Django ORM, caching |

---

## Development Setup

### Prerequisites

```bash
Python 3.10+
PostgreSQL 15+
Redis 7.0+
Git
```

### Step-by-Step Setup

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Nexura.git
cd Nexura

# 2. Add the upstream remote
git remote add upstream https://github.com/your-team/Nexura.git

# 3. Create and activate virtualenv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 4. Install all dependencies including dev tools
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, flake8, black, etc.

# 5. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and DB credentials

# 6. Set up database and load fixtures
createdb nexura_dev
python manage.py migrate
bash fixtures/load_all.sh

# 7. Run the development server
python manage.py runserver

# 8. In separate terminals:
redis-server
celery -A nexura worker -l info
celery -A nexura beat   -l info
```

### Verify Your Setup

```bash
python manage.py check           # Check for Django issues
python manage.py test            # Run test suite
python manage.py fire_trigger \
  --zone 4 --type heavy_rain \
  --severity 42.0               # Test the trigger pipeline
```

---

## Branch Naming Conventions

Use descriptive branch names with a prefix:

| Prefix | Use case | Example |
|---|---|---|
| `feat/` | New feature | `feat/cyclone-trigger-type` |
| `fix/` | Bug fix | `fix/payout-duplicate-on-retry` |
| `docs/` | Documentation only | `docs/api-reference-update` |
| `test/` | Adding tests | `test/claims-pipeline-coverage` |
| `refactor/` | Code improvement | `refactor/fraud-pipeline-layers` |
| `chore/` | Build / tooling | `chore/upgrade-celery-5.4` |
| `hotfix/` | Urgent production fix | `hotfix/razorpay-webhook-sig` |

```bash
# Good
git checkout -b feat/satellite-rainfall-integration
git checkout -b fix/otp-resend-timer-reset

# Avoid
git checkout -b my-branch
git checkout -b fix1
```

---

## Commit Message Format

We follow **Conventional Commits** specification:

```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure without feature/fix |
| `test` | Adding or updating tests |
| `chore` | Build process, dependency updates |
| `perf` | Performance improvement |

### Scopes (optional but encouraged)

`accounts`, `claims`, `payouts`, `payments`, `fraud`, `pricing`, `forecasting`, `notifications`, `triggers`, `zones`, `policies`, `workers`, `circles`, `documents`, `admin`, `celery`, `ml`, `api`, `templates`, `static`

### Examples

```bash
# Good commit messages
feat(triggers): add cyclone warning trigger type with IMD API integration
fix(payouts): prevent duplicate payout creation on Celery retry
docs(api): add examples for /api/v1/claims/ endpoint
test(fraud): add unit tests for Layer 4 ML score computation
refactor(forecasting): lazy-load Prophet models per Celery worker process
chore(deps): upgrade XGBoost to 2.0.3

# Bad commit messages
fixed bug
update
WIP
asdf
```

---

## Pull Request Process

### Before Submitting

- [ ] Branch is up-to-date with `main`
- [ ] All tests pass: `python manage.py test`
- [ ] Code passes linting: `flake8 apps/` and `black --check apps/`
- [ ] New features have corresponding tests
- [ ] Fixtures updated if new models added
- [ ] Documentation updated if API changed

### PR Template

When you open a PR, fill in the template:

```markdown
## What does this PR do?
<!-- Concise description of the change -->

## Why is this change needed?
<!-- Problem it solves or feature it adds -->

## How was it tested?
<!-- Manual steps + automated tests -->

## Screenshots (if UI changes)

## Checklist
- [ ] Tests pass
- [ ] Linting passes
- [ ] Fixtures updated (if needed)
- [ ] README updated (if needed)
```

### Review Process

1. At least **1 team member** must review and approve
2. All CI checks must pass
3. No unresolved comments
4. PR will be squash-merged to `main`

---

## Code Style Guidelines

### Python

We use **Black** for formatting and **flake8** for linting.

```bash
# Format code
black apps/ nexura/

# Check linting
flake8 apps/ nexura/ --max-line-length=100
```

Key rules:
- 100-character line limit (not PEP 8's 79)
- Use f-strings, not `.format()` or `%`
- Type hints on all new public functions
- Docstrings on all models and non-trivial functions
- No bare `except:` — always catch specific exceptions

```python
# Good
def run_fraud_pipeline(claim: Claim) -> dict:
    """
    Run all 6 layers of fraud detection on a Claim instance.
    Returns a result dict with 'decision', 'fraud_score', and 'flags'.
    """
    ...

# Bad
def run(c):
    try:
        ...
    except:
        pass
```

### Django

- Use `select_related` and `prefetch_related` — no N+1 queries
- All Celery tasks must be **idempotent** (safe to run twice)
- Use `update_or_create` and `get_or_create` for race-condition-safe operations
- Wrap financial operations in `transaction.atomic()`
- Always use `update_fields=` in `.save()` calls — never save the whole object unnecessarily

```python
# Good — idempotent, atomic
with transaction.atomic():
    claim, created = Claim.objects.get_or_create(
        worker=worker,
        disruption_event=event,
        defaults={'payout_amount': amount, 'status': 'pending'},
    )

# Good — targeted save
claim.status = 'approved'
claim.save(update_fields=['status', 'updated_at'])
```

### Templates

- Extend `base.html`, `base_dashboard.html`, or `base_admin.html`
- Use `{% static %}` for all static file references
- Use `{% url %}` for all URL references — never hardcode paths
- Use `{% include %}` for reusable partials

### JavaScript

- Use `nexuraToast()` for user feedback — no raw `alert()`
- All fetch calls must handle errors with `.catch()`
- Use `data-confirm="..."` attribute for confirmation dialogs

---

## Testing Requirements

### Running Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test apps.claims
python manage.py test apps.fraud

# With coverage
coverage run manage.py test
coverage report
```

### What to Test

| Test type | What to cover |
|---|---|
| **Unit tests** | Individual functions: pipeline layers, price calculation, feature engineering |
| **Integration tests** | Full flow: trigger → claim → payout |
| **API tests** | All endpoints: status codes, response shape, authentication |
| **Model tests** | `unique_together`, properties, methods |

### Example Test Structure

```python
# apps/claims/tests.py
from django.test import TestCase
from apps.claims.models import Claim
from apps.fraud.service import run_fraud_pipeline

class FraudPipelineTest(TestCase):

    def setUp(self):
        # Create minimal test data: user, zone, policy, event
        ...

    def test_duplicate_claim_rejected(self):
        """Layer 2 must reject duplicate claims for the same event."""
        claim1 = Claim.objects.create(worker=self.worker, ...)
        claim2 = Claim.objects.create(worker=self.worker, ...)
        result = run_fraud_pipeline(claim2)
        self.assertEqual(result['decision'], 'reject')
        self.assertIn('duplicate', [f['flag'] for f in result['flags']])

    def test_auto_approve_low_score(self):
        """Claims scoring below 0.50 should be auto-approved."""
        claim = Claim.objects.create(worker=self.worker, ...)
        result = run_fraud_pipeline(claim)
        # With clean test data, score should be low
        if result['fraud_score'] < 0.50:
            self.assertEqual(result['decision'], 'approve')
```

---

## Project Architecture Notes

### Adding a New Trigger Type

1. Add to `DisruptionEvent.TRIGGER_TYPE_CHOICES` in `apps/triggers/models.py`
2. Add threshold constants to `apps/triggers/thresholds.py`
3. Add a polling task in `apps/triggers/tasks.py`
4. Add to `CELERY_BEAT_SCHEDULE` in `nexura/settings/base.py`
5. Add icon/color mapping in `DisruptionEvent.icon` and `.color` properties
6. Add fixture entry in `fixtures/demo_disruption_events.json`
7. Update the trigger badge CSS in `static/css/style.css`

### Adding a New City

1. Add zone rows to `fixtures/zones.json` with accurate lat/lng
2. Add the city to `apps/forecasting/loader.py` `CITY_KEY_MAP`
3. Train Prophet models for the new city (4 models per city)
4. Add city risk heuristics to `_city_heuristic_rain()` and related functions
5. Add to `apps/core/context_processors.py` `covered_cities` list

### Adding a Notification Type

1. Add message templates to `apps/notifications/channels.py` `MESSAGES` dict
2. Add all required language variants (en + hi minimum)
3. Create a new `@shared_task` in `apps/notifications/tasks.py`
4. Export the task from any caller that needs it

---

## Where to Get Help

- **Documentation:** Read `apps/<app_name>/` source code — each module has detailed docstrings
- **Fixture questions:** See `fixtures/README.md`
- **Architecture questions:** Open a GitHub Discussion
- **Bug reports:** Open a GitHub Issue
- **Security issues:** Email `security@Nexura.in` — do NOT open a public issue

---

*Thank you for making Nexura better — and for caring about India's gig workers.* 🙏
