import streamlit as st

landing_page = st.Page("src/pages/landing.py", title="Home", icon="🏠", default=True)
digital_eform_page = st.Page("src/pages/digital_eform.py", title="Digital E-Form", icon="📝")
pdf_tool_page = st.Page("src/pages/pdf_to_blue_table.py", title="PDF to BlueTable", icon="🚀")

pg = st.navigation([landing_page, digital_eform_page, pdf_tool_page])
pg.run()
