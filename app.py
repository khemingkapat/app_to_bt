"""
PDF ➜ BlueTable Auto-Fill
Iterate through every PDF field, one at a time.
• LEFT  – live PDF page with the current field highlighted
• RIGHT – BlueTable entry form; click a cell to fill it, or click anywhere
          outside the table to skip the current field.
"""

import json
import os
from io import BytesIO

import streamlit as st
from PIL import Image

# ── BlueTable field schema ─────────────────────────────────────────────────
BLUETABLE_FIELDS = [
    ("Main Insured", "name"),
    ("Date of Birth", "dob"),
    ("Age", "age"),
    ("ID No./Passport No.", "id_card_no"),
    ("Nationality", "nationality"),
    ("Beneficiary Name", "beneficiary"),
    ("Relation", "bene_relation"),
    ("Occupation", "occupation"),
    ("Agent CODE/Name", "agent"),
    ("Plan", "plan"),
    ("Deductible", "deductible"),
    ("Premium", "premium"),
    ("Effective Date", "effective_date"),
    ("Personal Address", "present_address"),
    ("Tel", "tel"),
    ("Email", "email"),
    ("Payor Name", "payor_name"),
    ("Payor Address", "payor_address"),
    ("TAX ID", "tax_id"),
    ("Acceptance Conditions", "acceptance_conditions"),
    ("Exclusions", "exclusions"),
    ("Spouse Name", "sp_name"),
    ("Spouse DOB", "sp_dob"),
    ("Spouse ID", "sp_id_card_no"),
    ("Spouse Nationality", "sp_nationality"),
    ("Spouse Beneficiary", "sp_beneficiary"),
    ("Spouse Relation", "sp_bene_relation"),
    ("Spouse Occupation", "sp_occupation"),
    ("Child 1 Name", "c1_name"),
    ("Child 1 DOB", "c1_dob"),
    ("Child 1 ID", "c1_id_card_no"),
    ("Child 2 Name", "c2_name"),
    ("Child 2 DOB", "c2_dob"),
    ("Child 2 ID", "c2_id_card_no"),
    ("Child 3 Name", "c3_name"),
    ("Child 3 DOB", "c3_dob"),
    ("Child 3 ID", "c3_id_card_no"),
]

# ── helpers ────────────────────────────────────────────────────────────────

def save_cache_incremental():
    if not st.session_state.get("pdf_id"):
        return
    cache_path = os.path.join("outputs", "assignment_cache.json")
    os.makedirs("outputs", exist_ok=True)
    global_cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                global_cache = json.load(f)
            except Exception:
                pass

    global_cache[st.session_state.pdf_id] = st.session_state.field_mapping

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(global_cache, f, indent=4, ensure_ascii=False)


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
        raw = uploaded.read()
        st.session_state.pdf_bytes = raw
        st.session_state.field_idx = 0
        st.session_state.bt_data = {}
        st.session_state.skipped = []
        st.session_state.assigned = []
        st.session_state.done = False

        with open("temp_upload.pdf", "wb") as f:
            f.write(raw)

        from src.pdf_processor.engine import process_pdf

        pdf_id, registry_dict, values_dict = process_pdf("temp_upload.pdf")

        st.session_state.pdf_id = pdf_id
        st.session_state.values_map = values_dict
        entry = registry_dict.get(pdf_id, {})
        fields = entry.get("fields", [])
        st.session_state.all_fields = sorted(fields, key=sort_key)

        cache_path = os.path.join("outputs", "assignment_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    global_cache = json.load(f)
            except Exception:
                global_cache = {}

            cache = global_cache.get(pdf_id, {})
            st.session_state.field_mapping = cache.copy()

            # Helper to find label for bt_key
            bt_labels = {key: label for label, key in BLUETABLE_FIELDS}

            for field in st.session_state.all_fields:
                fname = field.get("name", "?")
                if fname in cache:
                    bt_key = cache[fname]
                    if bt_key == "SKIPPED":
                        st.session_state.skipped.append(fname)
                        st.session_state.field_idx += 1
                    else:
                        lbl = bt_labels.get(bt_key, bt_key)
                        src_val = values_dict.get(fname, "")
                        val_to_write = src_val if src_val and not src_val.startswith("/") else ""
                        current = st.session_state.get(f"input_{bt_key}", "")
                        new_val = f"{current}-{val_to_write}" if current else val_to_write

                        st.session_state[f"input_{bt_key}"] = new_val
                        st.session_state.bt_data[bt_key] = new_val
                        st.session_state.assigned.append({
                            "field_name": fname,
                            "bt_key": bt_key,
                            "bt_label": lbl,
                            "value": new_val,
                            "field_idx": st.session_state.field_idx,
                        })
                        st.session_state.field_idx += 1

            if st.session_state.field_idx >= len(st.session_state.all_fields):
                st.session_state.done = True

        st.rerun()

    st.info("👆 Upload a PDF to begin.")
    st.stop()

# ── 2. Shorthand refs ──────────────────────────────────────────────────────
pdf_bytes = st.session_state.pdf_bytes
all_fields = st.session_state.all_fields
values_map = st.session_state.values_map
n_fields = len(all_fields)
idx = st.session_state.field_idx

# ── 3. Done state ──────────────────────────────────────────────────────────
if st.session_state.done or idx >= n_fields:
    st.success("✅ All fields processed!")

    if not st.session_state.get("cache_saved") and st.session_state.pdf_id:
        cache_path = os.path.join("outputs", "assignment_cache.json")
        os.makedirs("outputs", exist_ok=True)
        global_cache = {}
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                try:
                    global_cache = json.load(f)
                except Exception:
                    pass

        global_cache[st.session_state.pdf_id] = st.session_state.field_mapping

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(global_cache, f, indent=4, ensure_ascii=False)
        st.session_state.cache_saved = True

    col_res, col_dl = st.columns([3, 1])
    with col_res:
        st.subheader("BlueTable Summary")
        for label, key in BLUETABLE_FIELDS:
            val = st.session_state.get(f"input_{key}", "")
            if val:
                st.session_state.bt_data[key] = val
                st.markdown(f"**{label}**: {val}")

    with col_dl:
        st.subheader("Export")
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
            ]:
                del st.session_state[k]
            for _, key in BLUETABLE_FIELDS:
                if f"input_{key}" in st.session_state:
                    del st.session_state[f"input_{key}"]
            st.rerun()

    st.subheader("Assignment Log")
    st.json(st.session_state.assigned)
    st.stop()

# ── 4. Current field ───────────────────────────────────────────────────────
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

st.divider()

# ── 6. Two-pane layout ─────────────────────────────────────────────────────
left, mid, right = st.columns([5, 4, 1], gap="large")

# ── LEFT: PDF preview ──────────────────────────────────────────────────────
with left:
    img = render_page_with_highlight(pdf_bytes, field_page, current_field)
    if img:
        buf = BytesIO()
        img.save(buf, format="PNG")
        import base64

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
# ── RIGHT: BlueTable ───────────────────────────────────────────────────────
with mid:
    st.markdown("#### 🔵 BlueTable")

    def do_assign(k, i, src_val, f_name, lbl):
        val_to_write = src_val if src_val and not src_val.startswith("/") else ""
        current = st.session_state.get(f"input_{k}", "")
        new_val = f"{current}-{val_to_write}" if current else val_to_write
        st.session_state[f"input_{k}"] = new_val
        st.session_state.field_mapping[f_name] = k
        st.session_state.assigned.append(
            {
                "field_name": f_name,
                "bt_key": k,
                "bt_label": lbl,
                "value": new_val,
                "field_idx": i,
            }
        )
        st.session_state.field_idx += 1
        save_cache_incremental()
        if st.session_state.field_idx >= n_fields:
            st.session_state.done = True

    def do_clear(k):
        st.session_state[f"input_{k}"] = ""
        if k in st.session_state.bt_data:
            st.session_state.bt_data[k] = ""

        st.session_state.assigned = [
            a for a in st.session_state.assigned if a.get("bt_key") != k
        ]

        keys_to_remove = []
        for pdf_field, bt_key in st.session_state.field_mapping.items():
            if bt_key == k:
                keys_to_remove.append(pdf_field)
        for pdf_field in keys_to_remove:
            st.session_state.field_mapping.pop(pdf_field, None)

        save_cache_incremental()

    st.divider()

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
                st.session_state.bt_data[key] = edited_val

        with col_b:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            st.button(
                "Assign",
                key=f"assign_{key}_{idx}",
                on_click=do_assign,
                args=(key, idx, source_value, field_name, label),
                use_container_width=True,
            )

        with col_c:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            st.button(
                "Clear",
                key=f"clear_{key}_{idx}",
                on_click=do_clear,
                args=(key,),
                use_container_width=True,
            )

with right:
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    if st.button("⏮", disabled=(idx == 0), use_container_width=True, help="Previous"):
        st.session_state.field_idx -= 1
        st.rerun()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("⏭", use_container_width=True, help="Skip"):
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
