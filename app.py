import streamlit as st

st.set_page_config(
    page_title="AXA Health Insurance Application",
    page_icon="🏥",
    layout="centered"
)

st.title("🏥 AXA Health Insurance Application Portal")

st.markdown("""
Welcome to the AXA Health Insurance Application Portal.

Please select a tool from the sidebar, or click below to launch the PDF to BlueTable processing tool.
""")

col1, col2, col3 = st.columns([1,2,1])
with col2:
    if st.button("🚀 Launch PDF to BlueTable Tool", use_container_width=True):
        st.switch_page("pages/1_PDF_to_BlueTable.py")

st.divider()
st.caption("Internal tool for insurance application processing.")
