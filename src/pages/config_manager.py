import json
import os
import streamlit as st

st.set_page_config(layout="wide", page_title="Product Config Manager")

REGISTRY_PATH = "./outputs/pdf_registry.json"
CONFIG_DIR = "./config"
CACHE_PATH = "./outputs/assignment_cache.json"

st.title("⚙️ Product Config Manager")
st.caption(
    "Administrator portal to associate product configuration parameters (pricing, underwriting, etc.) with PDF structural templates."
)

# 1. Load Registry
try:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {}
except Exception as e:
    st.error(f"Error loading PDF registry: {e}")
    registry = {}

if not registry:
    st.warning("⚠️ No PDFs are registered in `pdf_registry.json` yet. Upload a PDF via PDF ➜ BlueTable first to create a registry.")
    st.stop()

# 2. Select PDF
st.subheader("1. Select PDF Template")
pdf_options = []
pdf_labels = {}

for pdf_id, data in registry.items():
    # Gather anchors as label hint
    anchors = data.get("word_anchors", [])
    preview_anchors = ", ".join(anchors[:8]) if anchors else "No word anchors"
    fields_count = len(data.get("fields", []))
    label = f"ID: {pdf_id[:8]}... ({fields_count} fields) - Words: [{preview_anchors}]"
    pdf_options.append(pdf_id)
    pdf_labels[pdf_id] = label

selected_pdf_id = st.selectbox(
    "Choose registered PDF:",
    options=pdf_options,
    format_func=lambda x: pdf_labels[x]
)

# Show detail of selected registry
selected_data = registry[selected_pdf_id]
st.info(f"**Selected PDF ID:** `{selected_pdf_id}`\n\n**Detected Pages:** {len(selected_data.get('pages', []))} | **Detected Fields:** {len(selected_data.get('fields', []))}")

# 3. Enter Configuration
st.subheader("2. Upload or Paste Product JSON Config")

tab_upload, tab_paste = st.tabs(["📤 Upload JSON File", "✍️ Paste JSON Text"])
config_json = None

with tab_upload:
    uploaded_file = st.file_uploader("Upload product config JSON", type=["json"])
    if uploaded_file is not None:
        try:
            config_json = json.load(uploaded_file)
            st.success("File uploaded and parsed successfully!")
        except Exception as e:
            st.error(f"Invalid JSON file: {e}")

with tab_paste:
    json_text = st.text_area(
        "Paste JSON config here:",
        height=300,
        placeholder='{\n    "product_name": "Health and Accident Insurance",\n    "pricing": { ... }\n}'
    )
    if json_text:
        try:
            config_json = json.loads(json_text)
            st.success("JSON parsed successfully!")
        except Exception as e:
            st.error(f"Invalid JSON text: {e}")

# Target filename
default_filename = "health_and_accident.json"
if config_json and "product_name" in config_json:
    clean_name = config_json["product_name"].lower().replace(" ", "_")
    default_filename = f"{clean_name}.json"

target_filename = st.text_input(
    "Target Config Filename:",
    value=default_filename,
    help="The filename to save this config under the ./config folder."
)

if st.button("🔗 Link & Save Configuration", type="primary"):
    if not config_json:
        st.error("Please upload or paste a valid JSON config first.")
    elif not target_filename:
        st.error("Please specify a target filename.")
    else:
        # 1. Add PDF ID to the JSON config
        config_json["pdf_id"] = selected_pdf_id
        
        # 2. Save JSON config file in CONFIG_DIR
        os.makedirs(CONFIG_DIR, exist_ok=True)
        config_path = os.path.join(CONFIG_DIR, target_filename)
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_json, f, indent=4, ensure_ascii=False)
            
            # 3. Save reference link in outputs/assignment_cache.json
            global_cache = {}
            if os.path.exists(CACHE_PATH):
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    try:
                        global_cache = json.load(f)
                    except Exception:
                        pass
            
            entry = global_cache.get(selected_pdf_id, {})
            if not isinstance(entry, dict) or "field_mappings" not in entry:
                # Transform flat cache to structured
                field_mappings = entry if isinstance(entry, dict) else {}
                entry = {
                    "product_config": target_filename,
                    "field_mappings": field_mappings
                }
            else:
                entry["product_config"] = target_filename
                
            global_cache[selected_pdf_id] = entry
            
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(global_cache, f, indent=4, ensure_ascii=False)
                
            st.success(f"🎉 Configuration successfully saved to `{config_path}` and linked to PDF ID `{selected_pdf_id}`!")
            st.json(config_json)
        except Exception as e:
            st.error(f"Error saving configuration: {e}")
