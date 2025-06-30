import time
import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import os
import threading
from dotenv import load_dotenv
from fpdf import FPDF
import cloudinary
import cloudinary.uploader
from AI_workflows.workflow2.crew_logic.crew import run_crew_workflow2
import unicodedata
import re

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
appointments_collection = db.new_appointments
users_collection = db.users


# === Helper Functions ===

def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def markdown_to_plain_text(md):
    # Remove markdown links and formatting
    plain_text = re.sub(r'!\[.*?\]\(.*?\)', '', md)  # remove images
    plain_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', plain_text)  # convert links to text
    plain_text = re.sub(r'[>#*_`]', '', plain_text)  # strip markdown symbols
    plain_text = re.sub(r'\n{2,}', '\n\n', plain_text)  # normalize line breaks
    return plain_text.strip()

def sanitize_text(text):
    return unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")

def generate_pdf(markdown_text, appointment_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    plain_text = markdown_to_plain_text(markdown_text)
    clean_text = sanitize_text(plain_text)

    for line in clean_text.split('\n'):
        pdf.multi_cell(0, 10, line)

    os.makedirs("temp_reports", exist_ok=True)
    file_path = f"temp_reports/report_{appointment_id}.pdf"
    pdf.output(file_path)
    return file_path

def upload_pdf_to_cloudinary(file_path, folder="reports"):
    result = cloudinary.uploader.upload(
        file_path,
        folder=folder,
        resource_type="raw"
    )
    return result.get("secure_url")


# === Async CrewAI Final Workflow ===
def run_final_report_async(appt, suggestions, doctor_name):
    try:
        final_markdown = run_crew_workflow2(
            intermediate_report=appt.get("intermediate_report"),
            suggestions_for_modifications=suggestions,
            doctor_name = doctor_name
        )

        pdf_path = generate_pdf(final_markdown, appt['appointment_id'])
        pdf_url = upload_pdf_to_cloudinary(pdf_path, folder=f"appointments/{appt['appointment_id']}/final_report")

        appointments_collection.update_one(
            {"_id": appt['_id']},
            {
                "$set": {
                    "final_report": final_markdown,
                    "final_report_pdf_url": pdf_url,
                    "status": "completed"
                }
            }
        )
        print(f"✅ Final report saved for Appointment #{appt['appointment_id']}")

    except Exception as e:
        print("❌ Final report generation error:", e)
        appointments_collection.update_one(
            {"_id": appt['_id']},
            {"$set": {"status": "error_finalizing"}}
        )


# === Main Dashboard ===
def doctor_dashboard(doctor, cookie_controller):
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


        if doctor.get('dp'):
            profile_url = doctor['dp']
        else:
            profile_url = "https://via.placeholder.com/150"

        # Centered and interactive doctor profile card
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
                    border: 3px solid #10B981;
                    box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
                    transition: transform 0.3s ease;
                '>
                    <img src="{profile_url}" style='width: 100%; height: 100%; object-fit: cover;' alt="Profile Picture">
                </div>
                <h4 style='margin-top: 10px;'>Dr. {doctor['name']}</h4>
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


    st.title("🩺 Pending Appointments to Review")

    pending_appointments = list(appointments_collection.find({
        "status": "pending_doctor_review"
    }))

    if not pending_appointments:
        st.info("🎉 No pending appointments")
        return

    for appt in pending_appointments:
        user = users_collection.find_one({"_id": appt['user_id']})
        if not user:
            continue

        with st.expander(f"Appointment - {user['name']}"):
            dob_date = datetime.strptime(user['dob'], '%Y-%m-%d').date()

            st.markdown("### 🧍 User Details")
            st.write(f"**Name:** {user['name']}")
            st.write(f"**Age:** {calculate_age(dob_date)}")
            st.write(f"**Gender:** {user['gender']}")
            st.write(f"**Height:** {user['height']} cm")
            st.write(f"**Weight:** {user['weight']} kg")

            st.markdown("---")
            st.markdown("### 📋 User Inputs")
            st.write("##### **Symptoms:**")
            st.write(appt['inputs'].get('symptoms', 'N/A'))
            st.write("##### **Recent Medications:**")
            st.write(appt['inputs'].get('recent_medications', 'N/A'))
            st.write("##### **Regular Medications:**")
            st.write(appt['inputs'].get('regular_medications', 'N/A'))
            st.write("##### **Important Notes:**")
            st.write(appt['inputs'].get('important_notes', 'N/A'))

            if appt['inputs'].get('lab_report'):
                st.markdown(f"##### 📄 [View Laboratory Diagnostics Report]({appt['inputs']['lab_report']})")

            if appt['inputs'].get('visual_symptoms'):
                st.markdown("##### 🖼️ Visual Symptoms:")
                images = appt['inputs']['visual_symptoms']
                cols = st.columns(2)
                for i, img_url in enumerate(images):
                    with cols[i % 2]:
                        st.image(img_url, use_container_width=True, caption=f"Symptom Image {i+1}")

            st.markdown("---")
            st.markdown("### 🧠 AI-Generated Intermediate Report")
            st.markdown(appt.get('intermediate_report', 'N/A'), unsafe_allow_html=True)

            st.markdown("### ✍️ Suggestions to Modify the Report")
            suggestions = st.text_area(
                "Suggestions for Modifying the AI Report",
                placeholder="E.g. Add clarity to diagnosis, suggest extra tests...",
                key=f"suggestions_{appt['_id']}"
            )

            st.markdown("### 💬 Doctor's Comments for User")
            comments = st.text_area(
                "Advice or instructions for the patient",
                placeholder="E.g. Take rest, follow up in 5 days, avoid spicy food...",
                key=f"comments_{appt['_id']}"
            )

            if st.button("✅ Validate and Finalize", key=f"submit_{appt['_id']}"):
                appointments_collection.update_one(
                    {"_id": appt['_id']},
                    {
                        "$set": {
                            "suggestions_for_modifications": suggestions,
                            "doctor_comments": comments,
                            "status": "generating_final_report",
                            "finalized_at": datetime.utcnow()
                        }
                    }
                )

                threading.Thread(
                    target=run_final_report_async,
                    args=(appt, suggestions, doctor['name']),
                    daemon=True
                ).start()

                st.success("🧠 Suggestions saved! Final report is being generated in background...")
                time.sleep(2)
                st.rerun()
