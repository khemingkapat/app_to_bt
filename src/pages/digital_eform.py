import streamlit as st
from src.pdf_processor.inverter import load_product_config

from src.pages.components.step1_health_gate import render_step1
from src.pages.components.step2_plan_sandbox import render_step2
from src.pages.components.step3_details_intake import render_step3
from src.pages.components.step4_hitl_review import render_step4

import os

# Setup page config
st.set_page_config(layout="wide", page_title="Digital E-Form Portal")

# Load configuration dynamically
config_dir = "./config"
json_files = []
if os.path.exists(config_dir):
    json_files = sorted([f for f in os.listdir(config_dir) if f.endswith(".json")])

if "health_and_accident_insurance.json" in json_files:
    json_files.remove("health_and_accident_insurance.json")
    json_files.insert(0, "health_and_accident_insurance.json")

if not json_files:
    st.warning("⚠️ No plan configuration is available. Please upload or link a product configuration first.")
    st.page_link("src/pages/config_manager.py", label="Go to Product Config Manager ➡️", icon="⚙️")
    st.stop()

# Helper to format config file name
def format_config_name(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".json") else filename
    words = name.replace("_", " ").replace("-", " ").split()
    return " ".join(w.capitalize() for w in words)

# Show dropdown to select product config
selected_file = st.selectbox(
    "Select Product Policy / Plan Config:",
    options=json_files,
    format_func=format_config_name,
    key="digital_eform_selected_config_file_dropdown"
)

# Reset session state if config selection changes
if "selected_config_file" not in st.session_state or st.session_state.selected_config_file != selected_file:
    st.session_state.selected_config_file = selected_file
    st.session_state.step = 1
    st.session_state.form_data = {}
    st.session_state.members_setup = {
        "main_age": 30,
        "cover_spouse": False,
        "spouse_age": 30,
        "child_count": 0,
        "child_1_age": 10,
        "child_2_age": 10,
        "child_3_age": 10,
        
        "comparison_options": [
            {"id": 1, "name": "Option 1", "plan": "Plan 1", "coverage": "ipd", "deductible": "0"},
            {"id": 2, "name": "Option 2", "plan": "Plan 2", "coverage": "ipd_opd_3000", "deductible": "0"},
            {"id": 3, "name": "Option 3", "plan": "Plan 3", "coverage": "ipd_opd_50000", "deductible": "20000"},
        ],
        "selected_option_id": 2,
        "option_counter": 3
    }
    st.session_state.ocr_simulated = {}

# Load selected config
CONFIG_PATH = os.path.join(config_dir, selected_file)
try:
    config = load_product_config(CONFIG_PATH)
except Exception:
    config = {}

if not config:
    st.warning("⚠️ Failed to load the selected configuration. Please verify its content.")
    st.page_link("src/pages/config_manager.py", label="Go to Product Config Manager ➡️", icon="⚙️")
    st.stop()

# Session State Bootstrapping
if "step" not in st.session_state:
    st.session_state.step = 1
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "members_setup" not in st.session_state:
    st.session_state.members_setup = {
        "main_age": 30,
        "cover_spouse": False,
        "spouse_age": 30,
        "child_count": 0,
        "child_1_age": 10,
        "child_2_age": 10,
        "child_3_age": 10,
        
        "comparison_options": [
            {"id": 1, "name": "Option 1", "plan": "Plan 1", "coverage": "ipd", "deductible": "0"},
            {"id": 2, "name": "Option 2", "plan": "Plan 2", "coverage": "ipd_opd_3000", "deductible": "0"},
            {"id": 3, "name": "Option 3", "plan": "Plan 3", "coverage": "ipd_opd_50000", "deductible": "20000"},
        ],
        "selected_option_id": 2,
        "option_counter": 3
    }
else:
    # Ensure backward compatibility for existing/reloading sessions
    setup = st.session_state.members_setup
    if "comparison_options" not in setup:
        setup["comparison_options"] = [
            {"id": 1, "name": "Option 1", "plan": "Plan 1", "coverage": "ipd", "deductible": "0"},
            {"id": 2, "name": "Option 2", "plan": "Plan 2", "coverage": "ipd_opd_3000", "deductible": "0"},
            {"id": 3, "name": "Option 3", "plan": "Plan 3", "coverage": "ipd_opd_50000", "deductible": "20000"},
        ]
        setup["selected_option_id"] = 2
        setup["option_counter"] = 3

if "ocr_simulated" not in st.session_state:
    st.session_state.ocr_simulated = {}

# Header
st.title("🏥 AXA Health Digital Application Portal")
st.write("Pathway B: Native Digital Form with Underwriting & Premium Sandbox")

# Step visualizer
col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.markdown(f"**Step 1: Underwriting Gate** {'🟢' if st.session_state.step > 1 else '🔵' if st.session_state.step == 1 else '⚪'}")
with col_s2:
    st.markdown(f"**Step 2: Plan Sandbox** {'🟢' if st.session_state.step > 2 else '🔵' if st.session_state.step == 2 else '⚪'}")
with col_s3:
    st.markdown(f"**Step 3: Details Intake** {'🟢' if st.session_state.step > 3 else '🔵' if st.session_state.step == 3 else '⚪'}")
with col_s4:
    st.markdown(f"**Step 4: HITL Review** {'🟢' if st.session_state.step > 4 else '🔵' if st.session_state.step == 4 else '⚪'}")

st.divider()

if st.session_state.step == 1:
    render_step1(config)
elif st.session_state.step == 2:
    render_step2(st.session_state.members_setup, config)
elif st.session_state.step == 3:
    render_step3(st.session_state.members_setup, st.session_state.form_data)
elif st.session_state.step == 4:
    render_step4(st.session_state.form_data, st.session_state.members_setup)

