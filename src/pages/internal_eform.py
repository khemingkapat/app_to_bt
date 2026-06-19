import streamlit as st
import re
import os
from datetime import datetime
from src.pdf_processor.inverter import load_product_config, fill_acroform_pdf
from src.blue_table_tools import fill_blue_table_docx, apply_acceptance_rules
from src.blue_table_tools.docx_generator import calculate_age, resolve_plan_combination
from src.blue_table_tools.schema import BLUETABLE_FIELDS

# Setup page config
st.set_page_config(layout="wide", page_title="AXA Internal Fast-Entry E-Form")

# Custom CSS for modern premium feel & helper alerts
st.markdown("""
<style>
    .title-container {
        background: linear-gradient(135deg, #002b49 0%, #005691 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    }
    .shortcut-badge {
        background-color: #005691;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .field-error {
        color: #ff4b4b;
        font-size: 0.82rem;
        margin-top: -12px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .field-success {
        color: #09ab3b;
        font-size: 0.82rem;
        margin-top: -12px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    div[data-testid="stForm"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    .section-header {
        color: #002b49;
        font-weight: 700;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 5px;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper to format config file name
def format_config_name(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".json") else filename
    words = name.replace("_", " ").replace("-", " ").split()
    return " ".join(w.capitalize() for w in words)

# Load configuration files
config_dir = "./config"
json_files = []
if os.path.exists(config_dir):
    json_files = sorted([f for f in os.listdir(config_dir) if f.endswith(".json")])

if "health_and_accident_insurance.json" in json_files:
    json_files.remove("health_and_accident_insurance.json")
    json_files.insert(0, "health_and_accident_insurance.json")

if not json_files:
    st.warning("⚠️ No plan configuration is available. Please upload or link a product configuration first.")
    st.stop()

# Initialize session state for internal form
defaults = {
    "agent": "",
    "product_name": "",
    "policy_version": "Thai",
    "plan": "",
    "deductible": "",
    "premium": "",
    "effective_date": datetime.today().strftime("%d/%m/%Y"),
    "name": "",
    "dob": "",
    "age": "",
    "id_card_no": "",
    "nationality": "Thai",
    "present_address": "",
    "tel": "",
    "email": "",
    "occupation": "",
    "tax_id": "",
    "beneficiary": "",
    "bene_relation": "",
    "exclusions": "",
    "cover_spouse": "no",
    "spouse_age": "",
    "sp_name": "",
    "sp_dob": "",
    "sp_id_card_no": "",
    "sp_nationality": "Thai",
    "sp_beneficiary": "",
    "sp_bene_relation": "",
    "sp_occupation": "",
    "sp_exclusions": "",
    "child_count": "0",
    "c1_name": "", "c1_dob": "", "c1_id_card_no": "", "c1_nationality": "Thai", "c1_beneficiary": "", "c1_bene_relation": "", "c1_occupation": "", "c1_exclusions": "", "child_1_age": "",
    "c2_name": "", "c2_dob": "", "c2_id_card_no": "", "c2_nationality": "Thai", "c2_beneficiary": "", "c2_bene_relation": "", "c2_occupation": "", "c2_exclusions": "", "child_2_age": "",
    "c3_name": "", "c3_dob": "", "c3_id_card_no": "", "c3_nationality": "Thai", "c3_beneficiary": "", "c3_bene_relation": "", "c3_occupation": "", "c3_exclusions": "", "child_3_age": ""
}

if "internal_form_data" not in st.session_state:
    st.session_state.internal_form_data = defaults.copy()

for k, v in defaults.items():
    sk = f"internal_input_{k}"
    if sk not in st.session_state:
        st.session_state[sk] = v

if "internal_submitted" not in st.session_state:
    st.session_state.internal_submitted = False

# Field Validation logic
def validate_field(key, val):
    if not val:
        return True, ""
    
    if "dob" in key or key == "effective_date":
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", val):
            return False, "Must be in DD/MM/YYYY format"
        try:
            datetime.strptime(val, "%d/%m/%Y")
            return True, ""
        except ValueError:
            return False, "Invalid calendar date"
            
    if key == "email":
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", val):
            return False, "Invalid email address format"
            
    if "id_card_no" in key:
        if not re.match(r"^[A-Za-z0-9]{5,20}$", val):
            return False, "Must be 5-20 alphanumeric characters"
            
    if key == "tel":
        if not re.match(r"^\+?[0-9]{9,15}$", val):
            return False, "Must be 9-15 digits"
            
    if key == "cover_spouse":
        if val.lower() not in ["y", "yes", "n", "no"]:
            return False, "Enter 'y' or 'n'"
            
    if key == "child_count":
        if val not in ["0", "1", "2", "3"]:
            return False, "Enter 0, 1, 2, or 3"
            
    return True, ""

# Get full validation report
def get_validation_report(form_data):
    report = {}
    is_valid = True
    
    # Define required fields
    required_fields = [
        ("agent", "Agent CODE/Name"),
        ("name", "Main Insured Full Name"),
        ("dob", "Main Insured DOB"),
        ("id_card_no", "Main Insured ID/Passport"),
        ("tel", "Main Insured Telephone"),
        ("email", "Main Insured Email"),
        ("present_address", "Main Insured Address"),
        ("beneficiary", "Main Insured Beneficiary"),
        ("bene_relation", "Relation to Beneficiary"),
        ("occupation", "Main Insured Occupation"),
        ("cover_spouse", "Cover Spouse (y/n)"),
        ("child_count", "Number of Children")
    ]
    
    cover_spouse = form_data.get("cover_spouse", "no").lower() in ["y", "yes"]
    if cover_spouse:
        required_fields += [
            ("sp_name", "Spouse Full Name"),
            ("sp_dob", "Spouse DOB"),
            ("sp_id_card_no", "Spouse ID/Passport"),
            ("sp_nationality", "Spouse Nationality"),
            ("sp_beneficiary", "Spouse Beneficiary"),
            ("sp_bene_relation", "Spouse Relation"),
            ("sp_occupation", "Spouse Occupation")
        ]
        
    try:
        child_count = int(form_data.get("child_count", "0"))
    except ValueError:
        child_count = 0
        
    for i in range(1, child_count + 1):
        required_fields += [
            (f"c{i}_name", f"Child {i} Full Name"),
            (f"c{i}_dob", f"Child {i} DOB"),
            (f"c{i}_id_card_no", f"Child {i} ID/Passport"),
            (f"c{i}_nationality", f"Child {i} Nationality"),
            (f"c{i}_beneficiary", f"Child {i} Beneficiary"),
            (f"c{i}_bene_relation", f"Child {i} Relation"),
            (f"c{i}_occupation", f"Child {i} Occupation")
        ]
        
    for key, label in required_fields:
        val = form_data.get(key, "").strip()
        if not val:
            report[key] = {"status": "empty", "message": f"'{label}' is empty"}
            is_valid = False
        else:
            ok, msg = validate_field(key, val)
            if not ok:
                report[key] = {"status": "error", "message": f"'{label}' - {msg}"}
                is_valid = False
            else:
                report[key] = {"status": "ok", "message": ""}
                
    # Run format validation for non-required fields that have input
    for key, val in form_data.items():
        if key not in report:
            val_str = str(val).strip()
            if val_str:
                ok, msg = validate_field(key, val_str)
                if not ok:
                    report[key] = {"status": "error", "message": f"'{key}' - {msg}"}
                    is_valid = False
                    
    return is_valid, report

# Custom styled keyboard input widget
def render_keyboard_field(label, key, placeholder="", required=True, validation_report=None, col=None):
    container = col if col is not None else st
    
    # Calculate age automatically if DOB is valid
    if key == "age" and st.session_state.get("internal_input_dob"):
        derived = calculate_age(st.session_state["internal_input_dob"])
        if derived:
            st.session_state["internal_input_age"] = derived
            
    elif key == "spouse_age" and st.session_state.get("internal_input_sp_dob"):
        derived = calculate_age(st.session_state["internal_input_sp_dob"])
        if derived:
            st.session_state["internal_input_spouse_age"] = derived

    else:
        for i in range(1, 4):
            if key == f"child_{i}_age" and st.session_state.get(f"internal_input_c{i}_dob"):
                derived = calculate_age(st.session_state[f"internal_input_c{i}_dob"])
                if derived:
                    st.session_state[f"internal_input_child_{i}_age"] = derived
                
    # Get status details
    status = "empty"
    msg = ""
    if validation_report and key in validation_report:
        status = validation_report[key]["status"]
        msg = validation_report[key]["message"]
        
    lbl_text = f"{label} *" if required else label
    
    new_val = container.text_input(
        lbl_text,
        placeholder=placeholder,
        key=f"internal_input_{key}"
    )
    
    st.session_state.internal_form_data[key] = new_val
    
    # Display error/success labels below the input
    if status == "error":
        container.markdown(f"<p class='field-error'>⚠️ {msg.split(' - ')[-1]}</p>", unsafe_allow_html=True)
    elif status == "ok" and new_val:
        container.markdown("<p class='field-success'>✓ Valid</p>", unsafe_allow_html=True)
        
    return new_val

# Load selected config file
# We default config to health_and_accident_insurance.json or the selected sidebar dropdown
selected_file = st.session_state.get("internal_selected_config_file_dropdown", "health_and_accident_insurance.json")
CONFIG_PATH = os.path.join(config_dir, selected_file)
try:
    config = load_product_config(CONFIG_PATH)
except Exception:
    config = {}

# Header
st.markdown("""
<div class='title-container'>
    <h1 style='color:white; margin:0;'>⌨️ AXA Internal Fast-Entry E-Form Portal</h1>
    <p style='color:#e2e8f0; margin:5px 0 0 0;'>Optimized keyboard-only data capture workflow for insurance operations</p>
</div>
""", unsafe_allow_html=True)

# Main form layout splits
if not st.session_state.internal_submitted:
    st.markdown("### 📝 Application Data Entry")
    st.info("💡 Tip: Use your keyboard to type and navigate. Press **Enter** to quickly shift focus to the next field.")
    
    # Run validation once to get initial report
    _, initial_report = get_validation_report(st.session_state.internal_form_data)
    
    # SECTION 1: Policy Meta Details
    st.markdown("<div class='section-header'>📋 Policy Meta Details</div>", unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    render_keyboard_field("Agent CODE/Name", "agent", "E.g., AGENT007", required=True, validation_report=initial_report, col=m_col1)
    render_keyboard_field("Effective Date", "effective_date", "DD/MM/YYYY", required=True, validation_report=initial_report, col=m_col2)

    # Render product name and policy version choices
    m_col3, m_col4 = st.columns(2)
    product_options = config.get("product_options", {})
    prod_choices = product_options.get("product_name", {}).get("choices", ["ESSENTIAL", "EASYCARE"])
    selected_prod = m_col3.selectbox("Selected Product", options=prod_choices, key="internal_input_product_name")
    
    policy_choices = product_options.get("policy_version", {}).get("choices", ["Thai", "English"])
    selected_policy = m_col4.selectbox("Policy Version", options=policy_choices, key="internal_input_policy_version")
    
    # Save to form data
    st.session_state.internal_form_data["product_name"] = selected_prod
    st.session_state.internal_form_data["policy_version"] = selected_policy

    # Plan, Deductible, Premium
    m_col5, m_col6, m_col7 = st.columns(3)
    prod_key_map = {
        "ESSENTIAL": "SmartCare Essential",
        "EASYCARE": "EasyCare Visa"
    }
    prod_display_name = prod_key_map.get(selected_prod, "SmartCare Essential")
    prod_config = product_options.get("products", {}).get(prod_display_name, {})
    
    plan_choices = prod_config.get("plan_tier", {}).get("choices", ["ESSENTIAL1", "ESSENTIAL2", "ESSENTIAL3", "ESSENTIAL4"])
    if selected_prod == "EASYCARE":
        plan_choices = ["VISA1", "VISA2"]
        
    selected_plan = m_col5.selectbox("Plan Tier", options=plan_choices, key="internal_input_plan")
    
    ded_choices = prod_config.get("deductible", {}).get("choices", ["0", "20k", "40k", "100k", "200k"])
    if selected_prod == "EASYCARE":
        ded_choices = ["100k", "200k", "300k"]
    selected_ded = m_col6.selectbox("Deductible", options=ded_choices, key="internal_input_deductible")
    
    # Save to form data
    st.session_state.internal_form_data["plan"] = selected_plan
    st.session_state.internal_form_data["deductible"] = selected_ded

    # We can also add optional benefits for ESSENTIAL
    selected_benefit = ""
    selected_opd = ""
    if selected_prod == "ESSENTIAL":
        m_col8, m_col9 = st.columns(2)
        opt_benefit_choices = prod_config.get("optional_benefit", {}).get("choices", ["IPD", "IPD+OPD", "IPD+OPD+WELLNESS"])
        selected_benefit = m_col8.selectbox("Optional Benefit", options=opt_benefit_choices, key="internal_input_benefit")
        
        opd_choices = prod_config.get("opd_choice", {}).get("choices", ["3k * 30 times / year", "50k per year"])
        selected_opd = m_col9.selectbox("OPD Choice Limit", options=opd_choices, key="internal_input_opd_choice")

        # Save these components
        st.session_state.internal_form_data["benefit"] = selected_benefit
        st.session_state.internal_form_data["opd_choice"] = selected_opd
    
    # Premium text input
    selected_premium = render_keyboard_field("Premium", "premium", "E.g., 35,000", required=True, validation_report=initial_report, col=m_col7)
    
    # SECTION 2: Main Insured Details
    st.markdown("<div class='section-header'>👤 Main Insured Details</div>", unsafe_allow_html=True)
    mi_col1, mi_col2 = st.columns(2)
    render_keyboard_field("Full Name", "name", "First and Last Name", required=True, validation_report=initial_report, col=mi_col1)
    render_keyboard_field("ID Card / Passport No.", "id_card_no", "13 digits or passport string", required=True, validation_report=initial_report, col=mi_col2)
    
    mi_col3, mi_col4, mi_col5 = st.columns(3)
    render_keyboard_field("Date of Birth", "dob", "DD/MM/YYYY", required=True, validation_report=initial_report, col=mi_col3)
    render_keyboard_field("Age", "age", "Auto-calculated", required=False, validation_report=initial_report, col=mi_col4)
    render_keyboard_field("Nationality", "nationality", "E.g., Thai", required=True, validation_report=initial_report, col=mi_col5)
    
    render_keyboard_field("Personal / Present Address", "present_address", "Full address string", required=True, validation_report=initial_report)
    
    mi_col6, mi_col7, mi_col8 = st.columns(3)
    render_keyboard_field("Telephone No.", "tel", "E.g., 0812345678", required=True, validation_report=initial_report, col=mi_col6)
    render_keyboard_field("Email Address", "email", "E.g., customer@email.com", required=True, validation_report=initial_report, col=mi_col7)
    render_keyboard_field("Tax ID No. (Optional)", "tax_id", "Tax identification code", required=False, validation_report=initial_report, col=mi_col8)
    
    mi_col9, mi_col10, mi_col11 = st.columns(3)
    render_keyboard_field("Beneficiary Name", "beneficiary", "Full Name", required=True, validation_report=initial_report, col=mi_col9)
    render_keyboard_field("Relation to Beneficiary", "bene_relation", "E.g., Spouse, Child", required=True, validation_report=initial_report, col=mi_col10)
    render_keyboard_field("Occupation", "occupation", "E.g., Engineer", required=True, validation_report=initial_report, col=mi_col11)
    
    render_keyboard_field("Pre-existing Conditions or Exclusions", "exclusions", "E.g., Asthma (If none, leave blank or type 'None')", required=False, validation_report=initial_report)
    
    # SECTION 3: Family Setup
    st.markdown("<div class='section-header'>👨‍👩‍👧 Family Coverage Configuration</div>", unsafe_allow_html=True)
    fam_col1, fam_col2 = st.columns(2)
    cover_sp_val = render_keyboard_field("Cover Spouse? (y/n)", "cover_spouse", "Type 'y' or 'n'", required=True, validation_report=initial_report, col=fam_col1)
    child_cnt_val = render_keyboard_field("Number of Children (0-3)", "child_count", "Type 0, 1, 2, or 3", required=True, validation_report=initial_report, col=fam_col2)
    
    is_spouse_covered = cover_sp_val.lower() in ["y", "yes"]
    try:
        num_children = int(child_cnt_val)
    except ValueError:
        num_children = 0
        
    # SECTION 4: Spouse Details
    if is_spouse_covered:
        st.markdown("<div class='section-header'>💍 Spouse Details</div>", unsafe_allow_html=True)
        sp_col1, sp_col2 = st.columns(2)
        render_keyboard_field("Spouse Full Name", "sp_name", "First and Last Name", required=True, validation_report=initial_report, col=sp_col1)
        render_keyboard_field("Spouse ID Card / Passport No.", "sp_id_card_no", "13 digits or passport string", required=True, validation_report=initial_report, col=sp_col2)
        
        sp_col3, sp_col4, sp_col5 = st.columns(3)
        render_keyboard_field("Spouse Date of Birth", "sp_dob", "DD/MM/YYYY", required=True, validation_report=initial_report, col=sp_col3)
        render_keyboard_field("Spouse Age", "spouse_age", "Auto-calculated", required=False, validation_report=initial_report, col=sp_col4)
        render_keyboard_field("Spouse Nationality", "sp_nationality", "E.g., Thai", required=True, validation_report=initial_report, col=sp_col5)
        
        sp_col6, sp_col7, sp_col8 = st.columns(3)
        render_keyboard_field("Spouse Beneficiary Name", "sp_beneficiary", "Full Name", required=True, validation_report=initial_report, col=sp_col6)
        render_keyboard_field("Spouse Relation to Beneficiary", "sp_bene_relation", "E.g., Spouse", required=True, validation_report=initial_report, col=sp_col7)
        render_keyboard_field("Spouse Occupation", "sp_occupation", "E.g., Accountant", required=True, validation_report=initial_report, col=sp_col8)
        
        render_keyboard_field("Spouse Pre-existing Conditions / Exclusions", "sp_exclusions", "E.g., Hypertension (If none, leave blank)", required=False, validation_report=initial_report)
        
    # SECTION 5: Children Details
    for i in range(1, num_children + 1):
        st.markdown(f"<div class='section-header'>👶 Child {i} Details</div>", unsafe_allow_html=True)
        ch_col1, ch_col2 = st.columns(2)
        render_keyboard_field(f"Child {i} Full Name", f"c{i}_name", "First and Last Name", required=True, validation_report=initial_report, col=ch_col1)
        render_keyboard_field(f"Child {i} ID Card / Passport No.", f"c{i}_id_card_no", "ID No.", required=True, validation_report=initial_report, col=ch_col2)
        
        ch_col3, ch_col4, ch_col5 = st.columns(3)
        render_keyboard_field(f"Child {i} Date of Birth", f"c{i}_dob", "DD/MM/YYYY", required=True, validation_report=initial_report, col=ch_col3)
        render_keyboard_field(f"Child {i} Age", f"child_{i}_age", "Auto-calculated", required=False, validation_report=initial_report, col=ch_col4)
        render_keyboard_field(f"Child {i} Nationality", f"c{i}_nationality", "E.g., Thai", required=True, validation_report=initial_report, col=ch_col5)
        
        ch_col6, ch_col7, ch_col8 = st.columns(3)
        render_keyboard_field(f"Child {i} Beneficiary Name", f"c{i}_beneficiary", "Full Name", required=True, validation_report=initial_report, col=ch_col6)
        render_keyboard_field(f"Child {i} Relation to Beneficiary", f"c{i}_bene_relation", "E.g., Mother", required=True, validation_report=initial_report, col=ch_col7)
        render_keyboard_field(f"Child {i} Occupation / Education", f"c{i}_occupation", "E.g., Student", required=True, validation_report=initial_report, col=ch_col8)
        
        render_keyboard_field(f"Child {i} Pre-existing Conditions / Exclusions", f"c{i}_exclusions", "E.g., None", required=False, validation_report=initial_report)

    # Cleanups of conditional sections directly on form_data dictionary and widget session state
    if not is_spouse_covered:
        for sk in ["sp_name", "sp_dob", "sp_id_card_no", "sp_nationality", "sp_beneficiary", "sp_bene_relation", "sp_occupation", "sp_exclusions", "spouse_age"]:
            st.session_state.internal_form_data[sk] = ""
            st.session_state[f"internal_input_{sk}"] = ""
    for idx in range(num_children + 1, 4):
        for ck in [f"c{idx}_name", f"c{idx}_dob", f"c{idx}_id_card_no", f"c{idx}_nationality", f"c{idx}_beneficiary", f"c{idx}_bene_relation", f"c{idx}_occupation", f"c{idx}_exclusions", f"child_{idx}_age"]:
            st.session_state.internal_form_data[ck] = ""
            st.session_state[f"internal_input_{ck}"] = ""

    st.markdown("---")
    
    # Form Actions
    act_col1, act_col2 = st.columns([1, 1])
    with act_col1:
        if st.button("Reset Form (Alt + C) 🔄", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith("internal_input_") or k in ["internal_form_data", "internal_submitted"]:
                    del st.session_state[k]
            st.rerun()
            
    with act_col2:
        if st.button("Generate Deliverables (Alt + S) 🚀", type="primary", use_container_width=True):
            is_valid_click, report_click = get_validation_report(st.session_state.internal_form_data)
            if is_valid_click:
                st.session_state.internal_submitted = True
                st.rerun()
            else:
                st.error("🛑 **Cannot Proceed:** Please resolve all validation errors and fill in all required fields first.")

else:
    # Submissions Details Review
    st.markdown("### 🔍 Verification & Deliverables Generation")
    
    # Run validation checks
    is_valid_final, final_report = get_validation_report(st.session_state.internal_form_data)
    
    col_review, col_action = st.columns([2, 1], gap="large")
    
    # Prepare form data
    data_to_save = st.session_state.internal_form_data.copy()
    if config and "pdf_id" in config:
        data_to_save["pdf_id"] = config["pdf_id"]
        
    # Construct plan value for resolve_plan_combination
    if data_to_save.get("product_name") == "EASYCARE":
        plan_val = data_to_save.get("plan", "")
    else:
        # ESSENTIAL
        tier = data_to_save.get("plan", "") # e.g. ESSENTIAL1
        benefit = data_to_save.get("benefit", "IPD") # e.g. IPD+OPD
        opd = data_to_save.get("opd_choice", "") # e.g. 3k * 30 times / year
        if benefit == "IPD":
            plan_val = f"{tier}-IPD"
        else:
            plan_val = f"{tier}-{benefit}({opd})"

    data_to_save["plan"] = plan_val
    data_to_save["deductible"] = data_to_save.get("deductible", "")
    data_to_save["premium"] = data_to_save.get("premium", "")
    data_to_save["product_name"] = data_to_save.get("product_name", "")
    data_to_save["policy_version"] = data_to_save.get("policy_version", "")
    
    data_to_save = resolve_plan_combination(data_to_save)
    data_to_save = apply_acceptance_rules(data_to_save)
    
    with col_review:
        st.subheader("🔵 Compiled BlueTable Fields")
        
        # Show fields table
        rows = []
        for label, key in BLUETABLE_FIELDS:
            val = data_to_save.get(key, "")
            if val:
                rows.append({"Field Label": label, "Variable Key": key, "Value": val})
                
        st.table(rows)
        
    with col_action:
        if not is_valid_final:
            st.error("🛑 **Deliverables Blocked:** Some fields are empty or off-format. Please go back and correct them before generating deliverables.")
            if st.button("⬅️ Edit Current Values", use_container_width=True, type="primary"):
                st.session_state.internal_submitted = False
                st.rerun()
        else:
            st.subheader("📥 Downstream Deliverables")
            
            template_docx_path = "./resources/BlueTable.docx"
            if os.path.exists(template_docx_path):
                with st.spinner("Generating filled BlueTable DOCX..."):
                    try:
                        docx_stream = fill_blue_table_docx(template_docx_path, data_to_save)
                        st.download_button(
                            "⬇️ Download Filled BlueTable DOCX",
                            data=docx_stream.getvalue(),
                            file_name="bluetable_filled.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"Failed to generate DOCX: {e}")
            else:
                st.error(f"Template DOCX not found at: {template_docx_path}")
                
            st.write("---")
            
            template_pdf_path = "./resources/OriginalApplication.pdf"
            if os.path.exists(template_pdf_path):
                with st.spinner("Generating official pre-filled PDF..."):
                    try:
                        filled_pdf_stream = fill_acroform_pdf(template_pdf_path, data_to_save)
                        st.download_button(
                            "⬇️ Download Pre-filled Official PDF",
                            data=filled_pdf_stream.getvalue(),
                            file_name="PreFilled_Application.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                        st.info("💡 The output PDF contains interactive AcroForm fields pre-populated with customer data.")
                    except Exception as e:
                        st.error(f"Failed to generate pre-filled PDF: {e}")
            else:
                st.error(f"Template PDF not found at: {template_pdf_path}")
                
            if st.button("🔄 Start New Fast-Entry", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k.startswith("internal_input_") or k in ["internal_form_data", "internal_submitted"]:
                        del st.session_state[k]
                st.rerun()
                
            if st.button("⬅️ Edit Current Values", use_container_width=True):
                st.session_state.internal_submitted = False
                st.rerun()

# Run the validation report at the bottom of the script for up-to-date sidebar rendering
is_valid, report = get_validation_report(st.session_state.internal_form_data)
total_fields = len(report)
valid_fields = sum(1 for k, v in report.items() if v["status"] == "ok")
progress_percentage = int((valid_fields / max(total_fields, 1)) * 100)

with st.sidebar:
    st.subheader("⚙️ Config & Intake Progress")
    
    selected_file = st.selectbox(
        "Product Policy / Plan Config:",
        options=json_files,
        format_func=format_config_name,
        key="internal_selected_config_file_dropdown"
    )
    
    st.divider()
    
    st.markdown("### 📊 Form Completeness")
    st.progress(valid_fields / max(total_fields, 1))
    st.markdown(f"**Progress:** {progress_percentage}% ({valid_fields}/{total_fields} fields)")
    
    errors = [v["message"] for k, v in report.items() if v["status"] == "error"]
    empties = [v["message"] for k, v in report.items() if v["status"] == "empty"]
    
    if errors:
        st.markdown("**🛑 Validation Errors:**")
        for err in errors:
            st.markdown(f"- <span style='color:#ff4b4b;'>{err}</span>", unsafe_allow_html=True)
            
    if empties:
        st.markdown("**⏳ Pending Required Fields:**")
        for emp in empties[:8]:
            st.markdown(f"- <span style='color:#666;'>{emp}</span>", unsafe_allow_html=True)
        if len(empties) > 8:
            st.markdown(f"*...and {len(empties) - 8} more required fields.*")
            
    if not errors and not empties:
        st.success("✨ All required fields filled & valid!")
        
    st.divider()
    st.markdown("### 🎹 Keyboard Shortcuts")
    st.markdown("""
    - <span class='shortcut-badge'>Enter</span> / <span class='shortcut-badge'>Tab</span>: Next field
    - <span class='shortcut-badge'>Shift + Enter</span>: Previous field
    - <span class='shortcut-badge'>Alt + S</span>: Submit & Generate
    - <span class='shortcut-badge'>Alt + C</span>: Reset Form
    """, unsafe_allow_html=True)

# Client-side JavaScript Autofocus & Navigation Injection
st.iframe("""
<script>
const doc = window.parent.document;

function getLabel(input) {
    const parent = input.closest('[data-testid="stTextInput"], [data-testid="stNumberInput"]');
    if (parent) {
        const labelEl = parent.querySelector('label');
        if (labelEl) return labelEl.innerText.trim();
    }
    return null;
}

function restoreFocus() {
    const savedLabel = localStorage.getItem('lastFocusedInputLabel');
    if (savedLabel) {
        const inputs = Array.from(doc.querySelectorAll('input[type="text"], input[type="number"]'));
        for (const inp of inputs) {
            if (getLabel(inp) === savedLabel) {
                if (doc.activeElement !== inp) {
                    inp.focus();
                }
                break;
            }
        }
    }
}

function setupListeners() {
    const inputs = Array.from(doc.querySelectorAll('input[type="text"], input[type="number"]'));
    inputs.forEach((inp) => {
        if (inp.dataset.keyboardBound) return;
        inp.dataset.keyboardBound = "true";
        
        inp.addEventListener('focus', () => {
            const lbl = getLabel(inp);
            if (lbl) {
                localStorage.setItem('lastFocusedInputLabel', lbl);
            }
        });
        
        inp.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const nextIdx = inputs.indexOf(inp) + 1;
                if (nextIdx < inputs.length) {
                    const nextInp = inputs[nextIdx];
                    nextInp.focus();
                    nextInp.select();
                    const nextLbl = getLabel(nextInp);
                    if (nextLbl) {
                        localStorage.setItem('lastFocusedInputLabel', nextLbl);
                    }
                } else {
                    // Last input focuses the submit button
                    const btns = Array.from(doc.querySelectorAll('button'));
                    const submitBtn = btns.find(b => b.innerText.includes('Generate') || b.innerText.includes('Deliverables'));
                    if (submitBtn) {
                        submitBtn.focus();
                    }
                }
            }
        });
    });
}

// Global hotkeys
function setupHotkeys() {
    if (doc.dataset.hotkeysBound) return;
    doc.dataset.hotkeysBound = "true";
    
    doc.addEventListener('keydown', (e) => {
        // Alt + S for Submit
        if (e.altKey && e.key.toLowerCase() === 's') {
            e.preventDefault();
            const btns = Array.from(doc.querySelectorAll('button'));
            const submitBtn = btns.find(b => b.innerText.includes('Generate') || b.innerText.includes('Deliverables'));
            if (submitBtn) submitBtn.click();
        }
        // Alt + C for Reset
        if (e.altKey && e.key.toLowerCase() === 'c') {
            e.preventDefault();
            const btns = Array.from(doc.querySelectorAll('button'));
            const clearBtn = btns.find(b => b.innerText.includes('Reset') || b.innerText.includes('Start New'));
            if (clearBtn) clearBtn.click();
        }
    });
}

// Initialize
setupListeners();
restoreFocus();
setupHotkeys();

const observer = new MutationObserver(() => {
    setupListeners();
    restoreFocus();
    setupHotkeys();
});
observer.observe(doc.body, { childList: true, subtree: true });
</script>
""", height=1)
