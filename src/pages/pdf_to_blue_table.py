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


def render_page_with_highlight(
    pdf_bytes: bytes, page_num: int, field: dict, resolution: int = 120, highlight_choice_value: str = None
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
                        page.draw_rect(rect, color=(0.9, 0.1, 0.1), fill=(0.9, 0.1, 0.1, 0.4), width=3)
                    else:
                        page.draw_rect(rect, color=(1, 0.63, 0), fill=(1, 0.9, 0, 0.15), width=1.5)
                        
                    if choice_val:
                        # Draw label text slightly above the top-left of the box
                        point = fitz.Point(c["x0"], pdf_h - c["y1"] - 3)
                        # Remove leading slash for cleaner display in label, e.g. /Choice1 -> Choice1
                        display_text = choice_val.lstrip("/")
                        page.insert_text(point, display_text, fontsize=9, color=(0.8, 0, 0))
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
        "bt_data": {},
        "skipped": [],
        "assigned": [],
        "values_map": {},
        "done": False,
        "pdf_id": None,
        "cache_saved": False,
        "field_mapping": {},
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

                for field in st.session_state.all_fields:
                    fname = field.get("name", "?")
                    if fname not in cache:
                        continue

                    bt_key = cache[fname]

                    if bt_key == "SKIPPED":
                        # Record the skip but do NOT advance field_idx
                        if fname not in st.session_state.skipped:
                            st.session_state.skipped.append(fname)
                    else:
                        lbl = bt_labels.get(bt_key, bt_key)
                        src_val = values_dict.get(fname, "")
                        val_to_write = (
                            src_val if src_val and not src_val.startswith("/") else ""
                        )
                        current = st.session_state.get(f"input_{bt_key}", "")
                        new_val = (
                            f"{current}-{val_to_write}" if current else val_to_write
                        )

                        st.session_state[f"input_{bt_key}"] = new_val
                        st.session_state.bt_data[bt_key] = new_val
                        st.session_state.assigned.append(
                            {
                                "field_name": fname,
                                "bt_key": bt_key,
                                "bt_label": lbl,
                                "value": new_val,
                                "field_idx": 0,  # placeholder; not used for navigation
                            }
                        )
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
    st.warning(
        "⚠️ No fields are available to process. Please upload a valid PDF."
    )
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
        from src.blue_table_tools import apply_acceptance_rules
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
                    docx_stream = fill_blue_table_docx(template_docx_path, st.session_state.bt_data)
                    st.download_button(
                        "⬇ Download Filled DOCX",
                        data=docx_stream.getvalue(),
                        file_name="bluetable_filled.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary"
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

# ── 4. Current field ───────────────────────────────────────────────────────
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

# ── 5. Progress + top navigation ──────────────────────────────────────────
pct = idx / n_fields
st.caption(
    f"Field **{idx + 1}** of **{n_fields}** &nbsp;|&nbsp; "
    f"Page **{field_page}** &nbsp;|&nbsp; "
    f"✅ {len(st.session_state.assigned)} assigned &nbsp;|&nbsp; "
    f"⏭ {len(st.session_state.skipped)} skipped"
)
st.progress(pct)

# ── 6. Two-pane layout ─────────────────────────────────────────────────────
left, mid, right = st.columns([5, 4, 1], gap="large")

# ── LEFT: PDF preview ──────────────────────────────────────────────────────
with left:
    field_mappings = product_config.get("field_mappings", {})
    mapping_meta = field_mappings.get(field_name, {})
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

    highlight_choice = None
    widgets_list = current_field.get("widgets", [])
    choice_options = [w.get("choice_value", "") for w in widgets_list if w.get("choice_value")]
    
    if field_kind == "radio" and choice_options:
        st.write("🔧 **Choice Mapping Assistant**")
        col_c_sel, col_c_lbl = st.columns([2, 3])
        with col_c_sel:
            selected_choice = st.selectbox(
                "Select checkbox to locate & label:",
                options=choice_options,
                format_func=lambda val: f"{val} ({choices_map.get(val, 'No Label')})",
                key=f"sel_choice_{field_name}"
            )
            highlight_choice = selected_choice
            
        with col_c_lbl:
            current_choice_label = choices_map.get(selected_choice, "")
            new_choice_label = st.text_input(
                f"Readable label for choice `{selected_choice}`:",
                value=current_choice_label,
                key=f"choice_lbl_{field_name}_{selected_choice}"
            )
            if new_choice_label != current_choice_label:
                choices_map[selected_choice] = new_choice_label
                current_field["choices_map"] = choices_map
                save_choices_to_registry(st.session_state.pdf_id, field_name, choices_map)
                st.rerun()

    img = render_page_with_highlight(pdf_bytes, field_page, current_field, highlight_choice_value=highlight_choice)
    if img:
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        st.markdown(
            f"""
            <div style="height:110vh; overflow-y:auto; border:1px solid #333; border-radius:6px;">
                <img src="data:image/png;base64,{b64}" style="width:100%;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No preview available for this field.")

    value_to_assign = choices_map.get(source_value, source_value)

    if field_label:
        st.markdown(f"#### 📋 **{field_label}**")
        st.caption(
            f"Section: `{field_section}` &nbsp;|&nbsp; Field name: `{field_name}` &nbsp;|&nbsp; type: `{field_kind}` &nbsp;|&nbsp; page: {field_page}"
        )
    else:
        st.caption(
            f"🔍 **{field_name}** &nbsp;|&nbsp; type: `{field_kind}` &nbsp;|&nbsp; page: {field_page}"
        )

    if source_value:
        if value_to_assign != source_value:
            st.info(f"👉 **Selected Option:** {value_to_assign} (raw: `{source_value}`)")
        else:
            st.code(source_value, language=None)

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
        st.session_state[f"input_{k}"] = new_val
        st.session_state.bt_data = new_bt_data
        st.session_state.assigned = new_assigned
        st.session_state.field_mapping = new_field_mapping

        st.session_state.field_idx += 1
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

    from src.blue_table_tools import apply_acceptance_rules
    st.session_state.bt_data = apply_acceptance_rules(st.session_state.bt_data)
    status_keys = {
        "acceptance_conditions",
        "sp_acceptance_conditions",
        "c1_acceptance_conditions",
        "c2_acceptance_conditions",
        "c3_acceptance_conditions"
    }
    for key in status_keys:
        if key in st.session_state.bt_data:
            if st.session_state.get(f"input_{key}") != st.session_state.bt_data[key]:
                st.session_state[f"input_{key}"] = st.session_state.bt_data[key]

    with st.container(height=800):
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
    if st.button("⬆️", disabled=(idx == 0), use_container_width=True, help="Previous"):
        st.session_state.field_idx -= 1
        st.rerun()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("⬇️", use_container_width=True, help="Skip"):
        if field_name not in st.session_state.field_mapping:
            st.session_state.skipped.append(field_name)
            st.session_state.field_mapping[field_name] = "SKIPPED"
            save_cache_incremental()
        st.session_state.field_idx += 1
        if st.session_state.field_idx >= n_fields:
            st.session_state.done = True
        st.rerun()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("✅", use_container_width=True, help="Finish"):
        st.session_state.done = True
        st.rerun()
