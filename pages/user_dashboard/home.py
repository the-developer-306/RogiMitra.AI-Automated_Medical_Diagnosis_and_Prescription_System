import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('.env')

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.website_data
appointments_collection = db.new_appointments
users_collection = db.users

def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def user_dashboard(user, cookie_controller):
    # Sidebar
    with st.sidebar:

        st.markdown(
            """
            <div style="text-align: center; padding-bottom: 10px;">
                <img src="https://cdn-icons-png.flaticon.com/512/4320/4320337.png" width="50" style="margin-bottom: 5px;" />
                <h2 style="color:#4CAF50; margin-bottom: 5px;">Rogi<span style="color:#10B981;">Mitra</span><span style="color:#9CA3AF;">.AI</span></h2>
                <p style="font-size: 13px; color: #6B7280;">Your AI Health Companion</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")

        if user.get('dp'):
            profile_url = user['dp']
        else:
            profile_url = "https://via.placeholder.com/150"

        # Centered and interactive user profile card

        # Calculate age
        dob_date = datetime.strptime(user['dob'], '%Y-%m-%d').date()
        user_age = calculate_age(dob_date)

        st.markdown(f"""
            <div style='
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin-top: 30px;
                margin-bottom: 20px;
            '>
                <div style='
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    overflow: hidden;
                    border: 3px solid #3B82F6;
                    box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
                    transition: transform 0.3s ease;
                '>
                    <img src="{profile_url}" style='width: 100%; height: 100%; object-fit: cover;' alt="Profile Picture">
                </div>
                <h4 style='margin-top: 10px;'>{user['name']}</h4>
                <p style='margin: 0; font-size: 13px; color: #666;'>DOB: {user['dob']}</p>
                <p style='margin: 0; font-size: 13px; color: #666;'>Age: {user_age} years</p>
                <p style='margin: 0; font-size: 13px; color: #666;'>Gender: {user['gender']}</p>
                <p style='margin: 0; font-size: 13px; color: #666;'>Height: {user['height']} cm</p>
                <p style='margin: 0; font-size: 13px; color: #666;'>Weight: {user['weight']} kg</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        # Centered Logout button
        col_center = st.columns([1, 3, 1])[1]  # Centered column layout
        with col_center:
            if st.button("🚪 Logout", use_container_width=True):
                cookie_controller.set("session_token", "", max_age=0)
                st.session_state.clear()
                st.session_state.page = "login"
                st.rerun()

    st.markdown(f"""
        # 👋 Welcome, **{user['name']}**!

        <div style='font-size:17px; color:#4a4a4a;'>
        Welcome to your personal health assistant dashboard.<br>
        Easily start a new consultation or revisit your previous medical records.<br>
        Our <b>AI-powered system</b>, supervised by certified doctors, ensures you receive quick, accurate, and personalized healthcare guidance. 💡🩺
        </div>
        """, unsafe_allow_html=True
    )

    st.markdown("---")

    # 🩺 Start a new appointment
    st.markdown("### 🩺 Need a Checkup?")
    if st.button("➕ Start a New Appointment", use_container_width=True):
        st.session_state.current_page = "new_appointment"
        st.rerun()

    st.markdown("---")

    # 📜 View past history
    st.markdown("### 📜 View Your Medical History")
    if st.button("📂 View Past Appointments", use_container_width=True):
        past_appointments = list(appointments_collection.find({
            "user_id": user['_id'],
            "status": "completed"
        }))
        display_past_appointments(past_appointments)



def display_past_appointments(appointments):
    

    if not appointments:
        st.info("No past appointments found.")
        return

    for appt in appointments:

        created_at = appt["created_at"].strftime('%d %b %Y')
        with st.expander(f"🗓️ Appointment - {created_at}"):
            inputs = appt.get("inputs", {})

            # 💊 Symptoms
            st.markdown(f"#### **🩺 Symptoms:**\n\n{inputs.get('symptoms', 'N/A')}")

            # 💊 Recent Medications
            st.markdown(f"#### **🩺 Recent Medications:**\n\n{inputs.get('recent_medications', 'N/A')}")

            # 💊 Regular Medications
            st.markdown(f"#### **🩺 Regular Medications:**\n\n{inputs.get('regular_medications', 'N/A')}")

            # 💊 Notes
            st.markdown(f"#### **🩺 Important Notes:**\n\n{inputs.get('important_notes', 'N/A')}")

            # 📄 Lab Report Link
            lab_report = inputs.get("lab_report")
            if lab_report:
                st.markdown(f"#### **📄 [LAB REPORT]({lab_report})**", unsafe_allow_html=True)

            # 🖼️ Visual Symptoms (Images)
            if appt['inputs'].get('visual_symptoms'):
                st.markdown("##### 🖼️ Visual Symptoms:")
                images = appt['inputs']['visual_symptoms']
                cols = st.columns(2)
                for i, img_url in enumerate(images):
                    with cols[i % 2]:
                        st.image(img_url, use_container_width=True, caption=f"Symptom Image {i+1}")

            
            st.markdown("---")

            # 🧾 Final Report Link (Markdown)
            final_report = appt.get("final_report")
            if final_report:
                st.markdown("## **🧾 Diagnostics and Prescription Report:**")
                st.markdown(final_report, unsafe_allow_html=True)
            else:
                st.write("**🧾 Diagnostics and Prescription Report:** N/A")

            st.markdown("#### **Click here to download the Diagnostics and Prescription Report:**")
            if appt.get("final_report_pdf_url"):
                st.markdown(
                    f"""
                    <a href="{appt['final_report_pdf_url']}" target="_blank" download>
                        <button style="
                            background-color: #4CAF50;
                            color: white;
                            padding: 10px 20px;
                            text-align: center;
                            text-decoration: none;
                            display: inline-block;
                            font-size: 16px;
                            border: none;
                            border-radius: 5px;
                            cursor: pointer;
                            margin-top: 10px;
                        ">📥 Download Final Report (PDF)</button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )

            st.write("    ")

            # 💬 Doctor's Comments
            st.markdown(f"#### **💬 Doctor's Comments:**\n\n{appt.get('doctor_comments', 'N/A')}")

