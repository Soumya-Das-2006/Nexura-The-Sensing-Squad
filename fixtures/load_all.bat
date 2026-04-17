@echo off
echo Loading Nexura Fixtures...

python manage.py loaddata fixtures\zones.json
python manage.py loaddata fixtures\plans.json
python manage.py loaddata fixtures\risk_circles.json

echo Generating Demo Data...
python manage.py create_demo_data

echo All fixtures loaded successfully!
