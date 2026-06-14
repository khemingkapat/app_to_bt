import time
import streamlit as st
from src.blue_table_tools.state_handlers import simulate_ocr

def render_field(form_data, label_text, bt_key, section, placeholder="", is_required=True):
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

def run_ocr_simulation(form_data, section_name, id_name, id_dob, id_addr):
    progress_bar = st.progress(0)
    status_text = st.empty()

    for percent_complete in range(0, 101, 10):
        time.sleep(0.15)
        progress_bar.progress(percent_complete)
        status_text.text(f"🔍 Analyzing ID card layout... {percent_complete}%")

    status_text.success("✨ ID card processed! Form pre-populated successfully.")
    time.sleep(0.5)

    new_data, new_simulated = simulate_ocr(section_name, id_name, id_dob, id_addr)

    for k, v in new_data.items():
        form_data[k] = v
        st.session_state[f"input_field_{section_name}_{k}"] = v

    st.session_state.ocr_simulated.update(new_simulated)


def render_step3(setup: dict, form_data: dict) -> None:
    st.subheader("📝 Step 3: Progressive Personal Info Blocks")
    st.write("Please fill in the personal information. To speed up the intake and ensure 100% accuracy, you can upload your National ID card to automatically pre-fill details.")

    st.subheader("👤 Main Insured Details")

    col_upload, col_inputs = st.columns([1, 2], gap="large")

    with col_upload:
        st.write("Upload National ID to auto-fill:")
        uploaded_id = st.file_uploader("Upload Main Insured ID Card Image", type=["jpg", "png", "pdf"])
        if uploaded_id:
            if st.button("📸 Scan ID Card (Simulation)", key="btn_scan_main"):
                run_ocr_simulation(
                    form_data,
                    "Main",
                    "Alex Mercer",
                    "31/10/1990",
                    "123 BlueTable Boulevard, Bangkok, Thailand"
                )
                st.rerun()

    with col_inputs:
        render_field(form_data, "Full Name", "name", "Main")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            render_field(form_data, "Date of Birth", "dob", "Main", placeholder="DD/MM/YYYY")
        with col_d2:
            render_field(form_data, "ID Card / Passport No.", "id_card_no", "Main")

        render_field(form_data, "Present Address", "present_address", "Main")

        col_d3, col_d4 = st.columns(2)
        with col_d3:
            render_field(form_data, "Telephone No.", "tel", "Main")
        with col_d4:
            render_field(form_data, "Email Address", "email", "Main")

        col_d5, col_d6 = st.columns(2)
        with col_d5:
            render_field(form_data, "Nationality", "nationality", "Main")
        with col_d6:
            render_field(form_data, "Occupation", "occupation", "Main")

        col_d7, col_d8 = st.columns(2)
        with col_d7:
            render_field(form_data, "Beneficiary Name", "beneficiary", "Main")
        with col_d8:
            render_field(form_data, "Relation to Beneficiary", "bene_relation", "Main")

        render_field(form_data, "Tax ID No. (Optional)", "tax_id", "Main", is_required=False)

    if setup.get("cover_spouse"):
        st.divider()
        st.subheader("💍 Spouse Details")

        col_sp_upload, col_sp_inputs = st.columns([1, 2], gap="large")

        with col_sp_upload:
            st.write("Upload Spouse ID to auto-fill:")
            uploaded_sp_id = st.file_uploader("Upload Spouse ID Card Image", type=["jpg", "png", "pdf"])
            if uploaded_sp_id:
                if st.button("📸 Scan Spouse ID Card (Simulation)", key="btn_scan_spouse"):
                    run_ocr_simulation(
                        form_data,
                        "Spouse",
                        "John Mercer",
                        "20/08/1985",
                        "123 BlueTable Boulevard, Bangkok, Thailand"
                    )
                    st.rerun()

        with col_sp_inputs:
            render_field(form_data, "Spouse Full Name", "sp_name", "Spouse")

            col_s_d1, col_s_d2 = st.columns(2)
            with col_s_d1:
                render_field(form_data, "Spouse Date of Birth", "sp_dob", "Spouse", placeholder="DD/MM/YYYY")
            with col_s_d2:
                render_field(form_data, "Spouse ID Card / Passport No.", "sp_id_card_no", "Spouse")

            col_s_d3, col_s_d4 = st.columns(2)
            with col_s_d3:
                render_field(form_data, "Spouse Nationality", "sp_nationality", "Spouse")
            with col_s_d4:
                render_field(form_data, "Spouse Occupation", "sp_occupation", "Spouse")

            col_s_d5, col_s_d6 = st.columns(2)
            with col_s_d5:
                render_field(form_data, "Spouse Beneficiary Name", "sp_beneficiary", "Spouse")
            with col_s_d6:
                render_field(form_data, "Spouse Relation to Beneficiary", "sp_bene_relation", "Spouse")

    for i in range(1, setup.get("child_count", 0) + 1):
        st.divider()
        st.subheader(f"👶 Child {i} Details")

        col_c_d1, col_c_d2 = st.columns(2)
        with col_c_d1:
            render_field(form_data, f"Child {i} Full Name", f"c{i}_name", f"Child_{i}")
        with col_c_d2:
            render_field(form_data, f"Child {i} Date of Birth", f"c{i}_dob", f"Child_{i}", placeholder="DD/MM/YYYY")

        col_c_d3, col_c_d4 = st.columns(2)
        with col_c_d3:
            render_field(form_data, f"Child {i} ID Card / Passport No.", f"c{i}_id_card_no", f"Child_{i}")
        with col_c_d4:
            render_field(form_data, f"Child {i} Occupation / Education", f"c{i}_occupation", f"Child_{i}", is_required=False)

        col_c_d5, col_c_d6 = st.columns(2)
        with col_c_d5:
            render_field(form_data, f"Child {i} Beneficiary Name", f"c{i}_beneficiary", f"Child_{i}")
        with col_c_d6:
            render_field(form_data, f"Child {i} Relation to Beneficiary", f"c{i}_bene_relation", f"Child_{i}")

    st.divider()
    st.subheader("📋 Underwriting & Exclusions Details")
    render_field(form_data, "Pre-existing Conditions or Exclusions (if any)", "exclusions", "Underwriting", placeholder="E.g., Mild Asthma, None", is_required=False)

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
