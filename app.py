import streamlit as st

# Change from relative "." to an absolute import via src
from src.pdf_processor.engine import process_pdf

st.set_page_config(layout="wide")
st.title("PDF Field Inspector")
uploaded_file = st.file_uploader("Upload a PDF Form", type=["pdf"])
if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Directly get the dictionaries to use in your UI
    pdf_id, structure, values = process_pdf("temp.pdf")

    st.subheader("Extracted Values")
    st.text(pdf_id)
    st.text("from last time we got : 87ba7613a963df438482bbcd8c1612a0")
    st.json(values)
    st.json(structure)
