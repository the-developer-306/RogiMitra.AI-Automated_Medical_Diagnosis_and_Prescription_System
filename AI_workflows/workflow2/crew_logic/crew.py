import yaml
import warnings

from crewai import Agent, Task, Crew, LLM
import streamlit as st

warnings.filterwarnings('ignore')

# ----------------------------
# STEP 1: ENV & API INIT
# ----------------------------
def initialize_api():
    if not st.secrets.get("DEEPSEEK_API"):
        raise ValueError("DEEPSEEK_API key not found in .env file")

# ----------------------------
# STEP 2: LLM INIT
# ----------------------------
def llm_initialization():
    return LLM(
        base_url="https://api.deepseek.com",
        api_key=st.secrets["DEEPSEEK_API"],
        model="deepseek/deepseek-chat"
    )

# ----------------------------
# STEP 3: LOAD AGENTS & TASKS
# ----------------------------
def load_agents_and_tasks_and_create_crew(llm):

    # Loading Agent and Task YAML files
    files = {
        'agents': 'AI_workflows/workflow2/config/agents_and_tasks/agents.yaml',
        'tasks': 'AI_workflows/workflow2/config/agents_and_tasks/tasks.yaml'
    }

    configs = {}
    for config_type, file_path in files.items():
        with open(file_path, 'r') as file :
            configs[config_type] = yaml.safe_load(file)

    ## Assigning Loaded Configurations to specific variables
    agents_config = configs['agents']
    tasks_config = configs['tasks']
    
    # --------------------------------- Agent Initialization -----------------------------------------

    Prescription_and_final_Diagnostics_Report_Generator_Agent = Agent(
        config=agents_config['Prescription_and_final_Diagnostics_Report_Generator_Agent'],
        llm=llm,
        tools=[],
        verbose=True
    )
    
    # --------------------------------- Task Initialization -----------------------------------------

    Prescription_and_final_Diagnostics_Report_Generation_Task = Task(
        config=tasks_config['Prescription_and_final_Diagnostics_Report_Generation_Task'],
        agent=Prescription_and_final_Diagnostics_Report_Generator_Agent,
        tools=[],
    )

    # --------------------------------- Crew Creation -----------------------------------------

    crew = Crew(
        
        agents=[
            Prescription_and_final_Diagnostics_Report_Generator_Agent,
        ],
        
        tasks=[
            Prescription_and_final_Diagnostics_Report_Generation_Task,
        ],

        verbose=True,

        process="sequential",  
        
        # cache=True,  
        
        output_log_file="AI_workflows/workflow2/config/outputs/logs.json",  
    )

    return crew

# ----------------------------
# STEP 4: MAIN CREWAI RUNNER
# ----------------------------
def inputs_initialization(intermediate_report, suggestions_for_modifications, doctor_name):
    inputs = {
        "intermediate_report": intermediate_report,
        "suggestions_for_modifications": suggestions_for_modifications,
        "doctor_name": doctor_name
    }
    return inputs

# ----------------------------
# STEP 5: MAIN CREWAI RUNNER
# ----------------------------
def run_crew_workflow2(intermediate_report, suggestions_for_modifications, doctor_name):
    
    try:
        # Setup
        initialize_api()
        llm = llm_initialization()
        crew = load_agents_and_tasks_and_create_crew(llm)
        inputs = inputs_initialization(intermediate_report, suggestions_for_modifications, doctor_name)

        # Run CrewAI workflow
        result = crew.kickoff(inputs=inputs)

        # Post-processing or DB insert can be done here
        return result.raw

    except Exception as e:
        print("❌ CrewAI workflow failed:", e)
        return None
