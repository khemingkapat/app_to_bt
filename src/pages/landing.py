import streamlit as st

st.set_page_config(
    page_title="AXA Health Insurance Application",
    page_icon="🏥",
    layout="centered"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #002855 0%, #005a9c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .landing-desc {
        font-size: 1.15rem;
        color: #444;
        text-align: center;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }
    .path-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 14px;
        padding: 2rem;
        min-height: 280px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        text-align: center;
    }
    .path-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
    }
    .path-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .path-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #002855;
        margin-bottom: 0.8rem;
    }
    .path-desc {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>🏥 AXA Health Insurance Application Portal</h1>", unsafe_allow_html=True)
st.markdown("<div class='landing-desc'>A unified intake workflow platform designed for zero-error underwriting, automated data extraction, and human-in-the-loop validation.</div>", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns(3, gap="medium")

with col_a:
    st.markdown("""
    <div class='path-card'>
        <div class='path-icon'>🚀</div>
        <div class='path-title'>Pathway A: PDF to BlueTable</div>
        <div class='path-desc'>Internal operator interface to upload physical scanned documents, verify extracted fields visually, and export directly.</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Launch PDF to BlueTable Tool ➡️", key="btn_path_a", use_container_width=True):
        st.switch_page("src/pages/pdf_to_blue_table.py")

with col_b:
    st.markdown("""
    <div class='path-card'>
        <div class='path-icon'>⌨️</div>
        <div class='path-title'>Internal Fast-Entry E-Form</div>
        <div class='path-desc'>High-speed operator portal designed for rapid typing-only data capture with autofocus, keyboard hotkeys, and real-time validations.</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Launch Internal E-Form ➡️", key="btn_path_c", use_container_width=True, type="primary"):
        st.switch_page("src/pages/internal_eform.py")

with col_c:
    st.markdown("""
    <div class='path-card'>
        <div class='path-icon'>📝</div>
        <div class='path-title'>Pathway B: Digital E-Form</div>
        <div class='path-desc'>Customer-facing digital onboarding journey with health pre-screening underwriting and plan comparison sandbox.</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Launch Digital E-Form Portal ➡️", key="btn_path_b", use_container_width=True):
        st.switch_page("src/pages/digital_eform.py")

st.divider()
st.caption("Internal administrative utility for AXA Health and Accident Insurance operations.")
