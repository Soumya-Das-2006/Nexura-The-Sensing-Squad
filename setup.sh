#!/usr/bin/env bash
# ================================================================
# Nexura — One-Shot Dev Setup
# Run from the project root: bash setup.sh
# ================================================================
set -e

echo "🛡️  Nexura Setup"
echo "================"
echo ""

# 1. Check Python
python3 --version || { echo "ERROR: Python 3 not found"; exit 1; }

# 2. Copy .env if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env from .env.example (edit API keys as needed)"
else
    echo "✓ .env already exists"
fi

# 3. Install dependencies
echo ""
echo "▶ Installing dependencies..."
pip install -r requirements.txt --quiet
echo "  ✓ Dependencies installed"

# 4. Migrate
echo ""
echo "▶ Running migrations..."
python manage.py migrate --no-input
echo "  ✓ Database ready"

# 5. Load seed data
echo ""
echo "▶ Loading seed data..."
bash fixtures/load_all.sh
echo ""
echo "✅ Setup complete!"
echo ""
echo "Run the server:"
echo "  python manage.py runserver"
echo ""
echo "Visit: http://127.0.0.1:8000/"
echo ""
echo "Demo credentials:"
echo "  Admin:  mobile=9000000000   password=nexura@demo123"
echo "  Portal: http://127.0.0.1:8000/admin-portal/"
echo "  Admin:  http://127.0.0.1:8000/django-admin/"
