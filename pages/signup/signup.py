import streamlit as st
from pymongo import MongoClient
import bcrypt
from datetime import datetime, date
import secrets
import time
import cloudinary
import cloudinary.uploader

# Cloudinary config
cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"],
    secure=True
)

# Upload DP
def upload_dp_to_cloudinary(file, username):
    if file:
        result = cloudinary.uploader.upload(
            file,
            folder=f"profile_pictures/{username}",
            resource_type="image"
        )
        return result.get("secure_url")
    return None

def signup_page(cookie_controller):
    MONGO_URI = st.secrets["MONGO_URI"]
    client = MongoClient(MONGO_URI)
    db = client.website_data
    users_collection = db.users
    doctors_collection = db.doctors

    # Sidebar with branding
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

    # Main Title
    st.markdown("<h1 style='text-align: center;'>Create Your Account</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Choose your role and fill in your details to join RogiMitra.AI</p>", unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs(["👤 User", "🩺 Doctor"])

    # -------------------- USER SIGNUP -------------------- #
    with tabs[0]:
        st.markdown("#### 👤 User Signup")
        with st.form(key='user_signup_form'):
            username = st.text_input('Username')
            name = st.text_input('Full Name')
            dob = st.date_input('Date of Birth', min_value=date(1970, 1, 1))
            gender = st.selectbox('Gender', ['Male', 'Female', 'Other'])
            weight = st.number_input('Weight (kg)', min_value=0.0, format='%f')
            height = st.number_input('Height (cm)', min_value=0.0, format='%f')
            password = st.text_input('Password', type='password')
            confirm_password = st.text_input('Confirm Password', type='password')
            dp = st.file_uploader('Upload Display Picture', type=['png', 'jpg', 'jpeg'])

            if st.form_submit_button('Sign Up'):
                if password != confirm_password:
                    st.error('❌ Passwords do not match.')
                elif users_collection.find_one({"username": username}):
                    st.error("❌ Username already exists.")
                else:
                    dp_url = upload_dp_to_cloudinary(dp, username)
                    session_token = secrets.token_urlsafe(32)
                    user_doc = {
                        "username": username,
                        "name": name,
                        "dob": dob.strftime('%Y-%m-%d'),
                        "gender": gender,
                        "weight": weight,
                        "height": height,
                        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
                        "dp": dp_url,
                        "created_at": datetime.utcnow(),
                        "session_token": session_token
                    }
                    users_collection.insert_one(user_doc)
                    cookie_controller.set("session_token", session_token, max_age=86400)

                    time.sleep(1)
                    st.session_state["authenticated"] = True
                    st.session_state["user_type"] = "user"
                    st.session_state["user_data"] = user_doc
                    st.rerun()

    # -------------------- DOCTOR SIGNUP -------------------- #
    with tabs[1]:
        st.markdown("#### 🩺 Doctor Signup")
        with st.form(key='doctor_signup_form'):
            username = st.text_input('Username', key="doc_user")
            name = st.text_input('Full Name', key="doc_name")
            password = st.text_input('Password', type='password', key="doc_pass")
            confirm_password = st.text_input('Confirm Password', type='password', key="doc_conf")
            dp = st.file_uploader('Upload Display Picture', type=['png', 'jpg', 'jpeg'], key="doc_dp")

            if st.form_submit_button('Sign Up'):
                if password != confirm_password:
                    st.error('❌ Passwords do not match.')
                elif doctors_collection.find_one({"username": username}):
                    st.error("❌ Username already exists.")
                else:
                    dp_url = upload_dp_to_cloudinary(dp, username)
                    session_token = secrets.token_urlsafe(32)
                    doctor_doc = {
                        "username": username,
                        "name": name,
                        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
                        "dp": dp_url,
                        "created_at": datetime.utcnow(),
                        "session_token": session_token
                    }
                    doctors_collection.insert_one(doctor_doc)
                    cookie_controller.set("session_token", session_token, max_age=86400)

                    time.sleep(1)
                    st.session_state["authenticated"] = True
                    st.session_state["user_type"] = "doctor"
                    st.session_state["user_data"] = doctor_doc
                    st.rerun()

    # ----- Login Redirect CTA ----- #
    st.markdown("---")
    st.markdown("<div style='text-align: center;'>Already have an account?</div>", unsafe_allow_html=True)
    if st.button("🔐 Login"):
        st.session_state.page = "login"
        st.rerun()
