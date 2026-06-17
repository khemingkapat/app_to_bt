"""
PDF ➜ BlueTable Auto-Fill
Iterate through every PDF field, one at a time.
• LEFT  – live PDF page with the current field highlighted
• RIGHT – BlueTable entry form; click a cell to fill it, or click anywhere
          outside the table to skip the current field.
"""

import json
import base64
from io import BytesIO

import streamlit as st
from PIL import Image

from src.blue_table_tools import (
    BLUETABLE_FIELDS,
    load_cache,
    save_cache,
    assign_field,
    clear_field,
    manual_edit_field,
    AssignFieldParams,
    fill_blue_table_docx,
)
from src.pdf_processor.inverter import load_product_config

# Load product config mapping definitions
try:
    product_config = load_product_config("./config/health_and_accident.json")
except Exception:
    product_config = {}

# ── helpers ────────────────────────────────────────────────────────────────


def save_cache_incremental():
    if not st.session_state.get("pdf_id"):
        return
    save_cache(st.session_state.pdf_id, st.session_state.field_mapping)


def save_choices_to_registry(pdf_id: str, field_name: str, choices_map: dict):
    if not pdf_id:
        return
    import json

    registry_path = "./outputs/pdf_registry.json"
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception:
        registry = {}

    if pdf_id in registry:
        for f in registry[pdf_id].get("fields", []):
            if f.get("name") == field_name:
                f["choices_map"] = choices_map
                break

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4, ensure_ascii=False)


def do_assign_choice_option(opt_key, choice_val, bt_key):
    if st.session_state.pdf_id is None:
        return
    idx = st.session_state.field_idx
    current_field = st.session_state.all_fields[idx]
    field_name = current_field.get("name", "?")

    widgets = current_field.get("widgets", [])
    w_idx = st.session_state.widget_idx
    if not widgets or w_idx < 0 or w_idx >= len(widgets):
        return
    raw_choice = widgets[w_idx].get("choice_value", "")
    if not raw_choice:
        return

    choices_map = current_field.get("choices_map", {})
    if choices_map is None:
        choices_map = {}

    # Set the mapping
    choices_map[raw_choice] = choice_val
    current_field["choices_map"] = choices_map

    # Save choice mapping back to pdf_registry.json
    save_choices_to_registry(st.session_state.pdf_id, field_name, choices_map)

    # Update field mapping to target BlueTable key, including choices_map in cache
    st.session_state.field_mapping[field_name] = {
        "bt_key": bt_key,
        "choices_map": choices_map,
    }

    # If the PDF's current value is the one we just mapped, write it to bt_data
    source_val = field_value_hint(current_field, st.session_state.values_map)

    # We update the actual value written to the BlueTable field
    bt_labels = {key: label for label, key in BLUETABLE_FIELDS}
    new_val = rebuild_bt_value(bt_key)
    st.session_state[f"input_{bt_key}"] = new_val
    st.session_state.bt_data[bt_key] = new_val

    # Remove existing log entries for this bt_key to prevent duplicate/stale logs
    st.session_state.assigned = [a for a in st.session_state.assigned if a.get("bt_key") != bt_key]
    st.session_state.assigned.append(
        {
            "field_name": field_name,
            "bt_key": bt_key,
            "bt_label": bt_labels.get(bt_key, bt_key.capitalize()),
            "value": new_val,
            "field_idx": idx,
        }
    )

    # Go to next choice/field choice-by-choice
    st.session_state.widget_idx += 1
    if st.session_state.widget_idx >= len(widgets):
        st.session_state.widget_idx = 0
        st.session_state.field_idx += 1
        if st.session_state.field_idx >= len(st.session_state.all_fields):
            st.session_state.done = True

    save_cache_incremental()


def render_page_with_highlight(
    pdf_bytes: bytes,
    page_num: int,
    field: dict,
    resolution: int = 120,
    highlight_choice_value: str = None,
):
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return None
        page = doc[page_num - 1]
        pdf_h = page.rect.height

        kind = field.get("field_kind")
        if kind == "radio":
            for w in field.get("widgets", []):
                c = w.get("coords")
                choice_val = w.get("choice_value", "")
                if c and w.get("page") == page_num:
                    rect = fitz.Rect(c["x0"], pdf_h - c["y1"], c["x1"], pdf_h - c["y0"])

                    if highlight_choice_value and choice_val == highlight_choice_value:
                        page.draw_rect(
                            rect,
                            color=(0.9, 0.1, 0.1),
                            fill=(0.9, 0.1, 0.1, 0.4),
                            width=3,
                        )
                    else:
                        page.draw_rect(
                            rect, color=(1, 0.63, 0), fill=(1, 0.9, 0, 0.15), width=1.5
                        )

                    if choice_val:
                        # Draw label text slightly above the top-left of the box
                        point = fitz.Point(c["x0"], pdf_h - c["y1"] - 3)
                        # Remove leading slash for cleaner display in label, e.g. /Choice1 -> Choice1
                        display_text = choice_val.lstrip("/")
                        page.insert_text(
                            point, display_text, fontsize=9, color=(0.8, 0, 0)
                        )
        else:
            c = field.get("coords")
            if c:
                rect = fitz.Rect(c["x0"], pdf_h - c["y1"], c["x1"], pdf_h - c["y0"])
                page.draw_rect(rect, color=(1, 0.63, 0), fill=(1, 0.9, 0, 0.4), width=2)

        zoom = resolution / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img

    except Exception as e:
        st.warning(f"Cannot render PDF preview: {e}")
        return None


def field_value_hint(f: dict, values_map: dict) -> str:
    return values_map.get(f.get("name", ""), "")


def get_field_product_line(mapping: dict) -> str:
    """Returns 'SmartCare Essential', 'EasyCare Visa', or 'Both' based on choice values."""
    if not isinstance(mapping, dict):
        return "Both"
    choices_map = mapping.get("choices_map", {})
    values = set(choices_map.values())
    
    essential_unique = {"ESSENTIAL1", "ESSENTIAL2", "ESSENTIAL3", "ESSENTIAL4", "IPD", "IPD+OPD", "IPD+OPD+WELLNESS", "3k * 30 times / year", "50k per year", "0", "20k", "40k"}
    visa_unique = {"VISA1", "VISA2", "300k"}
    
    if values & essential_unique:
        return "SmartCare Essential"
    if values & visa_unique:
        return "EasyCare Visa"
        
    return "Both"


def rebuild_bt_value(bt_key: str) -> str:
    parts = []
    if not st.session_state.get("all_fields") or not st.session_state.get("field_mapping") or not st.session_state.get("values_map"):
        return ""
        
    # Determine currently selected product line
    product_selection = st.session_state.bt_data.get("product_name", "")
    selected_product_line = "SmartCare Essential"
    if "EASYCARE" in product_selection:
        selected_product_line = "EasyCare Visa"
        
    for field in st.session_state.all_fields:
        fname = field.get("name")
        if not fname:
            continue
        mapping = st.session_state.field_mapping.get(fname)
        if not mapping:
            continue
        
        target_key = mapping.get("bt_key") if isinstance(mapping, dict) else mapping
        if target_key != bt_key:
            continue
            
        # Ignore fields that correspond to the non-selected product line
        field_prod_line = get_field_product_line(mapping)
        if field_prod_line != "Both" and field_prod_line != selected_product_line:
            continue
            
        src_val = st.session_state.values_map.get(fname, "")
        if isinstance(mapping, dict):
            choices_map = mapping.get("choices_map", {})
            val = choices_map.get(src_val, "")
        else:
            val = src_val if src_val and not src_val.startswith("/") else ""
            
        if val and val not in parts:
            parts.append(val)
            
    return "-".join(parts)


def sort_key(f):
    page = f.get("page") or 99
    if f.get("field_kind") == "radio":
        widgets = f.get("widgets", [])
        if widgets and widgets[0].get("coords"):
            c = widgets[0]["coords"]
            return (page, round(c.get("canvas_top", 9999), -1), c.get("x0", 9999))
        return (page, 9999, 9999)
    else:
        coords = f.get("coords") or {}
        return (page, round(coords.get("canvas_top", 9999), -1), coords.get("x0", 9999))


# ── session-state bootstrap ────────────────────────────────────────────────


def init_state():
    defaults = {
        "pdf_bytes": None,
        "all_fields": [],
        "field_idx": 0,
        "widget_idx": 0,
        "bt_data": {},
        "skipped": [],
        "assigned": [],
        "values_map": {},
        "done": False,
        "pdf_id": None,
        "cache_saved": False,
        "field_mapping": {},
        "product_config": product_config,
    }
    for _, key in BLUETABLE_FIELDS:
        defaults[f"input_{key}"] = ""

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── page config ────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="PDF ➜ BlueTable")
init_state()

# ── 1. Upload (hidden once a file is loaded) ───────────────────────────────
if st.session_state.pdf_bytes is None:
    st.title("📋 PDF ➜ BlueTable Auto-Fill")
    st.caption(
        "Iterate through every field in the source PDF and map it to the BlueTable — one field at a time."
    )
    uploaded = st.file_uploader("Upload source PDF", type=["pdf"])

    if uploaded:
        # Prevent resetting state on every rerun caused by Streamlit re-executing the script
        if (
            "last_uploaded_name" not in st.session_state
            or st.session_state.last_uploaded_name != uploaded.name
        ):
            raw = uploaded.read()
            st.session_state.pdf_bytes = raw
            st.session_state.field_idx = 0
            st.session_state.bt_data = {}
            st.session_state.skipped = []
            st.session_state.assigned = []
            st.session_state.done = False
            st.session_state.last_uploaded_name = uploaded.name

            from src.pdf_processor.engine import update_pdf_registry

            stream = BytesIO(raw)
            pdf_id, registry_dict, values_dict = update_pdf_registry(stream)

            st.session_state.pdf_id = pdf_id
            st.session_state.values_map = values_dict
            entry = registry_dict.get(pdf_id, {})
            fields = entry.get("fields", [])
            st.session_state.all_fields = sorted(fields, key=sort_key)

            from src.pdf_processor.inverter import load_config_by_pdf_id
            st.session_state.product_config = load_config_by_pdf_id(pdf_id)
            st.session_state.bt_data["pdf_id"] = pdf_id

            # ── Bug fix: guard against empty field list (unrecognised flattened PDF) ──
            if not st.session_state.all_fields:
                st.session_state.pdf_bytes = None  # reset so uploader shows again
                # TODO: Implement Visual Admin Tool: Interactive Click-and-Match UI for structural map templates (Pathway A)
                st.warning(
                    "⚠️ No fields could be found or matched in this PDF. "
                    "If this is a flattened (Print-to-PDF) copy, make sure the "
                    "original AcroForm PDF has been processed first so the registry "
                    "has a word-anchor entry to match against."
                )
                st.stop()

            # ── Restore cache: pre-populate bt_data & assigned WITHOUT advancing field_idx ──
            cache = load_cache(pdf_id)
            if cache:
                st.session_state.field_mapping = cache.copy()
                bt_labels = {key: label for label, key in BLUETABLE_FIELDS}

                # Apply choices_map back to fields
                for field in st.session_state.all_fields:
                    fname = field.get("name", "?")
                    if fname in cache:
                        bt_key_entry = cache[fname]
                        if isinstance(bt_key_entry, dict):
                            field["choices_map"] = bt_key_entry.get("choices_map", {})

                # Determine all unique assigned bt_keys
                unique_keys = set()
                for fname, entry in cache.items():
                    if entry == "SKIPPED":
                        if fname not in st.session_state.skipped:
                            st.session_state.skipped.append(fname)
                    else:
                        bt_key = entry.get("bt_key") if isinstance(entry, dict) else entry
                        unique_keys.add(bt_key)

                # Rebuild values for all mapped keys
                for bt_key in unique_keys:
                    val = rebuild_bt_value(bt_key)
                    st.session_state[f"input_{bt_key}"] = val
                    st.session_state.bt_data[bt_key] = val
                    
                    # Find first field name mapping to this key for reference in the log
                    ref_fname = next((fname for fname, entry in cache.items() if (entry.get("bt_key") if isinstance(entry, dict) else entry) == bt_key), "?")
                    st.session_state.assigned.append({
                        "field_name": ref_fname,
                        "bt_key": bt_key,
                        "bt_label": bt_labels.get(bt_key, bt_key),
                        "value": val,
                        "field_idx": 0,
                    })
                # field_idx intentionally stays at 0 — user reviews from field 1
                # with values already pre-populated from the cache.

            st.rerun()

        if "all_fields" not in st.session_state:
            st.stop()
    else:
        st.info("👆 Upload a PDF to begin.")
        st.stop()

# ── 2. Shorthand refs ──────────────────────────────────────────────────────
pdf_bytes = st.session_state.pdf_bytes
all_fields = st.session_state.all_fields
values_map = st.session_state.values_map
n_fields = len(all_fields)
idx = st.session_state.field_idx

# ── Bug fix: guard against empty field list reaching this point ────────────
if n_fields == 0:
    st.warning("⚠️ No fields are available to process. Please upload a valid PDF.")
    if st.button("🔄 Start Over"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.stop()

# ── 3. Done state ──────────────────────────────────────────────────────────
# Only trigger done when explicitly set — idx >= n_fields is no longer used
# as the completion signal to avoid false positives on cache-restored sessions.
if st.session_state.done:
    st.success("✅ All fields processed!")

    if not st.session_state.get("cache_saved") and st.session_state.pdf_id:
        save_cache(st.session_state.pdf_id, st.session_state.field_mapping)
        st.session_state.cache_saved = True

    col_res, col_dl = st.columns([3, 1])
    with col_res:
        st.subheader("BlueTable Summary")
        from src.blue_table_tools.docx_generator import resolve_plan_combination
        from src.blue_table_tools import apply_acceptance_rules

        st.session_state.bt_data = resolve_plan_combination(st.session_state.bt_data)
        st.session_state.bt_data = apply_acceptance_rules(st.session_state.bt_data)
        for label, key in BLUETABLE_FIELDS:
            val = st.session_state.bt_data.get(key, "")
            if val:
                st.session_state[f"input_{key}"] = val
                st.markdown(f"**{label}**: {val}")

    with col_dl:
        st.subheader("Export")

        import os

        template_docx_path = "./resources/BlueTable.docx"

        if os.path.exists(template_docx_path):
            with st.spinner("Generating filled BlueTable DOCX..."):
                try:
                    docx_stream = fill_blue_table_docx(
                        template_docx_path, st.session_state.bt_data
                    )
                    st.download_button(
                        "⬇ Download Filled DOCX",
                        data=docx_stream.getvalue(),
                        file_name="bluetable_filled.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"Failed to generate DOCX: {e}")
        else:
            st.error(f"Template DOCX not found at: {template_docx_path}")
        if st.button("🔄 Start Over"):
            for k in [
                "pdf_bytes",
                "all_fields",
                "field_idx",
                "bt_data",
                "skipped",
                "assigned",
                "values_map",
                "done",
                "pdf_id",
                "cache_saved",
                "field_mapping",
                "last_uploaded_name",
            ]:
                st.session_state.pop(k, None)
            for _, key in BLUETABLE_FIELDS:
                st.session_state.pop(f"input_{key}", None)
            st.rerun()

    st.subheader("Assignment Log")
    st.json(st.session_state.assigned)
    st.stop()

# ── 4. Current field & Choice Wizard ───────────────────────────────────────
# Clamp idx in case it drifted past the end (e.g. after a back-navigate)
idx = min(idx, n_fields - 1)
st.session_state.field_idx = idx

current_field = all_fields[idx]
field_name = current_field.get("name", "?")
field_kind = current_field.get("field_kind", "text")
field_page = current_field.get("page") or (
    current_field.get("widgets", [{}])[0].get("page", 1)
)
source_value = field_value_hint(current_field, values_map)

widgets = current_field.get("widgets", [])
is_radio = field_kind == "radio"
n_widgets = len(widgets) if (is_radio and widgets) else 1

# Clamp widget_idx
w_idx = min(st.session_state.widget_idx, n_widgets - 1)
st.session_state.widget_idx = w_idx

# Find current choice value
current_choice_value = ""
if is_radio and widgets:
    current_choice_value = widgets[w_idx].get("choice_value", "")
    # Store the current choice value in session state so the callback can read it
    st.session_state[f"sel_choice_{field_name}"] = current_choice_value

# ── 5. Progress + top navigation ──────────────────────────────────────────
pct = idx / n_fields
st.caption(
    f"Field **{idx + 1}** of **{n_fields}** &nbsp;|&nbsp; "
    f"Page **{field_page}** &nbsp;|&nbsp; "
    f"Choice **{w_idx + 1}** of **{n_widgets}** &nbsp;|&nbsp; "
    f"✅ {len(st.session_state.assigned)} assigned &nbsp;|&nbsp; "
    f"⏭ {len(st.session_state.skipped)} skipped"
)
st.progress(pct)

# ── 6. Three-pane layout ───────────────────────────────────────────────────
left, mid, right = st.columns([5, 5, 1], gap="large")

# ── LEFT: PDF preview ──────────────────────────────────────────────────────
with left:
    mapping_meta = st.session_state.field_mapping.get(field_name, {})
    if isinstance(mapping_meta, str):
        mapping_meta = {"bt_key": mapping_meta}
    field_label = mapping_meta.get("label", "")
    field_section = mapping_meta.get("section", "")

    # Check registry choice mappings first, fallback to config
    choices_map = current_field.get("choices_map", {})
    if choices_map is None:
        choices_map = {}

    # Merge with mapping_meta choices if any are present
    meta_choices = mapping_meta.get("choices", {})
    if meta_choices:
        for k, v in meta_choices.items():
            if k not in choices_map:
                choices_map[k] = v

    img = render_page_with_highlight(
        pdf_bytes,
        field_page,
        current_field,
        highlight_choice_value=current_choice_value,
    )
    if img:
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        st.markdown(
            f"""
            <div style="height:80vh; overflow-y:auto; border:1px solid #333; border-radius:6px;">
                <img src="data:image/png;base64,{b64}" style="width:100%;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No preview available for this field.")

    value_to_assign = choices_map.get(source_value, source_value)


# ── MID: BlueTable ─────────────────────────────────────────────────────────
with mid:
    st.markdown("#### 🔵 BlueTable")

    def do_assign(k, i, src_val, f_name, lbl):
        current_input = st.session_state.get(f"input_{k}", "")
        params = AssignFieldParams(
            bt_key=k,
            field_idx=i,
            src_val=src_val,
            field_name=f_name,
            bt_label=lbl,
            bt_data=st.session_state.bt_data,
            assigned=st.session_state.assigned,
            field_mapping=st.session_state.field_mapping,
            current_input=current_input,
        )
        new_val, new_bt_data, new_assigned, new_field_mapping = assign_field(params)
        
        # Overwrite with rebuilt value in reading order
        rebuilt = rebuild_bt_value(k)
        st.session_state[f"input_{k}"] = rebuilt
        new_bt_data[k] = rebuilt
        
        # Keep assigned log entries in sync
        for a in new_assigned:
            if a.get("field_name") == f_name and a.get("bt_key") == k:
                a["value"] = rebuilt

        st.session_state.bt_data = new_bt_data
        st.session_state.assigned = new_assigned
        st.session_state.field_mapping = new_field_mapping

        st.session_state.field_idx += 1
        st.session_state.widget_idx = 0
        save_cache_incremental()
        # Use explicit done flag rather than idx >= n_fields comparison
        if st.session_state.field_idx >= n_fields:
            st.session_state.done = True

    def do_clear(k):
        st.session_state[f"input_{k}"] = ""
        new_bt_data, new_assigned, new_field_mapping = clear_field(
            k,
            st.session_state.bt_data,
            st.session_state.assigned,
            st.session_state.field_mapping,
        )
        st.session_state.bt_data = new_bt_data
        st.session_state.assigned = new_assigned
        st.session_state.field_mapping = new_field_mapping
        save_cache_incremental()

    # ── 1. Plan Options Mapping at the Top of BlueTable Block ──
    product_config_live = st.session_state.get("product_config", {})
    product_options = product_config_live.get("product_options", {})
    if product_options:
        st.caption(
            "Highlight a checkbox on the left, then click an option below to map it."
        )

        # Selected Product mapping row
        product_name_opt = product_options.get("product_name", {})
        if product_name_opt:
            label = product_name_opt.get("label", "Selected Product")
            bt_key = product_name_opt.get("bt_key", "product_name")
            choices = product_name_opt.get("choices", [])

            cols = st.columns([2] + [2] * len(choices))
            with cols[0]:
                st.markdown(
                    f"<span style='font-size:0.85rem; font-weight:bold;'>{label}</span>",
                    unsafe_allow_html=True,
                )
            for i, val in enumerate(choices):
                with cols[i + 1]:
                    st.button(
                        val,
                        key=f"assign_opt_prod_{val}_{idx}",
                        on_click=do_assign_choice_option,
                        args=("product_name", val, bt_key),
                        use_container_width=True,
                    )

        # Determine detected product line from the PDF mapping state
        product_selection = st.session_state.bt_data.get("product_name", "")
        detected_product = "SmartCare Essential"
        if "EASYCARE" in product_selection:
            detected_product = "EasyCare Visa"

        # Let the user select which product line options to view/map, defaulting to the detected one
        product_list = ["SmartCare Essential", "EasyCare Visa"]
        default_idx = product_list.index(detected_product) if detected_product in product_list else 0
        
        selected_product = st.selectbox(
            "Select Product Line Options to Map",
            options=product_list,
            index=default_idx,
            key=f"prod_select_box_{idx}"
        )

        st.markdown(f"**Options for {selected_product}**")
        opts = product_options.get("products", {}).get(selected_product, {})
        with st.container(border=True):
            for opt_key, opt_data in opts.items():
                label = opt_data.get("label", opt_key)
                bt_key = opt_data.get("bt_key", "plan")
                choices = opt_data.get("choices", [])

                cols = st.columns([2] + [2] * len(choices))
                with cols[0]:
                    st.markdown(
                        f"<span style='font-size:0.85rem; font-weight:bold;'>{label}</span>",
                        unsafe_allow_html=True,
                    )
                for i, val in enumerate(choices):
                    with cols[i + 1]:
                        st.button(
                            val,
                            key=f"assign_opt_{opt_key}_{val}_{idx}",
                            on_click=do_assign_choice_option,
                            args=(opt_key, val, bt_key),
                            use_container_width=True,
                        )
    else:
        st.warning("⚠️ No plan configuration is available. Please upload or link a product configuration first.")
        st.page_link("src/pages/config_manager.py", label="Go to Product Config Manager ➡️", icon="⚙️")

    # ── 2. BlueTable Fields Below Plan Options Mapping ──
    from src.blue_table_tools.docx_generator import resolve_plan_combination
    from src.blue_table_tools import apply_acceptance_rules

    st.session_state.bt_data = resolve_plan_combination(st.session_state.bt_data)
    st.session_state.bt_data = apply_acceptance_rules(st.session_state.bt_data)
    status_keys = {
        "plan",
        "deductible",
        "acceptance_conditions",
        "sp_acceptance_conditions",
        "c1_acceptance_conditions",
        "c2_acceptance_conditions",
        "c3_acceptance_conditions",
    }
    for key in status_keys:
        if key in st.session_state.bt_data:
            if st.session_state.get(f"input_{key}") != st.session_state.bt_data[key]:
                st.session_state[f"input_{key}"] = st.session_state.bt_data[key]

    with st.container(height=350):
        for label, key in BLUETABLE_FIELDS:
            existing_val = st.session_state.bt_data.get(key, "")
            col_a, col_b, col_c = st.columns([5, 1.5, 1.5])

            with col_a:
                st.markdown(
                    f"<span style='color:white; font-size:0.85rem;'>{label}</span>",
                    unsafe_allow_html=True,
                )
                edited_val = st.text_input(
                    label,
                    value=existing_val,
                    key=f"input_{key}",
                    placeholder="—",
                    label_visibility="collapsed",
                )

            # Keep bt_data live as user types
            if edited_val != existing_val:
                new_bt_data, new_assigned = manual_edit_field(
                    key,
                    label,
                    edited_val,
                    st.session_state.bt_data,
                    st.session_state.assigned,
                )
                st.session_state.bt_data = new_bt_data
                st.session_state.assigned = new_assigned

            with col_b:
                st.markdown(
                    "<div style='margin-top:28px'></div>", unsafe_allow_html=True
                )
                st.button(
                    "Assign",
                    key=f"assign_{key}_{idx}",
                    on_click=do_assign,
                    args=(key, idx, value_to_assign, field_name, label),
                    use_container_width=True,
                )

            with col_c:
                st.markdown(
                    "<div style='margin-top:28px'></div>", unsafe_allow_html=True
                )
                st.button(
                    "Clear",
                    key=f"clear_{key}_{idx}",
                    on_click=do_clear,
                    args=(key,),
                    use_container_width=True,
                )

# ── RIGHT: navigation ──────────────────────────────────────────────────────
with right:
    st.markdown("<div style='height:360px'></div>", unsafe_allow_html=True)
    if st.button(
        "⬆️",
        disabled=(idx == 0 and st.session_state.widget_idx == 0),
        use_container_width=True,
        help="Previous",
    ):
        is_radio = field_kind == "radio"
        if is_radio and st.session_state.widget_idx > 0:
            st.session_state.widget_idx -= 1
        else:
            st.session_state.field_idx -= 1
            if st.session_state.field_idx < 0:
                st.session_state.field_idx = 0
                st.session_state.widget_idx = 0
            else:
                prev_field = all_fields[st.session_state.field_idx]
                if prev_field.get("field_kind") == "radio" and prev_field.get(
                    "widgets"
                ):
                    st.session_state.widget_idx = len(prev_field["widgets"]) - 1
                else:
                    st.session_state.widget_idx = 0
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("⬇️", use_container_width=True, help="Skip"):
        is_radio = field_kind == "radio"
        if is_radio and widgets:
            st.session_state.widget_idx += 1
            if st.session_state.widget_idx >= len(widgets):
                st.session_state.widget_idx = 0
                if field_name not in st.session_state.field_mapping:
                    st.session_state.field_mapping[field_name] = "SKIPPED"
                    if field_name not in st.session_state.skipped:
                        st.session_state.skipped.append(field_name)
                st.session_state.field_idx += 1
                if st.session_state.field_idx >= n_fields:
                    st.session_state.done = True
        else:
            if field_name not in st.session_state.field_mapping:
                st.session_state.field_mapping[field_name] = "SKIPPED"
                if field_name not in st.session_state.skipped:
                    st.session_state.skipped.append(field_name)
            st.session_state.field_idx += 1
            st.session_state.widget_idx = 0
            if st.session_state.field_idx >= n_fields:
                st.session_state.done = True
        save_cache_incremental()
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("✅", use_container_width=True, help="Finish"):
        st.session_state.done = True
        st.rerun()
