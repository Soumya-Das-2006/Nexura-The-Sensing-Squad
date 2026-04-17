import requests

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

def run_tests():
    print("--- 1. Testing Registration ---")
    reg_data = {
        "mobile": "9876543210",
        "name": "Test Worker",
        "platform": "zomato",
        "segment": "food",
        "zone": "1"  # Assuming zone PK 1 exists after fixtures
    }
    # First get the CSRF token
    r = session.get(f"{BASE_URL}/register/")
    if r.status_code == 200:
        csrf_token = r.cookies.get('csrftoken', '')
        reg_data['csrfmiddlewaretoken'] = csrf_token
        
        # We assume it's a standard form post
        res = session.post(f"{BASE_URL}/register/", data=reg_data, headers={'Referer': f"{BASE_URL}/register/"})
        print("Registration Response:", res.status_code)
        
    print("--- 2. Testing Login ---")
    login_data = {
        "mobile": "9876543210",
        "otp": "123456",
        "csrfmiddlewaretoken": csrf_token
    }
    res = session.post(f"{BASE_URL}/login/", data=login_data, headers={'Referer': f"{BASE_URL}/login/"})
    print("Login Response:", res.status_code)

    print("--- 3. Testing Calculator API ---")
    # See if there's an API for the calculator
    res = session.get(f"{BASE_URL}/pricing/calculator/")
    print("Calculator Page Status:", res.status_code)

if __name__ == "__main__":
    run_tests()
