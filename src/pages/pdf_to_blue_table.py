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
)

# ── helpers ────────────────────────────────────────────────────────────────


def save_cache_incremental():
    if not st.session_state.get("pdf_id"):
        return
    save_cache(st.session_state.pdf_id, st.session_state.field_mapping)


def render_page_with_highlight(
    pdf_bytes: bytes, page_num: int, field: dict, resolution: int = 120
):
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return None
        page = doc[page_num - 1]
        pdf_h = page.rect.height

        boxes = []
        kind = field.get("field_kind")
        if kind == "radio":
            for w in field.get("widgets", []):
                c = w.get("coords")
                if c and w.get("page") == page_num:
                    boxes.append(c)
        else:
            c = field.get("coords")
            if c:
                boxes.append(c)

        for c in boxes:
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
    for field in BLUETABLE_FIELDS:
        defaults[f"input_{field.key}"] = ""

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
                bt_labels = {field.key: field.label for field in BLUETABLE_FIELDS}

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
        for field in BLUETABLE_FIELDS:
            val = st.session_state.get(f"input_{field.key}", "")
            if val:
                st.session_state.bt_data[field.key] = val
                st.markdown(f"**{field.label}**: {val}")

    with col_dl:
        st.subheader("Export")
        # TODO: Generate Pre-Filled Official PDF As Truth Anchor for Signature
        result_json = json.dumps(st.session_state.bt_data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇ Download BlueTable JSON",
            data=result_json,
            file_name="bluetable_filled.json",
            mime="application/json",
        )
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
            for field in BLUETABLE_FIELDS:
                st.session_state.pop(f"input_{field.key}", None)
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
    img = render_page_with_highlight(pdf_bytes, field_page, current_field)
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

    st.caption(
        f"🔍 **{field_name}** &nbsp;|&nbsp; type: `{field_kind}` &nbsp;|&nbsp; page: {field_page}"
    )
    if source_value:
        st.code(source_value, language=None)

# ── MID: BlueTable ─────────────────────────────────────────────────────────
with mid:
    st.markdown("#### 🔵 BlueTable")

    def do_assign(k, i, src_val, f_name, lbl):
        current_input = st.session_state.get(f"input_{k}", "")
        new_val, new_bt_data, new_assigned, new_field_mapping = assign_field(
            k,
            i,
            src_val,
            f_name,
            lbl,
            st.session_state.bt_data,
            st.session_state.assigned,
            st.session_state.field_mapping,
            current_input,
        )
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

    with st.container(height=800):
        for field in BLUETABLE_FIELDS:
            existing_val = st.session_state.bt_data.get(field.key, "")
            col_a, col_b, col_c = st.columns([5, 1.5, 1.5])

            with col_a:
                st.markdown(
                    f"<span style='color:white; font-size:0.85rem;'>{field.label}</span>",
                    unsafe_allow_html=True,
                )
                edited_val = st.text_input(
                    field.label,
                    value=existing_val,
                    key=f"input_{field.key}",
                    placeholder="—",
                    label_visibility="collapsed",
                )

            # Keep bt_data live as user types
            if edited_val != existing_val:
                new_bt_data, new_assigned = manual_edit_field(
                    field.key,
                    field.label,
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
                    key=f"assign_{field.key}_{idx}",
                    on_click=do_assign,
                    args=(field.key, idx, source_value, field_name, field.label),
                    use_container_width=True,
                )

            with col_c:
                st.markdown(
                    "<div style='margin-top:28px'></div>", unsafe_allow_html=True
                )
                st.button(
                    "Clear",
                    key=f"clear_{field.key}_{idx}",
                    on_click=do_clear,
                    args=(field.key,),
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
