import streamlit as st

st.set_page_config(
    page_title="AXA Application Tools Portal", page_icon="🏥", layout="wide"
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #002855;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .landing-desc {
        font-size: 1.1rem;
        color: #555;
        text-align: center;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }
    
    /* Control container spacing to reduce space between buttons */
    div.stButton {
        margin-bottom: -4px !important;
    }
    
    /* Style all Streamlit buttons on this page to be clean list items with same length matching container */
    div.stButton > button {
        background-color: #ffffff !important;
        color: #002855 !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
        padding: 0.8rem 1.5rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important; /* Fill container width */
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02) !important;
    }
    
    div.stButton > button:hover {
        border-color: #002855 !important;
        background-color: #f7f9fc !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 40, 85, 0.08) !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 class='main-header'>🏥 AXA Application Tools Portal</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='landing-desc'>A unified intake workflow platform designed for zero-error underwriting, automated data extraction, and human-in-the-loop validation.</div>",
    unsafe_allow_html=True,
)

# Thinner vertical alignment list centered in the mid column
col_l, col_m, col_r = st.columns([1, 1, 1])

with col_m:
    st.markdown("<h4 style='color: #666; margin-bottom: 12px; text-align: center;'>Select a Tool to Launch:</h4>", unsafe_allow_html=True)

    if st.button("🚀 Launch PDF to BlueTable Tool ➡️", key="btn_path_a", use_container_width=True):
        st.switch_page("src/pages/pdf_to_blue_table.py")

    if st.button("📝 Launch Digital E-Form Portal ➡️", key="btn_path_b", use_container_width=True):
        st.switch_page("src/pages/digital_eform.py")

    if st.button("⌨️ Launch Internal E-Form ➡️", key="btn_path_c", use_container_width=True):
        st.switch_page("src/pages/internal_eform.py")

    if st.button("✍️ Launch Signature Gateway ➡️", key="btn_signature_gateway", use_container_width=True):
        st.switch_page("src/pages/signature_gateway.py")

    if st.button("⚙️ Launch Configuration Manager ➡️", key="btn_config_manager", use_container_width=True):
        st.switch_page("src/pages/config_manager.py")

st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.caption(
    "Internal administrative utility for AXA Health and Accident Insurance operations."
)
