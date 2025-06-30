import streamlit as st
import sys
import os
from streamlit_cookies_controller import CookieController
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add paths for module imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'user_dashboard'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'doctor_dashboard'))

# Import pages
from login.login import login_page
from signup.signup import signup_page
from user_dashboard.home import user_dashboard
from user_dashboard.new_appointment import new_appointment_page
from doctor_dashboard.home import doctor_dashboard

# Validate session token with database
def validate_auth_token(token):
    from pymongo import MongoClient
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI)
    db = client.website_data

    user = db.users.find_one({"session_token": token})
    if user:
        return {'type': 'user', 'data': user}

    doctor = db.doctors.find_one({"session_token": token})
    if doctor:
        return {'type': 'doctor', 'data': doctor}

    return None

# Main app logic
def main():
    cookie_controller = CookieController()

    # Restore session from cookie if not already authenticated
    session_token = cookie_controller.get("session_token")
    if session_token and not st.session_state.get("authenticated"):
        user_data = validate_auth_token(session_token)
        if user_data:
            st.session_state["authenticated"] = True
            st.session_state["user_type"] = user_data["type"]
            st.session_state["user_data"] = user_data["data"]

    # Set default page
    if "page" not in st.session_state:
        st.session_state.page = "signup"

    # Handle authenticated session
    if st.session_state.get("authenticated"):
        if st.session_state["user_type"] == "user":
            # Check for dynamic routing to new appointment
            if st.session_state.get("current_page") == "new_appointment":
                new_appointment_page(st.session_state["user_data"], cookie_controller)
            else:
                user_dashboard(st.session_state["user_data"], cookie_controller)

        elif st.session_state["user_type"] == "doctor":
            doctor_dashboard(st.session_state["user_data"], cookie_controller)

    # Handle unauthenticated views
    else:
        if st.session_state.page == "signup":
            signup_page(cookie_controller)
        elif st.session_state.page == "login":
            login_page(cookie_controller)

# Run the app
if __name__ == "__main__":
    main()
