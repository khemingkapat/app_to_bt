import os
import json
import streamlit as st
from src.pdf_processor.inverter import fill_acroform_pdf
from src.blue_table_tools import fill_blue_table_docx

def render_step4(form_data: dict, setup: dict) -> None:
    st.subheader("🔍 Step 4: Human-in-the-Loop Verification & Output Generation")
    st.success("🎉 Application Submitted Successfully! Review the compiled parameters below.")

    col_review, col_action = st.columns([2, 1], gap="large")

    with col_review:
        st.subheader("🔵 Compiled BlueTable Fields")

        from src.blue_table_tools.schema import BLUETABLE_FIELDS
        from src.blue_table_tools.docx_generator import resolve_plan_combination
        from src.blue_table_tools import apply_acceptance_rules

        form_data = resolve_plan_combination(form_data)
        form_data = apply_acceptance_rules(form_data)

        rows = []
        for label, key in BLUETABLE_FIELDS:
            val = form_data.get(key, "")
            if val:
                rows.append({"Field Label": label, "Variable Key": key, "Value": val})

        st.table(rows)

    with col_action:
        st.subheader("#### 📥 Downstream Deliverables")

        template_docx_path = "./resources/BlueTable.docx"
        if os.path.exists(template_docx_path):
            with st.spinner("Generating filled BlueTable DOCX..."):
                try:
                    docx_stream = fill_blue_table_docx(template_docx_path, form_data)
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

        if st.button("🔄 Start New Application", use_container_width=True):
            for k in ["step", "form_data", "members_setup", "ocr_simulated"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
