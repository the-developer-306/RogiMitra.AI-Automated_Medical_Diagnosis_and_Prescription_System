import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
from bson.objectid import ObjectId
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import threading

# === Load environment variables ===
load_dotenv('.env')

# === Cloudinary Configuration ===
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# === MongoDB Setup ===
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.website_data
appointments_collection = db["new_appointments"]

# === Helper Functions ===
def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def get_next_appointment_id():
    last_appt = appointments_collection.find_one(sort=[("appointment_id", -1)])
    return (last_appt["appointment_id"] + 1) if last_appt else 1

def upload_to_cloudinary(file, folder="appointments", resource_type="auto"):
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        resource_type=resource_type
    )
    return result.get("secure_url")

# === Async CrewAI Execution ===
def run_crew_async(personal_data, appointment_data, inserted_id):
    try:
        from AI_workflows.workflow1.crew_logic.crew import run_crew_workflow1
        output = run_crew_workflow1(personal_data, appointment_data)

        appointments_collection.update_one(
            {"_id": inserted_id},
            {
                "$set": {
                    "intermediate_report": output,
                    "status": "pending_doctor_review"
                }
            }
        )
    except Exception as e:
        print("❌ Error running CrewAI workflow in background:", e)

# === Main Appointment Page ===
def new_appointment_page(user, cookie_controller):
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
        col_center = st.columns([1, 10, 1])[1]  # Centered column layout
        with col_center:

            if st.button("🔙 Back to Dashboard"):
                st.session_state.current_page = None
                st.rerun()

            if st.button("🚪 Logout", use_container_width=True):
                cookie_controller.set("session_token", "", max_age=0)
                st.session_state.clear()
                st.session_state.page = "login"
                st.rerun()

    st.title(f"🩺 New Appointment for {user['name']}")

    # === Form ===
    with st.form(key='new_appointment_form'):
        symptoms = st.text_area('Symptoms')
        recent_medications = st.text_area('Recent Medications')
        regular_medications = st.text_area('Regular Medications')
        lab_report = st.file_uploader('Lab Report (PDF)', type=['pdf'])
        important_notes = st.text_area('Important Notes')
        visual_symptoms = st.file_uploader('Visual Symptoms', type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if st.form_submit_button('Submit Appointment'):
            appt_id = get_next_appointment_id()

            # Upload files to Cloudinary
            lab_report_url = upload_to_cloudinary(lab_report, folder=f"appointments/{appt_id}", resource_type="raw") if lab_report else None
            visual_symptom_urls = [upload_to_cloudinary(img, folder=f"appointments/{appt_id}/images") for img in visual_symptoms] if visual_symptoms else []

            # Prepare appointment data
            appointment_data = {
                "appointment_id": appt_id,
                "user_id": user['_id'],
                "created_at": datetime.utcnow(),
                "status": "pending",  # will change after AI runs
                "inputs": {
                    "symptoms": symptoms,
                    "recent_medications": recent_medications,
                    "regular_medications": regular_medications,
                    "important_notes": important_notes,
                    "lab_report": lab_report_url,
                    "visual_symptoms": visual_symptom_urls
                }
            }

            # Insert appointment to DB
            insert_result = appointments_collection.insert_one(appointment_data)
            inserted_id = insert_result.inserted_id

            # Prepare personal data for Crew
            personal_data = {
                "name": user["name"],
                "dob": user["dob"],
                "age": calculate_age(dob_date),
                "weight": user["weight"],
                "height": user["height"]
            }

            # Start CrewAI in background
            threading.Thread(
                target=run_crew_async,
                args=(personal_data, appointment_data, inserted_id),
                daemon=True
            ).start()

            # ✅ Immediate Confirmation
            st.success(f"✅ Appointment #{appt_id} submitted successfully! AI workflow is now running.")
            # st.balloons()

            # # Summary
            # st.markdown("---")
            # st.subheader("📋 Appointment Summary")
            # st.write(f"**Symptoms:** {symptoms}")
            # st.write(f"**Recent Medications:** {recent_medications}")
            # st.write(f"**Regular Medications:** {regular_medications}")
            # st.write(f"**Important Notes:** {important_notes}")
            # if lab_report_url:
            #     st.markdown(f"**Lab Report:** [View PDF]({lab_report_url})")
            # if visual_symptom_urls:
            #     st.markdown("**Visual Symptoms:**")
            #     for url in visual_symptom_urls:
            #         st.image(url, width=300)

            st.markdown("---")
            st.info("Our AI system is generating your diagnostic report. A doctor will review it and update your dashboard shortly.")
