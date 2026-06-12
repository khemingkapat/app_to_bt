import streamlit as st

landing_page = st.Page("src/pages/landing.py", title="Home", icon="🏠", default=True)
pdf_tool_page = st.Page("src/pages/pdf_to_blue_table.py", title="PDF to BlueTable", icon="🚀")
intake_form_page = st.Page("src/pages/intake_form.py", title="Intake Form", icon="📝")

pg = st.navigation([landing_page, pdf_tool_page, intake_form_page])
pg.run()
