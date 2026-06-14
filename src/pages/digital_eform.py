import json
import os
import time
from io import BytesIO
import streamlit as st
from src.pdf_processor.inverter import fill_acroform_pdf, load_product_config
from src.blue_table_tools.pricing import calculate_all_plans_premiums

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
        "plan": "Plan 2",
        "deductible": "0",
        "coverage_type": "ipd"
    }
if "ocr_simulated" not in st.session_state:
    st.session_state.ocr_simulated = {}

# Header (Using Standard Streamlit title and write)
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
    st.write("Input your family structure and customize deductibles to see your premiums in real time.")

    col_setup, col_pricing = st.columns([2, 3], gap="large")
    
    setup = st.session_state.members_setup

    with col_setup:
        st.subheader("👨‍👩‍👧 Family Composition")
        
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
            
        st.divider()
        st.subheader("⚙️ Policy Configurations")
        
        # Coverage Type Selector
        coverage_labels = {
            "ipd": "IPD Only",
            "ipd_opd_3000": "IPD + OPD 3,000 THB/visit (30 visits/year)",
            "ipd_opd_3000_wellness": "IPD + OPD 3,000 THB + Wellness",
            "ipd_opd_50000": "IPD + OPD 50,000 THB/year",
            "ipd_opd_50000_wellness": "IPD + OPD 50,000 THB + Wellness"
        }
        setup["coverage_type"] = st.selectbox(
            "Coverage Type",
            options=list(coverage_labels.keys()),
            format_func=lambda x: coverage_labels[x],
            index=list(coverage_labels.keys()).index(setup.get("coverage_type", "ipd"))
        )
        
        # Deductible selector
        deductibles = config.get("pricing", {}).get("deductibles", [])
        ded_labels = {d["key"]: d["label"] for d in deductibles}
        setup["deductible"] = st.selectbox(
            "Deductible Option (Applies to IPD)",
            options=list(ded_labels.keys()),
            format_func=lambda x: ded_labels[x],
            index=list(ded_labels.keys()).index(setup["deductible"])
        )

    with col_pricing:
        st.subheader("🏷️ Premium Calculation Comparison Matrix")
        st.write("Select the plans you want to compare and click the plan selector to highlight.")

        # Calculate premiums for all 4 plans
        plans_pricing = calculate_all_plans_premiums(
            setup["coverage_type"],
            int(setup["deductible"]),
            setup,
            config
        )
        
        # Let user select which plans to compare
        plans_to_compare = st.multiselect(
            "Plans to Compare",
            options=["Plan 1", "Plan 2", "Plan 3", "Plan 4"],
            default=["Plan 1", "Plan 2", "Plan 3", "Plan 4"]
        )
        
        filtered_plans = [p for p in plans_pricing if p["key"] in plans_to_compare]
        
        if filtered_plans:
            # Generate dynamic Markdown table to compare plans side-by-side
            h1 = "| Benefit / Detail |"
            h2 = "| :--- |"
            for p in filtered_plans:
                is_sel = (p["key"] == setup["plan"])
                header = f"**{p['key']} (Selected) ✅**" if is_sel else f"**{p['key']}**"
                h1 += f" {header} |"
                h2 += " :---: |"
                
            r1 = "| **IPD Limit** |"
            for p in filtered_plans:
                r1 += f" {p['coverage']} |"
                
            r2 = "| **Room Limit** |"
            for p in filtered_plans:
                r2 += f" {p['room_limit']} THB |"
                
            r3 = "| **Annual Premium** |"
            for p in filtered_plans:
                is_sel = (p["key"] == setup["plan"])
                val = f"**{p['total']:,.0f} THB**" if is_sel else f"{p['total']:,.0f} THB"
                r3 += f" {val} |"
                
            r4 = "| **Average / Person** |"
            for p in filtered_plans:
                is_sel = (p["key"] == setup["plan"])
                val = f"**{p['avg']:,.0f} THB**" if is_sel else f"{p['avg']:,.0f} THB"
                r4 += f" {val} |"
                
            table_md = f"{h1}\n{h2}\n{r1}\n{r2}\n{r3}\n{r4}"
            st.markdown(table_md)
        else:
            st.warning("⚠️ Please select at least one plan to compare.")

        st.divider()
        st.subheader("Select Plan for Application")
        selected_plan = st.radio(
            "Active Plan Choice",
            options=["Plan 1", "Plan 2", "Plan 3", "Plan 4"],
            index=["Plan 1", "Plan 2", "Plan 3", "Plan 4"].index(setup["plan"]),
            horizontal=True
        )
        setup["plan"] = selected_plan
        
        # Family discount notification
        o = 1 + (1 if setup["cover_spouse"] else 0) + setup["child_count"]
        if o >= 2 and o <= 3:
            st.info("🎉 Family Discount: **5% off** has been applied to all premiums.")
        elif o >= 4:
            st.info("🎉 Family Discount: **10% off** has been applied to all premiums.")

    st.markdown("---")
    
    col_b, col_n = st.columns([1, 1])
    with col_b:
        if st.button("⬅️ Back to Health Gate"):
            st.session_state.step = 1
            st.rerun()
    with col_n:
        if st.button("Proceed to Details Intake ➡️", type="primary", use_container_width=True):
            st.session_state.members_setup = setup
            
            # Fetch pricing details for the chosen plan
            chosen_plan_pricing = next(p for p in plans_pricing if p["key"] == setup["plan"])
            
            # Populate form_data for output mapping
            st.session_state.form_data["plan"] = setup["plan"]
            st.session_state.form_data["deductible"] = ded_labels[setup["deductible"]]
            st.session_state.form_data["premium"] = f"{chosen_plan_pricing['total']:,.0f}"
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
            form_data["name"] = id_name
            form_data["dob"] = id_dob
            form_data["present_address"] = id_addr
            st.session_state.ocr_simulated["Main_name"] = True
            st.session_state.ocr_simulated["Main_dob"] = True
            st.session_state.ocr_simulated["Main_present_address"] = True
        elif section_name == "Spouse":
            form_data["sp_name"] = id_name
            form_data["sp_dob"] = id_dob
            st.session_state.ocr_simulated["Spouse_sp_name"] = True
            st.session_state.ocr_simulated["Spouse_sp_dob"] = True

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
