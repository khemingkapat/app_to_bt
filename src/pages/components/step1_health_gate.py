import streamlit as st

def render_step1(config: dict) -> None:
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
