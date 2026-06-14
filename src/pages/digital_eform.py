import json
import os
import time
from io import BytesIO
import streamlit as st
from src.pdf_processor.inverter import fill_acroform_pdf, load_product_config
from src.blue_table_tools import calculate_single_option_premium

# Setup page config
st.set_page_config(layout="wide", page_title="Digital E-Form Portal")

# Load configuration
CONFIG_PATH = "./config/health_and_accident.json"
config = load_product_config(CONFIG_PATH)

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

# ── STEP 1: HARD-NO HEALTH GATE ────────────────────────────────────────────
if st.session_state.step == 1:
    st.subheader("📋 Step 1: Health Pre-Screening Questionnaire")
    st.write("To protect your time, we screen key medical history upfront. Please select if any applicant in your family has ever been diagnosed with or received treatment for any of the following:")

    conditions = config.get("underwriting_rules", {}).get("critical_conditions", [])
    # TODO: Jules to implement dynamic follow-up questions from config schema if certain non-critical conditions are checked.
    has_declined = False
    
    col_c1, col_c2 = st.columns(2)
    half = (len(conditions) + 1) // 2
    
    with col_c1:
        for cond in conditions[:half]:
            val = st.checkbox(cond, key=f"cond_{cond}")
            if val:
                has_declined = True
    with col_c2:
        for cond in conditions[half:]:
            val = st.checkbox(cond, key=f"cond_{cond}")
            if val:
                has_declined = True

    st.markdown("---")

    if has_declined:
        st.error("⚠️ **Automatic Decline Notice**\n\nBased on your selected health conditions, we cannot approve this application online. This is aligned with our underwriting guidelines to ensure absolute accuracy and risk management. Thank you for your interest.")
        st.button("Start Over", on_click=lambda: st.session_state.clear(), type="primary")
    else:
        if st.button("Proceed to Plan Sandbox ➡️", type="primary"):
            st.session_state.step = 2
            st.rerun()

# ── STEP 2: PLAN SANDBOX & PREMIUM ENGINE ──────────────────────────────────
elif st.session_state.step == 2:
    st.subheader("🎨 Step 2: Interactive Plan & Premium Sandbox")
    st.write("Input family structure (static params) and customize Option A, B, and C (dynamic params) to compare them side-by-side.")

    col_setup, col_pricing = st.columns([1.5, 3.5], gap="large")
    
    setup = st.session_state.members_setup

    with col_setup:
        st.subheader("👨‍👩‍👧 Static Parameters: Family Structure")
        
        # Main Insured
        setup["main_age"] = st.number_input("Main Insured Age", min_value=0, max_value=64, value=setup["main_age"])
        
        # Spouse cover
        setup["cover_spouse"] = st.checkbox("Cover Spouse", value=setup["cover_spouse"])
        if setup["cover_spouse"]:
            setup["spouse_age"] = st.number_input("Spouse Age", min_value=18, max_value=64, value=setup["spouse_age"])
            
        # Children cover
        setup["child_count"] = st.slider("Number of Children to Cover", min_value=0, max_value=3, value=setup["child_count"])
        
        for i in range(1, setup["child_count"] + 1):
            setup[f"child_{i}_age"] = st.number_input(f"Child {i} Age", min_value=0, max_value=17, value=setup.get(f"child_{i}_age", 10))

    with col_pricing:
        st.subheader("🏷️ Dynamic Parameters: Compare Custom Options")
        st.write("Configure each column independently to compare plan level, coverage, and deductible combinations.")

        # Definitions
        coverage_labels = {
            "ipd": "IPD Only",
            "ipd_opd_3000": "IPD + OPD 3,000 THB/visit (30 visits/year)",
            "ipd_opd_3000_wellness": "IPD + OPD 3,000 THB + Wellness",
            "ipd_opd_50000": "IPD + OPD 50,000 THB/year",
            "ipd_opd_50000_wellness": "IPD + OPD 50,000 THB + Wellness"
        }
        
        deductibles = config.get("pricing", {}).get("deductibles", [])
        ded_labels = {d["key"]: d["label"] for d in deductibles}

        # 1. Configuration form to add a new option
        st.markdown("### **➕ Add Custom Combination to Compare**")
        col_new_plan, col_new_cov, col_new_ded = st.columns(3)
        with col_new_plan:
            new_plan = st.selectbox(
                "Select Plan",
                ["Plan 1", "Plan 2", "Plan 3", "Plan 4"],
                key="new_plan_sel"
            )
        with col_new_cov:
            new_coverage = st.selectbox(
                "Select Coverage",
                list(coverage_labels.keys()),
                format_func=lambda x: coverage_labels[x],
                key="new_cov_sel"
            )
        with col_new_ded:
            new_ded = st.selectbox(
                "Select Deductible",
                list(ded_labels.keys()),
                format_func=lambda x: ded_labels[x],
                key="new_ded_sel"
            )
        
        if st.button("➕ Add to Comparison", use_container_width=True):
            options = setup.setdefault("comparison_options", [])
            setup["option_counter"] = setup.get("option_counter", len(options)) + 1
            new_id = setup["option_counter"]
            
            # Check if this combo is already added
            exists = any(
                o["plan"] == new_plan and o["coverage"] == new_coverage and o["deductible"] == new_ded
                for o in options
            )
            if exists:
                st.warning("⚠️ This combination is already in the comparison.")
            else:
                options.append({
                    "id": new_id,
                    "name": f"Option {new_id}",
                    "plan": new_plan,
                    "coverage": new_coverage,
                    "deductible": new_ded
                })
                # If nothing was selected before, select this one
                if "selected_option_id" not in setup or not any(o["id"] == setup["selected_option_id"] for o in options):
                    setup["selected_option_id"] = new_id
                st.rerun()

        # Render dynamic comparison table
        options = setup.get("comparison_options", [])
        if not options:
            options = [
                {"id": 1, "name": "Option 1", "plan": "Plan 1", "coverage": "ipd", "deductible": "0"},
                {"id": 2, "name": "Option 2", "plan": "Plan 2", "coverage": "ipd_opd_3000", "deductible": "0"},
                {"id": 3, "name": "Option 3", "plan": "Plan 3", "coverage": "ipd_opd_50000", "deductible": "20000"}
            ]
            setup["comparison_options"] = options
            setup["selected_option_id"] = 2
            setup["option_counter"] = 3

        st.divider()
        st.subheader("📊 Comparison Matrix")
        
        # Calculate premiums for all options in comparison
        options_data = []
        for opt in options:
            res = calculate_single_option_premium(opt["plan"], opt["coverage"], int(opt["deductible"]), setup, config)
            options_data.append({
                "id": opt["id"],
                "name": opt["name"],
                "plan": opt["plan"],
                "coverage": opt["coverage"],
                "deductible": opt["deductible"],
                "res": res
            })
            
        # Render clean Markdown Table
        h1 = "| Parameter / Option |"
        h2 = "| :--- |"
        
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            header = f"**{opt['name']} (Selected) ✅**" if is_sel else f"**{opt['name']}**"
            h1 += f" {header} |"
            h2 += " :---: |"
            
        r_plan = "| **Plan Tier** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['plan']}**" if is_sel else f"{opt['plan']}"
            r_plan += f" {val} |"
            
        r_cov = "| **Coverage Type** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            lbl = coverage_labels[opt["coverage"]]
            val = f"**{lbl}**" if is_sel else f"{lbl}"
            r_cov += f" {val} |"
            
        r_ded = "| **Deductible** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            lbl = ded_labels[opt["deductible"]]
            val = f"**{lbl}**" if is_sel else f"{lbl}"
            r_ded += f" {val} |"
            
        r_ipd = "| **IPD Limit** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['coverage']}**" if is_sel else f"{opt['res']['coverage']}"
            r_ipd += f" {val} |"
            
        r_room = "| **Room Limit** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['room_limit']} THB**" if is_sel else f"{opt['res']['room_limit']} THB"
            r_room += f" {val} |"
            
        r_tot = "| **Total Annual Premium** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['total']:,.0f} THB**" if is_sel else f"{opt['res']['total']:,.0f} THB"
            r_tot += f" {val} |"
            
        r_avg = "| **Average / Person** |"
        for opt in options_data:
            is_sel = (setup.get("selected_option_id") == opt["id"])
            val = f"**{opt['res']['avg']:,.0f} THB**" if is_sel else f"{opt['res']['avg']:,.0f} THB"
            r_avg += f" {val} |"
            
        table_md = f"{h1}\n{h2}\n{r_plan}\n{r_cov}\n{r_ded}\n{r_ipd}\n{r_room}\n{r_tot}\n{r_avg}"
        st.markdown(table_md)

        # Actions for removing compared options
        st.markdown("🗑️ **Remove Options from Comparison:**")
        rem_cols = st.columns(max(len(options_data), 1))
        for idx, opt in enumerate(options_data):
            with rem_cols[idx]:
                if st.button(f"Remove {opt['name']} ❌", key=f"rem_opt_{opt['id']}", disabled=(len(options_data) <= 1)):
                    # If we remove the selected one, select another one
                    if setup.get("selected_option_id") == opt["id"]:
                        remaining = [o for o in options_data if o["id"] != opt["id"]]
                        setup["selected_option_id"] = remaining[0]["id"]
                    setup["comparison_options"] = [o for o in options if o["id"] != opt["id"]]
                    st.rerun()

        st.divider()
        st.subheader("Select Final Choice for Application")
        option_names = [o["name"] for o in options_data]
        selected_name = next((o["name"] for o in options_data if o["id"] == setup.get("selected_option_id")), option_names[0])
        selected_option = st.radio(
            "Apply Selected Combination",
            options=option_names,
            index=option_names.index(selected_name),
            horizontal=True
        )
        # Update selected option id matching this name
        setup["selected_option_id"] = next(o["id"] for o in options_data if o["name"] == selected_option)
        
        # Family discount indicator
        o_count = 1 + (1 if setup["cover_spouse"] else 0) + setup["child_count"]
        if o_count >= 2 and o_count <= 3:
            st.info("🎉 Family Volume Discount: **5% off** has been automatically applied to all options.")
        elif o_count >= 4:
            st.info("🎉 Family Volume Discount: **10% off** has been automatically applied to all options.")

    st.markdown("---")
    
    col_b, col_n = st.columns([1, 1])
    with col_b:
        if st.button("⬅️ Back to Health Gate"):
            st.session_state.step = 1
            st.rerun()
    with col_n:
        if st.button("Proceed to Details Intake ➡️", type="primary", use_container_width=True):
            st.session_state.members_setup = setup
            
            # Fetch pricing details for the chosen option
            chosen_opt = next(o for o in options_data if o["id"] == setup["selected_option_id"])
            
            # Populate form_data for output mapping
            st.session_state.form_data["plan"] = chosen_opt["plan"]
            st.session_state.form_data["deductible"] = ded_labels[chosen_opt["deductible"]]
            st.session_state.form_data["premium"] = f"{chosen_opt['res']['total']:,.0f}"
            st.session_state.step = 3
            st.rerun()

# ── STEP 3: DETAILS INTAKE & OCR SIMULATION ────────────────────────────────
elif st.session_state.step == 3:
    st.subheader("📝 Step 3: Progressive Personal Info Blocks")
    st.write("Please fill in the personal information. To speed up the intake and ensure 100% accuracy, you can upload your National ID card to automatically pre-fill details.")
    
    setup = st.session_state.members_setup
    form_data = st.session_state.form_data

    # Helper function to render a standard text field
    def render_field(label_text, bt_key, section, placeholder="", is_required=True):
        full_key = f"{section}_{bt_key}"
        is_prefilled = full_key in st.session_state.ocr_simulated
        
        if is_prefilled:
            st.warning("⚠️ Review pre-filled info")
            
        val = st.text_input(
            f"{label_text} {'*' if is_required else ''}",
            value=form_data.get(bt_key, ""),
            placeholder=placeholder,
            key=f"input_field_{full_key}"
        )
        form_data[bt_key] = val
        return val

    # Helper function to simulate OCR Scanning
    def run_ocr_simulation(section_name, id_name, id_dob, id_addr):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent_complete in range(0, 101, 10):
            time.sleep(0.15)
            progress_bar.progress(percent_complete)
            status_text.text(f"🔍 Analyzing ID card layout... {percent_complete}%")
            
        status_text.success("✨ ID card processed! Form pre-populated successfully.")
        time.sleep(0.5)
        
        if section_name == "Main":
            form_data["dob"] = id_dob
            form_data["present_address"] = id_addr
            form_data["tel"] = "0812345678"
            form_data["email"] = "alex.mercer@example.com"
            form_data["nationality"] = "Thai"
            form_data["occupation"] = "Engineer"
            form_data["beneficiary"] = "Jane Mercer"
            form_data["bene_relation"] = "Mother"
            
            # Leave Name and ID card empty as requested
            form_data["name"] = ""
            form_data["id_card_no"] = ""
            
            st.session_state["input_field_Main_dob"] = id_dob
            st.session_state["input_field_Main_present_address"] = id_addr
            st.session_state["input_field_Main_tel"] = "0812345678"
            st.session_state["input_field_Main_email"] = "alex.mercer@example.com"
            st.session_state["input_field_Main_nationality"] = "Thai"
            st.session_state["input_field_Main_occupation"] = "Engineer"
            st.session_state["input_field_Main_beneficiary"] = "Jane Mercer"
            st.session_state["input_field_Main_bene_relation"] = "Mother"
            st.session_state["input_field_Main_name"] = ""
            st.session_state["input_field_Main_id_card_no"] = ""
            
            st.session_state.ocr_simulated["Main_dob"] = True
            st.session_state.ocr_simulated["Main_present_address"] = True
            st.session_state.ocr_simulated["Main_tel"] = True
            st.session_state.ocr_simulated["Main_email"] = True
            st.session_state.ocr_simulated["Main_nationality"] = True
            st.session_state.ocr_simulated["Main_occupation"] = True
            st.session_state.ocr_simulated["Main_beneficiary"] = True
            st.session_state.ocr_simulated["Main_bene_relation"] = True
            
        elif section_name == "Spouse":
            form_data["sp_dob"] = id_dob
            form_data["sp_nationality"] = "Thai"
            form_data["sp_occupation"] = "Accountant"
            form_data["sp_beneficiary"] = "Alex Mercer"
            form_data["sp_bene_relation"] = "Husband"
            
            # Leave Spouse Name and ID card empty
            form_data["sp_name"] = ""
            form_data["sp_id_card_no"] = ""
            
            st.session_state["input_field_Spouse_sp_dob"] = id_dob
            st.session_state["input_field_Spouse_sp_nationality"] = "Thai"
            st.session_state["input_field_Spouse_sp_occupation"] = "Accountant"
            st.session_state["input_field_Spouse_sp_beneficiary"] = "Alex Mercer"
            st.session_state["input_field_Spouse_sp_bene_relation"] = "Husband"
            st.session_state["input_field_Spouse_sp_name"] = ""
            st.session_state["input_field_Spouse_sp_id_card_no"] = ""
            
            st.session_state.ocr_simulated["Spouse_sp_dob"] = True
            st.session_state.ocr_simulated["Spouse_sp_nationality"] = True
            st.session_state.ocr_simulated["Spouse_sp_occupation"] = True
            st.session_state.ocr_simulated["Spouse_sp_beneficiary"] = True
            st.session_state.ocr_simulated["Spouse_sp_bene_relation"] = True

    # 1. Main Insured Details
    st.subheader("👤 Main Insured Details")
    
    col_upload, col_inputs = st.columns([1, 2], gap="large")
    
    with col_upload:
        st.write("Upload National ID to auto-fill:")
        uploaded_id = st.file_uploader("Upload Main Insured ID Card Image", type=["jpg", "png", "pdf"])
        if uploaded_id:
            # TODO: Jules to integrate with actual OCR API (e.g. Google Cloud Document AI or custom OCR server) in production to replace this simulated scanning process.
            if st.button("📸 Scan ID Card (Simulation)", key="btn_scan_main"):
                run_ocr_simulation(
                    "Main",
                    "Alex Mercer",
                    "31/10/1990",
                    "123 BlueTable Boulevard, Bangkok, Thailand"
                )
                st.rerun()

    with col_inputs:
        render_field("Full Name", "name", "Main")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            render_field("Date of Birth", "dob", "Main", placeholder="DD/MM/YYYY")
        with col_d2:
            render_field("ID Card / Passport No.", "id_card_no", "Main")
            
        render_field("Present Address", "present_address", "Main")
        
        col_d3, col_d4 = st.columns(2)
        with col_d3:
            render_field("Telephone No.", "tel", "Main")
        with col_d4:
            render_field("Email Address", "email", "Main")
            
        col_d5, col_d6 = st.columns(2)
        with col_d5:
            render_field("Nationality", "nationality", "Main")
        with col_d6:
            render_field("Occupation", "occupation", "Main")
            
        col_d7, col_d8 = st.columns(2)
        with col_d7:
            render_field("Beneficiary Name", "beneficiary", "Main")
        with col_d8:
            render_field("Relation to Beneficiary", "bene_relation", "Main")
            
        render_field("Tax ID No. (Optional)", "tax_id", "Main", is_required=False)

    # 2. Spouse Details (if covered)
    if setup["cover_spouse"]:
        st.divider()
        st.subheader("💍 Spouse Details")
        
        col_sp_upload, col_sp_inputs = st.columns([1, 2], gap="large")
        
        with col_sp_upload:
            st.write("Upload Spouse ID to auto-fill:")
            uploaded_sp_id = st.file_uploader("Upload Spouse ID Card Image", type=["jpg", "png", "pdf"])
            if uploaded_sp_id:
                if st.button("📸 Scan Spouse ID Card (Simulation)", key="btn_scan_spouse"):
                    run_ocr_simulation(
                        "Spouse",
                        "John Mercer",
                        "20/08/1985",
                        "123 BlueTable Boulevard, Bangkok, Thailand"
                    )
                    st.rerun()

        with col_sp_inputs:
            render_field("Spouse Full Name", "sp_name", "Spouse")
            
            col_s_d1, col_s_d2 = st.columns(2)
            with col_s_d1:
                render_field("Spouse Date of Birth", "sp_dob", "Spouse", placeholder="DD/MM/YYYY")
            with col_s_d2:
                render_field("Spouse ID Card / Passport No.", "sp_id_card_no", "Spouse")
                
            col_s_d3, col_s_d4 = st.columns(2)
            with col_s_d3:
                render_field("Spouse Nationality", "sp_nationality", "Spouse")
            with col_s_d4:
                render_field("Spouse Occupation", "sp_occupation", "Spouse")
                
            col_s_d5, col_s_d6 = st.columns(2)
            with col_s_d5:
                render_field("Spouse Beneficiary Name", "sp_beneficiary", "Spouse")
            with col_s_d6:
                render_field("Spouse Relation to Beneficiary", "sp_bene_relation", "Spouse")

    # 3. Children Details (if covered)
    for i in range(1, setup["child_count"] + 1):
        st.divider()
        st.subheader(f"👶 Child {i} Details")
        
        col_c_d1, col_c_d2 = st.columns(2)
        with col_c_d1:
            render_field(f"Child {i} Full Name", f"c{i}_name", f"Child_{i}")
        with col_c_d2:
            render_field(f"Child {i} Date of Birth", f"c{i}_dob", f"Child_{i}", placeholder="DD/MM/YYYY")
            
        col_c_d3, col_c_d4 = st.columns(2)
        with col_c_d3:
            render_field(f"Child {i} ID Card / Passport No.", f"c{i}_id_card_no", f"Child_{i}")
        with col_c_d4:
            render_field(f"Child {i} Occupation / Education", f"c{i}_occupation", f"Child_{i}", is_required=False)
            
        col_c_d5, col_c_d6 = st.columns(2)
        with col_c_d5:
            render_field(f"Child {i} Beneficiary Name", f"c{i}_beneficiary", f"Child_{i}")
        with col_c_d6:
            render_field(f"Child {i} Relation to Beneficiary", f"c{i}_bene_relation", f"Child_{i}")

    # 4. Underwriting Declarations
    st.divider()
    st.subheader("📋 Underwriting & Exclusions Details")
    render_field("Pre-existing Conditions or Exclusions (if any)", "exclusions", "Underwriting", placeholder="E.g., Mild Asthma, None", is_required=False)

    st.markdown("---")
    
    col_b, col_n = st.columns([1, 1])
    with col_b:
        if st.button("⬅️ Back to Sandbox"):
            st.session_state.step = 2
            st.rerun()
    with col_n:
        if st.button("Submit Application ✅", type="primary", use_container_width=True):
            st.session_state.form_data = form_data
            st.session_state.step = 4
            st.rerun()

# ── STEP 4: HITL REVIEW & EXPORT ───────────────────────────────────────────
elif st.session_state.step == 4:
    st.subheader("🔍 Step 4: Human-in-the-Loop Verification & Output Generation")
    st.success("🎉 Application Submitted Successfully! Review the compiled parameters below.")
    # TODO: Jules to save the submitted form_data into a local sqlite database (or queue table) so that it can be loaded on the Central Admin Verification Queue Dashboard page.

    form_data = st.session_state.form_data
    setup = st.session_state.members_setup

    col_review, col_action = st.columns([2, 1], gap="large")

    with col_review:
        st.subheader("🔵 Compiled BlueTable Fields")
        
        # Display as a table/keys
        from src.blue_table_tools.schema import BLUETABLE_FIELDS
        
        rows = []
        for label, key in BLUETABLE_FIELDS:
            val = form_data.get(key, "")
            if val:
                rows.append({"Field Label": label, "Variable Key": key, "Value": val})
                
        st.table(rows)

    with col_action:
        st.subheader("#### 📥 Downstream Deliverables")
        
        # 1. Download BlueTable Row JSON
        result_json = json.dumps(form_data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Download BlueTable JSON Row",
            data=result_json,
            file_name="bluetable_row.json",
            mime="application/json",
            use_container_width=True
        )
        
        st.write("---")
        
        # 2. Fill PDF Form and offer download
        template_pdf_path = "./resources/OriginalApplication.pdf"
        
        if os.path.exists(template_pdf_path):
            with st.spinner("Generating official pre-filled PDF..."):
                try:
                    # Fill interactive PDF fields
                    filled_pdf_stream = fill_acroform_pdf(template_pdf_path, form_data)
                    
                    # TODO: Jules to implement email routing or downstream API integration to send the filled PDF automatically to the customer for signature (e.g., DocuSign or Adobe Sign).
                    st.download_button(
                        "⬇️ Download Pre-filled Official PDF",
                        data=filled_pdf_stream.getvalue(),
                        file_name="PreFilled_Application.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
                    st.info("💡 The output PDF contains interactive AcroForm fields pre-populated with customer data, ready for final signature routing.")
                except Exception as e:
                    st.error(f"Failed to generate pre-filled PDF: {e}")
        else:
            st.error(f"Template PDF not found at: {template_pdf_path}")
            
        if st.button("🔄 Start New Application", use_container_width=True):
            # Reset session state
            for k in ["step", "form_data", "members_setup", "ocr_simulated"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
