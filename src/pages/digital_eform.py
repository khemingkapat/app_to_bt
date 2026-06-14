import json
import os
import time
from io import BytesIO
import streamlit as st
from src.pdf_processor.inverter import fill_acroform_pdf, load_product_config, parse_date_part

# Setup page config
st.set_page_config(layout="wide", page_title="Digital E-Form Portal")

# Load configuration
CONFIG_PATH = "./config/health_and_accident.json"
config = load_product_config(CONFIG_PATH)

# Custom Styling for Premium Aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #002855 0%, #005a9c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
    }
    .price-tag {
        font-size: 1.8rem;
        font-weight: 700;
        color: #002855;
    }
    .review-badge {
        background-color: #ffeeb5;
        color: #856404;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    .prefilled-field {
        background-color: #fff3cd !important;
        border: 1px solid #ffeeba !important;
    }
</style>
""", unsafe_allow_html=True)

# Premium Calculations Import
from src.blue_table_tools.pricing import calculate_premium

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
        "plan": "Standard",
        "deductible": "None"
    }
if "ocr_simulated" not in st.session_state:
    st.session_state.ocr_simulated = {}

# Header
st.markdown("<div class='main-header'>🏥 AXA Health Digital Application Portal</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Pathway B: Native Digital Form with Underwriting & Premium Sandbox</div>", unsafe_allow_html=True)

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
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 👨‍👩‍👧 Family Composition")
        
        # Main Insured
        setup["main_age"] = st.number_input("Main Insured Age", min_value=0, max_value=100, value=setup["main_age"])
        
        # Spouse cover
        setup["cover_spouse"] = st.checkbox("Cover Spouse", value=setup["cover_spouse"])
        if setup["cover_spouse"]:
            setup["spouse_age"] = st.number_input("Spouse Age", min_value=0, max_value=100, value=setup["spouse_age"])
            
        # Children cover
        setup["child_count"] = st.slider("Number of Children to Cover", min_value=0, max_value=3, value=setup["child_count"])
        
        for i in range(1, setup["child_count"] + 1):
            setup[f"child_{i}_age"] = st.number_input(f"Child {i} Age", min_value=0, max_value=25, value=setup.get(f"child_{i}_age", 10))
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### ⚙️ Policy Configurations")
        
        # Deductible selector
        deductibles = config.get("pricing", {}).get("deductibles", [])
        ded_labels = {d["key"]: d["label"] for d in deductibles}
        setup["deductible"] = st.selectbox(
            "Deductible Option",
            options=list(ded_labels.keys()),
            format_func=lambda x: ded_labels[x],
            index=list(ded_labels.keys()).index(setup["deductible"])
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_pricing:
        st.markdown("#### 🏷️ Premium Calculation Comparison Matrix")
        st.write("Compare different plan tiers side-by-side. Your selected settings are applied live.")

        plans = config.get("pricing", {}).get("plans", [])
        
        col_p1, col_p2, col_p3 = st.columns(3)
        cols = [col_p1, col_p2, col_p3]
        
        for idx, plan in enumerate(plans):
            final_p, breakdown = calculate_premium(plan["key"], setup["deductible"], setup)
            is_selected = (setup["plan"] == plan["key"])
            
            with cols[idx]:
                st.markdown(f"""
                <div class='card' style='border: 2px solid {'#005a9c' if is_selected else '#e0e0e0'}; background-color: {'#f0f8ff' if is_selected else '#ffffff'};'>
                    <h4 style='color: #002855;'>{plan['label']}</h4>
                    <p style='font-size:0.85rem; color:#666;'>Standard coverage tier</p>
                    <hr>
                    <p class='price-tag'>{final_p:,.2f} THB</p>
                    <p style='font-size:0.75rem; color:#888;'>Annual premium (incl. tax)</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Choose {plan['key']}", key=f"btn_plan_{plan['key']}", use_container_width=True):
                    setup["plan"] = plan["key"]
                    st.rerun()

        # Display pricing breakdown
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 🧾 Pricing Breakdown Details")
        
        current_final, curr_breakdown = calculate_premium(setup["plan"], setup["deductible"], setup)
        
        st.write(f"**Selected Plan:** {setup['plan']} | **Deductible:** {ded_labels[setup['deductible']]}")
        
        # Details table
        st.markdown(f"""
        * **Main Insured:** {curr_breakdown['Main Insured']:,.2f} THB
        """, unsafe_allow_html=True)
        
        if setup["cover_spouse"]:
            st.markdown(f"""
            * **Spouse Premium:** {curr_breakdown['Spouse']:,.2f} THB
            """, unsafe_allow_html=True)
            
        if setup["child_count"] > 0:
            for idx, c_cost in enumerate(curr_breakdown['Children']):
                st.markdown(f"""
                * **Child {idx+1} Premium:** {c_cost:,.2f} THB
                """, unsafe_allow_html=True)
                
        ded_obj = next(d for d in deductibles if d["key"] == setup["deductible"])
        if ded_obj["multiplier"] < 1.0:
            discount = (1.0 - ded_obj["multiplier"]) * 100
            st.markdown(f"* **Deductible Discount:** -{discount:.0f}%")
            
        st.markdown(f"### **Total Annual Premium: {current_final:,.2f} THB**")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    col_b, col_n = st.columns([1, 1])
    with col_b:
        if st.button("⬅️ Back to Health Gate"):
            st.session_state.step = 1
            st.rerun()
    with col_n:
        if st.button("Proceed to Details Intake ➡️", type="primary", use_container_width=True):
            st.session_state.members_setup = setup
            # Automatically set Plan details in form_data
            st.session_state.form_data["plan"] = setup["plan"]
            st.session_state.form_data["deductible"] = ded_labels[setup["deductible"]]
            st.session_state.form_data["premium"] = f"{current_final:,.2f}"
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
        # Check if pre-filled by OCR
        is_prefilled = full_key in st.session_state.ocr_simulated
        
        # Display highlight warning if prefilled
        if is_prefilled:
            st.markdown("<span class='review-badge'>⚠️ Review pre-filled info</span>", unsafe_allow_html=True)
            
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
        
        # Store pre-filled values
        form_data["name"] if section_name == "Main" else None
        
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
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 👤 Main Insured Details")
    
    col_upload, col_inputs = st.columns([1, 2], gap="large")
    
    with col_upload:
        st.write("Upload National ID to auto-fill:")
        uploaded_id = st.file_uploader("Upload Main Insured ID Card Image", type=["jpg", "png", "pdf"])
        if uploaded_id:
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
        
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Spouse Details (if covered)
    if setup["cover_spouse"]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 💍 Spouse Details")
        
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
                
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Children Details (if covered)
    for i in range(1, setup["child_count"] + 1):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"### 👶 Child {i} Details")
        
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
            
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. Underwriting Declarations
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📋 Underwriting & Exclusions Details")
    render_field("Pre-existing Conditions or Exclusions (if any)", "exclusions", "Underwriting", placeholder="E.g., Mild Asthma, None", is_required=False)
    st.markdown("</div>", unsafe_allow_html=True)

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
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 🔵 Compiled BlueTable Fields")
        
        # Display as a table/keys
        from src.blue_table_tools.schema import BLUETABLE_FIELDS
        
        rows = []
        for label, key in BLUETABLE_FIELDS:
            val = form_data.get(key, "")
            if val:
                rows.append({"Field Label": label, "Variable Key": key, "Value": val})
                
        st.table(rows)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_action:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📥 Downstream Deliverables")
        
        # 1. Download BlueTable Row JSON
        result_json = json.dumps(form_data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Download BlueTable JSON Row",
            data=result_json,
            file_name="bluetable_row.json",
            mime="application/json",
            use_container_width=True
        )
        
        st.markdown("---")
        
        # 2. Fill PDF Form and offer download
        template_pdf_path = "./resources/OriginalApplication.pdf"
        
        if os.path.exists(template_pdf_path):
            with st.spinner("Generating official pre-filled PDF..."):
                try:
                    # Fill interactive PDF fields
                    filled_pdf_stream = fill_acroform_pdf(template_pdf_path, form_data)
                    
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
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("🔄 Start New Application", use_container_width=True):
            # Reset session state
            for k in ["step", "form_data", "members_setup", "ocr_simulated"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
