import streamlit as st

# Check if a signature gateway token is present in the query parameters.
# If so, render ONLY the Signature Gateway page so that the customer does not see the navigation sidebar.
if "token" in st.query_params:
    signature_gateway_page = st.Page("src/pages/signature_gateway.py", title="Signature Gateway", icon="✍️", default=True)
    pg = st.navigation([signature_gateway_page])
else:
    landing_page = st.Page("src/pages/landing.py", title="Home", icon="🏠", default=True)
    digital_eform_page = st.Page("src/pages/digital_eform.py", title="Digital E-Form", icon="📝")
    internal_eform_page = st.Page("src/pages/internal_eform.py", title="Internal E-Form", icon="⌨️")
    pdf_tool_page = st.Page("src/pages/pdf_to_blue_table.py", title="PDF to BlueTable", icon="🚀")
    signature_gateway_page = st.Page("src/pages/signature_gateway.py", title="Signature Gateway", icon="✍️")
    config_manager_page = st.Page("src/pages/config_manager.py", title="Config Manager", icon="⚙️")

    # TODO: Jules to implement the Central Admin Verification Queue Dashboard (Phase 5 of project_plan.md)
    # This page should display pending submissions (both from digital_eform and pdf_to_blue_table uploads)
    # and let the administrator open, review, and approve them.

    pg = st.navigation([
        landing_page,
        digital_eform_page,
        internal_eform_page,
        pdf_tool_page,
        signature_gateway_page,
        config_manager_page
    ])

pg.run()
