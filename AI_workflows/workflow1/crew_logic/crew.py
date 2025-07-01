import yaml
import warnings
from PyPDF2 import PdfReader
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from tavily import TavilyClient
import tempfile
import requests
import streamlit as st

warnings.filterwarnings('ignore')

# ----------------------------
# STEP 1: ENV & API INIT
# ----------------------------
def initialize_api():
    if not st.secrets.get("DEEPSEEK_API"):
        raise ValueError("❌ DEEPSEEK_API key not found in secrets.toml")
    if not st.secrets.get("TAVILY_API_KEY"):
        raise ValueError("❌ TAVILY_API_KEY not found in secrets.toml")

# ----------------------------
# STEP 2: LLM INIT
# ----------------------------
def llm_initialization():
    return LLM(
        base_url="https://api.deepseek.com",
        api_key=st.secrets["DEEPSEEK_API"],
        model="deepseek/deepseek-chat"
    )

# ---------------------------
# STEP 3i: TOOL INIT (PDF)
# ----------------------------
def tool_initialization():
    class PDFReaderTool(BaseTool):
        name: str = "PDF Reader"
        description: str = "Reads contents of a PDF and returns the text."

        def _run(self, pdf_path: str) -> str:
        # If it's a URL, download it first
            if pdf_path.startswith("http"):
                response = requests.get(pdf_path)
                if response.status_code != 200:
                    raise ValueError("Failed to download PDF from Cloudinary")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name
            else:
                tmp_path = pdf_path

            reader = PdfReader(tmp_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text

    return PDFReaderTool()


# ---------------------------
# STEP 3ii: GENERATE SEARCH QUERY
# ----------------------------
def generate_web_search_query(symptoms_text, llm):
    prompt = f"""
    You are a medical assistant. Based on the following user-entered symptoms, generate a concise and medically relevant search query to help find potential cures or diagnostic approaches.
    
    Symptoms: {symptoms_text}

    Generate a compact and keyword-based medical search query strictly under 300 characters. Avoid full sentences.
    
    Output just the search query string.
    """
    response = llm.call(prompt)
    return response.strip().replace('"', '')[:380]

# ----------------------------
# STEP 5: PERFORM WEB SEARCH
# ----------------------------
def perform_web_search(query, k=3):
    client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
    results = client.search(query, search_depth="advanced", max_results=k)
    return "\n\n".join([res['content'] for res in results['results']])

# ----------------------------
# STEP 4: LOAD AGENTS & TASKS
# ----------------------------
def load_agents_and_tasks_and_create_crew(llm):

    # Loading Agent and Task YAML files
    files = {
        'agents': 'AI_workflows/workflow1/config/agents_and_tasks/agents.yaml',
        'tasks': 'AI_workflows/workflow1/config/agents_and_tasks/tasks.yaml'
    }

    configs = {}
    for config_type, file_path in files.items():
        with open(file_path, 'r') as file :
            configs[config_type] = yaml.safe_load(file)

    ## Assigning Loaded Configurations to specific variables
    agents_config = configs['agents']
    tasks_config = configs['tasks']
    
    # --------------------------------- Agent Initialization -----------------------------------------

    Symptom_Summarizer_Agent = Agent(
        config=agents_config['Symptom_Summarizer_Agent'],
        llm=llm,
        tools=[],
        verbose=True
    )

    Medications_Summarizer_Agent = Agent(
        config=agents_config['Medications_Summarizer_Agent'],
        llm=llm,
        tools=[],
        verbose=True
    )

    Laboratory_Diagnosis_Report_Summarizer_Agent = Agent(
        config=agents_config['Laboratory_Diagnosis_Report_Summarizer_Agent'],
        llm=llm,
        tools=[],
        verbose=True
    )

    Intermediate_Diagnostics_Report_Generator_Agent = Agent(
        config=agents_config['Intermediate_Diagnostics_Report_Generator_Agent'],
        llm=llm,
        tools=[],
        verbose=True
    )
    
    # --------------------------------- Task Initialization -----------------------------------------

    Symptom_Summarization_Task = Task(
        config=tasks_config['Symptom_Summarization_Task'],
        agent=Symptom_Summarizer_Agent,
        tools=[],
    )

    Recent_Medications_Summarization_Task = Task(
        config=tasks_config['Recent_Medications_Summarization_Task'],
        agent=Medications_Summarizer_Agent,
        tools=[],
    )

    Regular_Medications_Summarization_Task = Task(
        config=tasks_config['Regular_Medications_Summarization_Task'],
        agent=Medications_Summarizer_Agent,
        tools=[],
    )

    Laboratory_Diagnosis_Report_Summarization_Task = Task(
        config=tasks_config['Laboratory_Diagnosis_Report_Summarization_Task'],
        agent=Laboratory_Diagnosis_Report_Summarizer_Agent,
        tools=[],
    )

    Intermediate_Diagnostics_Report_Generation_Task = Task(
        config=tasks_config['Intermediate_Diagnostics_Report_Generation_Task'],
        agent=Intermediate_Diagnostics_Report_Generator_Agent,
        context=[Symptom_Summarization_Task, Recent_Medications_Summarization_Task, Regular_Medications_Summarization_Task, Laboratory_Diagnosis_Report_Summarization_Task],
        tools=[],
    )

    # --------------------------------- Crew Creation -----------------------------------------

    crew = Crew(
        
        agents=[
            Symptom_Summarizer_Agent,
            Medications_Summarizer_Agent,
            Laboratory_Diagnosis_Report_Summarizer_Agent,
            Intermediate_Diagnostics_Report_Generator_Agent,
        ],
        
        tasks=[
            Symptom_Summarization_Task,
            Recent_Medications_Summarization_Task,
            Regular_Medications_Summarization_Task,
            Laboratory_Diagnosis_Report_Summarization_Task,
            Intermediate_Diagnostics_Report_Generation_Task
        ],

        verbose=True,

        process="sequential",  
        
        cache=True,  
        
        output_log_file="AI_workflows/workflow1/config/outputs/logs.json",  
    )

    return crew

# ----------------------------
# STEP 6: MAIN CREWAI RUNNER
# ----------------------------
def inputs_initialization(personal_data, appointment_data, lab_report_extracted_text, search_results):
    inputs = {
        "name": personal_data.get("name"),
        "dob": personal_data.get("dob"),
        "age": personal_data.get("age"),
        "weight": personal_data.get("weight"),
        "height": personal_data.get("height"),
        "symptoms": appointment_data["inputs"].get("symptoms"),
        "recent_medications": appointment_data["inputs"].get("recent_medications"),
        "regular_medications": appointment_data["inputs"].get("regular_medications"),
        "lab_report_extracted_text": lab_report_extracted_text,
        "websearch_results": search_results,
    }
    return inputs

## web search add.

# ----------------------------
# STEP 6: MAIN CREWAI RUNNER
# ----------------------------
def run_crew_workflow1(personal_data, appointment_data):
    """
    This function takes an appointment_data dictionary,
    runs the AI agents, and returns the intermediate report.
    """
    try:
        # Setup
        initialize_api()
        llm = llm_initialization()

        pdf_reader_tool = tool_initialization()
        lab_report_extracted_text = pdf_reader_tool._run(pdf_path=appointment_data["inputs"].get("lab_report"))

        symptoms_text = appointment_data["inputs"].get("symptoms")
        search_query = generate_web_search_query(symptoms_text, llm)
        search_results = perform_web_search(search_query)

        crew = load_agents_and_tasks_and_create_crew(llm)
        inputs = inputs_initialization(personal_data, appointment_data, lab_report_extracted_text, search_results)

        # Run CrewAI workflow
        result = crew.kickoff(inputs=inputs)

        # Post-processing or DB insert can be done here
        return result.raw

    except Exception as e:
        print("❌ CrewAI workflow failed:", e)
        return None
