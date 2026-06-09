import streamlit as st
import pdfplumber
import json
import os
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

# Initialize system settings
st.set_page_config(layout="wide")
TEMPLATE_DIR = "templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# 1. State Initializer
if "current_map" not in st.session_state:
    st.session_state.current_map = []
if "temp_coords" not in st.session_state:
    st.session_state.temp_coords = None

st.title("🛡️ Application-to-BlueTable Layout Mapper (POC)")
st.subheader("Visual Field Configuration & Target Schema Directory")

# 2. File Ingestion Layer
uploaded_file = st.file_uploader("Upload OriginalApplication.pdf", type=["pdf"])

if uploaded_file:
    # Read backend data bytes directly using pdfplumber
    with pdfplumber.open(uploaded_file) as pdf:
        total_pages = len(pdf.pages)

        # Multi-page selection control
        page_num = st.sidebar.number_input(
            f"Select Page (1 to {total_pages})",
            min_value=1,
            max_value=total_pages,
            value=1,
        )
        current_page = pdf.pages[page_num - 1]

        # Convert the structural PDF page to a visual PIL image for canvas rendering
        page_image = current_page.to_image(resolution=150).original
        width, height = page_image.size

    # 3. Side-by-Side Interface Splitting
    left_pane, right_pane = st.columns([6, 4])

    with left_pane:
        st.markdown("### 🗺️ Left Pane: Interactive Document Canvas")
        st.info("Click directly on any empty form label space to capture coordinates.")

        # Render interactive image canvas and listen to local click events
        value = streamlit_image_coordinates(page_image, key="canvas")

        if value:
            # Capture exact visual pixel coordinates on click
            st.session_state.temp_coords = {
                "x": value["x"],
                "y": value["y"],
                "page": page_num,
            }
            st.success(
                f"Captured Target Location: X={value['x']}, Y={value['y']} on Page {page_num}"
            )

    with right_pane:
        st.markdown("### 📋 Right Pane: Target Schema Directory")

        # Define standard target company fields from BlueTable template configuration
        standard_fields = [
            "main_insured_name",
            "main_insured_dob",
            "main_insured_id_passport",
            "main_insured_address",
            "main_insured_mobile",
            "main_insured_email",
            "plan_selection",
        ]

        selected_field = st.selectbox(
            "Assign Captured Coordinates to Schema Variable:", standard_fields
        )

        # Binding mechanism
        if st.button("Bind Selection to Schema Token") and st.session_state.temp_coords:
            binding_token = {
                "target_schema_key": selected_field,
                "page": st.session_state.temp_coords["page"],
                "coordinates": {
                    "click_x": st.session_state.temp_coords["x"],
                    "click_y": st.session_state.temp_coords["y"],
                    "canvas_width": width,
                    "canvas_height": height,
                },
            }
            # Append binding straight into local in-memory active stream state
            st.session_state.current_map.append(binding_token)
            st.session_state.temp_coords = None  # Reset buffer
            st.toast(f"Bound {selected_field} successfully!")

        # Display current template build status
        st.markdown("#### Active Configuration Mapping Buffer")
        st.json(st.session_state.current_map)

        # 4. JSON Serialization Layer (Local Save)
        template_name = st.text_input(
            "Enter Unique Template Identifier Key:", value="axa_health_v1"
        )
        if st.button("💾 Save Template Layout Configuration"):
            if st.session_state.current_map:
                output_payload = {
                    "template_id": template_name,
                    "fields_map": st.session_state.current_map,
                }

                # Write to local file storage directory
                filepath = os.path.join(TEMPLATE_DIR, f"{template_name}.json")
                with open(filepath, "w") as f:
                    json.dump(output_payload, f, indent=2)
                st.success(f"Template maps saved locally to: `{filepath}`")
            else:
                st.error("Cannot export empty map. Bind configurations first.")
