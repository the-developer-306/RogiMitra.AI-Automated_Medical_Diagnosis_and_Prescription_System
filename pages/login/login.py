import streamlit as st
from pymongo import MongoClient
import bcrypt
import secrets
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('.env')


# ------------------ AUTH HELPERS ------------------ #
def authenticate_user(users_collection, username, password):
    user = users_collection.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode(), user['password_hash']):
        return user
    return None


def authenticate_doctor(doctors_collection, username, password):
    doctor = doctors_collection.find_one({"username": username})
    if doctor and bcrypt.checkpw(password.encode(), doctor['password_hash']):
        return doctor
    return None


# ------------------ MAIN LOGIN PAGE ------------------ #
def login_page(cookie_controller):
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI)
    db = client.website_data
    users_collection = db.users
    doctors_collection = db.doctors

    # ----- SIDEBAR WITH LOGO AND BRAND ----- #
    with st.sidebar:
        st.markdown("""
            <div style='text-align: center; margin-top: 30px;'>
                <img src="https://cdn-icons-png.flaticon.com/512/4320/4320337.png" width="100">
                <h2 style="color:#4CAF50; margin-bottom: 5px;">Rogi<span style="color:#10B981;">Mitra</span><span style="color:#9CA3AF;">.AI</span></h2>
                <p style='font-size: 13px; color: #666; padding: 0 10px;'>
                    Your intelligent health companion. Get AI-powered diagnosis and prescription, backed by certified doctors — anytime, anywhere.
                </p>
            </div>
        """, unsafe_allow_html=True)

    # ----- MAIN LOGIN SECTION ----- #
    st.markdown("<h1 style='text-align: center;'>Login to Continue</h1>", unsafe_allow_html=True)

    tabs = st.tabs(["👤 User", "🩺 Doctor"])

    with tabs[0]:
        st.markdown("#### User Login")
        with st.form(key='user_login_form'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            if st.form_submit_button('Login'):
                user = authenticate_user(users_collection, username, password)
                if user:
                    session_token = secrets.token_urlsafe(32)
                    users_collection.update_one(
                        {"_id": user['_id']},
                        {"$set": {"session_token": session_token}}
                    )
                    cookie_controller.set("session_token", session_token, max_age=86400)  # 1 day

                    time.sleep(1)
                    st.session_state["authenticated"] = True
                    st.session_state["user_type"] = "user"
                    st.session_state["user_data"] = user
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tabs[1]:
        st.markdown("#### Doctor Login")
        with st.form(key='doctor_login_form'):
            username = st.text_input('Username', key='doctor_username')
            password = st.text_input('Password', type='password', key='doctor_password')
            if st.form_submit_button('Login'):
                doctor = authenticate_doctor(doctors_collection, username, password)
                if doctor:
                    session_token = secrets.token_urlsafe(32)
                    doctors_collection.update_one(
                        {"_id": doctor['_id']},
                        {"$set": {"session_token": session_token}}
                    )
                    cookie_controller.set("session_token", session_token, max_age=86400)  # 1 day
                    st.session_state["authenticated"] = True
                    st.session_state["user_type"] = "doctor"
                    st.session_state["user_data"] = doctor
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    # ----- SIGNUP CTA ----- #
    st.markdown("---")
    st.markdown("<div style='text-align: center;'>Don't have an account?</div>", unsafe_allow_html=True)
    if st.button("📋 Signup Here"):
        st.session_state.page = "signup"
        st.rerun()
