import streamlit as st

def render_underwriting_gate():
    st.header("Step 1: Underwriting Gate")

    st.write("Please answer the following medical disclosure questions:")
    fatal_condition = st.radio(
        "Do you have a fatal chronic medical condition?",
        options=["Select", "YES", "NO"],
        index=0
    )

    if fatal_condition == "YES":
        st.error("Application Rejected: High-liability risk profiles cannot proceed.")
        st.stop()

    return fatal_condition == "NO"

import re
import json
import io
from pypdf import PdfReader, PdfWriter
from src.blue_table_tools.schema import BLUETABLE_FIELDS

def clean_numeric_string(val):
    """Strip non-digits (letters, spaces, hyphens)."""
    return re.sub(r"[^\d]", "", val)

def convert_be_to_ce(date_str):
    """Convert BE year (e.g. 2533) to CE (e.g. 1990) in DD/MM/YYYY format."""
    if not date_str:
        return date_str
    parts = date_str.split("/")
    if len(parts) == 3:
        try:
            year = int(parts[2])
            if year > 2500:
                parts[2] = str(year - 543)
            return "/".join(parts)
        except ValueError:
            pass
    return date_str

def on_main_insured_change():
    """Callback to normalize Main Insured details upon input."""
    # Convert dates
    raw_dob = st.session_state.get("raw_main_dob", "")
    if raw_dob:
        st.session_state.main_dob = convert_be_to_ce(raw_dob)

    raw_eff = st.session_state.get("raw_main_effective_date", "")
    if raw_eff:
        st.session_state.main_effective_date = convert_be_to_ce(raw_eff)

    # Strip ID and Tel
    raw_id = st.session_state.get("raw_main_id", "")
    if raw_id:
        st.session_state.main_id_card_no = clean_numeric_string(raw_id)

    raw_tel = st.session_state.get("raw_main_tel", "")
    if raw_tel:
        st.session_state.main_tel = clean_numeric_string(raw_tel)


def on_dependent_change(idx, prefix):
    raw_dob = st.session_state.get(f"raw_{prefix}_dob_{idx}", "")
    if raw_dob:
        st.session_state[f"{prefix}_dob_{idx}"] = convert_be_to_ce(raw_dob)

    raw_id = st.session_state.get(f"raw_{prefix}_id_{idx}", "")
    if raw_id:
        st.session_state[f"{prefix}_id_card_no_{idx}"] = clean_numeric_string(raw_id)

def render_dependent_block():
    st.header("Step 3: Dependents (Optional)")

    has_spouse = st.checkbox("Add Spouse")
    if has_spouse:
        st.subheader("Spouse Details")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.sp_name = st.text_input("Spouse Name", value=st.session_state.get("sp_name", ""))
            st.text_input("Spouse DOB", key="raw_sp_dob_0", value=st.session_state.get("sp_dob_0", ""), on_change=on_dependent_change, args=(0, "sp"))
            st.text_input("Spouse ID", key="raw_sp_id_0", value=st.session_state.get("sp_id_card_no_0", ""), on_change=on_dependent_change, args=(0, "sp"))
            st.session_state.sp_nationality = st.text_input("Spouse Nationality", value=st.session_state.get("sp_nationality", ""))
        with col2:
            st.session_state.sp_occupation = st.text_input("Spouse Occupation", value=st.session_state.get("sp_occupation", ""))
            st.session_state.sp_beneficiary = st.text_input("Spouse Beneficiary", value=st.session_state.get("sp_beneficiary", ""))
            st.session_state.sp_bene_relation = st.text_input("Spouse Relation", value=st.session_state.get("sp_bene_relation", ""))
            st.session_state.sp_exclusions = st.text_input("Spouse Exclusions", value=st.session_state.get("sp_exclusions", ""))

    num_children = st.number_input("Number of Children", min_value=0, max_value=3, value=0)

    if "children" not in st.session_state:
        st.session_state.children = []

    # Ensure children array is correct length
    while len(st.session_state.children) < num_children:
        st.session_state.children.append({})
    while len(st.session_state.children) > num_children:
        st.session_state.children.pop()

    for i in range(num_children):
        st.subheader(f"Child {i+1} Details")
        c_idx = i + 1
        col1, col2 = st.columns(2)

        # We use a localized prefix for children to reuse the on_change callback
        # but store them in session_state.children dictionary upon submission.
        # For simplicity, we can just use session state keys and construct the dict later.
        with col1:
            st.session_state[f"c{c_idx}_name"] = st.text_input(f"Child {c_idx} Name", value=st.session_state.get(f"c{c_idx}_name", ""))
            st.text_input(f"Child {c_idx} DOB", key=f"raw_c{c_idx}_dob_{c_idx}", value=st.session_state.get(f"c{c_idx}_dob_{c_idx}", ""), on_change=on_dependent_change, args=(c_idx, f"c{c_idx}"))
            st.text_input(f"Child {c_idx} ID", key=f"raw_c{c_idx}_id_{c_idx}", value=st.session_state.get(f"c{c_idx}_id_card_no_{c_idx}", ""), on_change=on_dependent_change, args=(c_idx, f"c{c_idx}"))
            st.session_state[f"c{c_idx}_nationality"] = st.text_input(f"Child {c_idx} Nationality", value=st.session_state.get(f"c{c_idx}_nationality", ""))
        with col2:
            st.session_state[f"c{c_idx}_occupation"] = st.text_input(f"Child {c_idx} Occupation", value=st.session_state.get(f"c{c_idx}_occupation", ""))
            st.session_state[f"c{c_idx}_beneficiary"] = st.text_input(f"Child {c_idx} Beneficiary", value=st.session_state.get(f"c{c_idx}_beneficiary", ""))
            st.session_state[f"c{c_idx}_bene_relation"] = st.text_input(f"Child {c_idx} Relation", value=st.session_state.get(f"c{c_idx}_bene_relation", ""))
            st.session_state[f"c{c_idx}_exclusions"] = st.text_input(f"Child {c_idx} Exclusions", value=st.session_state.get(f"c{c_idx}_exclusions", ""))


def render_main_insured_details():
    st.header("Step 2: Main Insured Details")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.main_name = st.text_input("Name", value=st.session_state.get("main_name", ""))
        st.text_input("Date of Birth (DD/MM/YYYY or DD/MM/BE)", key="raw_main_dob", value=st.session_state.get("main_dob", ""), on_change=on_main_insured_change)
        st.text_input("ID No./Passport No.", key="raw_main_id", value=st.session_state.get("main_id_card_no", ""), on_change=on_main_insured_change)
        st.text_input("Tel", key="raw_main_tel", value=st.session_state.get("main_tel", ""), on_change=on_main_insured_change)
        st.session_state.main_email = st.text_input("Email", value=st.session_state.get("main_email", ""))
        st.session_state.main_nationality = st.text_input("Nationality", value=st.session_state.get("main_nationality", ""))
        st.session_state.main_occupation = st.text_input("Occupation", value=st.session_state.get("main_occupation", ""))
        st.session_state.main_tax_id = st.text_input("TAX ID", value=st.session_state.get("main_tax_id", ""))

    with col2:
        st.session_state.main_plan = st.selectbox("Plan", ["", "CHPLAN 01", "CHPLAN 02", "CHPLAN 03", "CHPLAN 04", "CHPLAN 05", "CHPLAN 06", "CHPLAN 07", "CHPLAN 08", "CHPLAN 09"], index=0)
        st.session_state.main_deductible = st.text_input("Deductible", value=st.session_state.get("main_deductible", ""))
        st.session_state.main_premium = st.text_input("Premium", value=st.session_state.get("main_premium", ""))
        st.text_input("Effective Date", key="raw_main_effective_date", value=st.session_state.get("main_effective_date", ""), on_change=on_main_insured_change)
        st.session_state.main_present_address = st.text_input("Personal Address", value=st.session_state.get("main_present_address", ""))
        st.session_state.main_beneficiary = st.text_input("Beneficiary Name", value=st.session_state.get("main_beneficiary", ""))
        st.session_state.main_bene_relation = st.text_input("Relation", value=st.session_state.get("main_bene_relation", ""))
        st.session_state.main_exclusions = st.text_input("Exclusions", value=st.session_state.get("main_exclusions", ""))


def main():
    st.title("📝 Intake Form")

    # Initialize state
    if "step" not in st.session_state:
        st.session_state.step = 1

    # Render Step 1
    if st.session_state.step >= 1:
        passed_gate = render_underwriting_gate()

        if passed_gate and st.session_state.step == 1:
            if st.button("Proceed to Step 2"):
                st.session_state.step = 2
                st.rerun()

    # Render Step 2
    if st.session_state.step >= 2:
        st.divider()
        render_main_insured_details()

        if st.session_state.step == 2:
            if st.button("Proceed to Step 3"):
                st.session_state.step = 3
                st.rerun()

    # Render Step 3
    if st.session_state.step >= 3:
        if not st.session_state.get("submitted", False):
            st.divider()
            render_dependent_block()

            st.divider()
            if st.button("Submit Application", type="primary"):
                st.session_state.submitted = True
                st.rerun()
        else:
            st.success("Application Submitted Successfully!")
            st.divider()

            # Pathway A: Tab-delimited Grid Output
            st.header("Pathway A: Spreadsheet Export")

            # Flatten to schema
            flattened_data = {}
            # Map main details
            flattened_data["name"] = st.session_state.get("main_name", "")
            flattened_data["dob"] = st.session_state.get("main_dob", "")
            flattened_data["id_card_no"] = st.session_state.get("main_id_card_no", "")
            flattened_data["nationality"] = st.session_state.get("main_nationality", "")
            flattened_data["beneficiary"] = st.session_state.get("main_beneficiary", "")
            flattened_data["bene_relation"] = st.session_state.get("main_bene_relation", "")
            flattened_data["occupation"] = st.session_state.get("main_occupation", "")
            flattened_data["plan"] = st.session_state.get("main_plan", "")
            flattened_data["deductible"] = st.session_state.get("main_deductible", "")
            flattened_data["premium"] = st.session_state.get("main_premium", "")
            flattened_data["effective_date"] = st.session_state.get("main_effective_date", "")
            flattened_data["present_address"] = st.session_state.get("main_present_address", "")
            flattened_data["tel"] = st.session_state.get("main_tel", "")
            flattened_data["email"] = st.session_state.get("main_email", "")
            flattened_data["tax_id"] = st.session_state.get("main_tax_id", "")
            flattened_data["exclusions"] = st.session_state.get("main_exclusions", "")

            # Map spouse
            flattened_data["sp_name"] = st.session_state.get("sp_name", "")
            flattened_data["sp_dob"] = st.session_state.get("sp_dob_0", "")
            flattened_data["sp_id_card_no"] = st.session_state.get("sp_id_card_no_0", "")
            flattened_data["sp_nationality"] = st.session_state.get("sp_nationality", "")
            flattened_data["sp_beneficiary"] = st.session_state.get("sp_beneficiary", "")
            flattened_data["sp_bene_relation"] = st.session_state.get("sp_bene_relation", "")
            flattened_data["sp_occupation"] = st.session_state.get("sp_occupation", "")
            flattened_data["sp_exclusions"] = st.session_state.get("sp_exclusions", "")

            # Map children
            for i in range(1, 4):
                if i - 1 < len(st.session_state.children):
                    st.session_state.children[i - 1]["name"] = st.session_state.get(f"c{i}_name", "")
                    st.session_state.children[i - 1]["dob"] = st.session_state.get(f"c{i}_dob_{i}", "")
                    st.session_state.children[i - 1]["id_card_no"] = st.session_state.get(f"c{i}_id_card_no_{i}", "")
                    st.session_state.children[i - 1]["nationality"] = st.session_state.get(f"c{i}_nationality", "")
                    st.session_state.children[i - 1]["beneficiary"] = st.session_state.get(f"c{i}_beneficiary", "")
                    st.session_state.children[i - 1]["bene_relation"] = st.session_state.get(f"c{i}_bene_relation", "")
                    st.session_state.children[i - 1]["occupation"] = st.session_state.get(f"c{i}_occupation", "")
                    st.session_state.children[i - 1]["exclusions"] = st.session_state.get(f"c{i}_exclusions", "")

                flattened_data[f"c{i}_name"] = st.session_state.get(f"c{i}_name", "")
                flattened_data[f"c{i}_dob"] = st.session_state.get(f"c{i}_dob_{i}", "")
                flattened_data[f"c{i}_id_card_no"] = st.session_state.get(f"c{i}_id_card_no_{i}", "")
                flattened_data[f"c{i}_nationality"] = st.session_state.get(f"c{i}_nationality", "")
                flattened_data[f"c{i}_beneficiary"] = st.session_state.get(f"c{i}_beneficiary", "")
                flattened_data[f"c{i}_bene_relation"] = st.session_state.get(f"c{i}_bene_relation", "")
                flattened_data[f"c{i}_occupation"] = st.session_state.get(f"c{i}_occupation", "")
                flattened_data[f"c{i}_exclusions"] = st.session_state.get(f"c{i}_exclusions", "")

            # Stash flattened data for Pathway B later
            st.session_state.flattened_data = flattened_data

            # Generate tab-delimited string
            ordered_values = []
            for label, key in BLUETABLE_FIELDS:
                ordered_values.append(str(flattened_data.get(key, "")))

            tab_delimited_string = "\t".join(ordered_values)

            st.code(tab_delimited_string, language="text")
            st.caption("Select and copy the text above to paste directly into the BlueTable spreadsheet.")

            # Pathway B: PDF Generation
            st.header("Pathway B: Compiled Application PDF")

            with open("outputs/assignment_cache.example.json", "r", encoding="utf-8") as f:
                assignment_cache = json.load(f)

            # Use the first mapping found in the cache
            mapping = list(assignment_cache.values())[0] if assignment_cache else {}

            pdf_data = {}
            for pdf_field, bt_key in mapping.items():
                if bt_key == "SKIPPED":
                    continue

                # Special handling for DOB fields which are split into DD, MM, YYYY across multiple PDF tags
                if bt_key in ["dob", "sp_dob", "c1_dob", "c2_dob", "c3_dob"]:
                    dob_val = flattened_data.get(bt_key, "")
                    parts = dob_val.split("/") if dob_val else []

                    # We need to map the parts based on the field name suffix (Text3, Text4, Text5)
                    # From exploration, the fields are ordered Text3 (DD), Text4 (MM), Text5 (YYYY)
                    # We can use a simple strategy: if it's the first time we see this DOB key, assign DD, etc.

                    if f"{bt_key}_part" not in st.session_state:
                        st.session_state[f"{bt_key}_part"] = 0

                    part_idx = st.session_state[f"{bt_key}_part"]
                    if part_idx < len(parts):
                        pdf_data[pdf_field] = parts[part_idx]
                        st.session_state[f"{bt_key}_part"] += 1
                else:
                    pdf_data[pdf_field] = flattened_data.get(bt_key, "")

            # Clear temp counters
            for k in list(st.session_state.keys()):
                if k.endswith("_part"):
                    del st.session_state[k]

            try:
                reader = PdfReader("resources/OriginalApplication.pdf")
                writer = PdfWriter(clone_from=reader)

                # Update first page
                writer.update_page_form_field_values(
                    writer.pages[0],
                    pdf_data
                )

                pdf_bytes = io.BytesIO()
                writer.write(pdf_bytes)
                pdf_bytes.seek(0)

                st.download_button(
                    label="⬇️ Download Pre-filled Application PDF",
                    data=pdf_bytes,
                    file_name="Compiled_Application.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

main()
