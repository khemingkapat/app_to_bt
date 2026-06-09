"""
PDF ➜ BlueTable Auto-Fill
Iterate through every PDF field, one at a time.
• LEFT  – live PDF page with the current field highlighted
• RIGHT – BlueTable entry form; click a cell to fill it, or click anywhere
          outside the table to skip the current field.
"""

import json
import math
import os
from io import BytesIO

import pdfplumber
import streamlit as st
from PIL import Image, ImageDraw

# ── paths ──────────────────────────────────────────────────────────────────
REGISTRY_PATH = "pdf_registry.json"
VALUES_PATH = "extracted_values.json"

# ── BlueTable field schema (page 1 of BlueTable) ──────────────────────────
BLUETABLE_FIELDS = [
    # (display_label, bt_key)
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
    # Spouse
    ("Spouse Name", "sp_name"),
    ("Spouse DOB", "sp_dob"),
    ("Spouse ID", "sp_id_card_no"),
    ("Spouse Nationality", "sp_nationality"),
    ("Spouse Beneficiary", "sp_beneficiary"),
    ("Spouse Relation", "sp_bene_relation"),
    ("Spouse Occupation", "sp_occupation"),
    # Child 1
    ("Child 1 Name", "c1_name"),
    ("Child 1 DOB", "c1_dob"),
    ("Child 1 ID", "c1_id_card_no"),
    # Child 2
    ("Child 2 Name", "c2_name"),
    ("Child 2 DOB", "c2_dob"),
    ("Child 2 ID", "c2_id_card_no"),
    # Child 3
    ("Child 3 Name", "c3_name"),
    ("Child 3 DOB", "c3_dob"),
    ("Child 3 ID", "c3_id_card_no"),
]

# ── helpers ────────────────────────────────────────────────────────────────


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {}
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def load_values():
    if not os.path.exists(VALUES_PATH):
        return {}
    with open(VALUES_PATH) as f:
        return json.load(f)


def get_fields_for_pdf(registry: dict, pdf_id: str) -> list:
    """Return fields list sorted by page then y-position (top of page first)."""
    entry = registry.get(pdf_id, {})
    fields = entry.get("fields", [])

    def sort_key(f):
        page = f.get("page") or 99
        # Use first widget coords for radio, else direct coords
        if f.get("field_kind") == "radio":
            widgets = f.get("widgets", [])
            top = widgets[0]["coords"]["canvas_top"] if widgets else 9999
        else:
            coords = f.get("coords") or {}
            top = coords.get("canvas_top", 9999)
        return (page, top)

    return sorted(fields, key=sort_key)


def render_page_with_highlight(
    pdf_bytes: bytes, page_num: int, field: dict, resolution: int = 120
):
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return None
        page = doc[page_num - 1]
        pdf_w = page.rect.width
        pdf_h = page.rect.height

        # Draw highlight before rendering
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


def field_display_name(f: dict) -> str:
    name = f.get("name", "?")
    kind = f.get("field_kind", "")
    value_hint = f.get("value", "")
    label = f"{name}  [{kind}]"
    if value_hint:
        label += f"  → {value_hint}"
    return label


def field_value_hint(f: dict, values_map: dict) -> str:
    """Look up the source PDF field's value or variable name from extracted_values."""
    name = f.get("name", "")
    return values_map.get(name, "")


# ── session-state bootstrap ────────────────────────────────────────────────


def init_state():
    defaults = {
        "pdf_bytes": None,
        "pdf_id": None,
        "all_fields": [],
        "field_idx": 0,
        "bt_data": {},  # bt_key ➜ value
        "skipped": [],
        "assigned": [],  # list of {field_name, bt_key, value}
        "done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── main app ───────────────────────────────────────────────────────────────

st.set_page_config(layout="wide", page_title="PDF ➜ BlueTable")
init_state()

st.title("📋 PDF ➜ BlueTable Auto-Fill")
st.caption(
    "Iterate through every field in the source PDF and map it to the BlueTable — one field at a time."
)

# ── 1. Upload & load ───────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload source PDF (AXA application form)", type=["pdf"])

if uploaded:
    raw = uploaded.read()
    if raw != st.session_state.pdf_bytes:
        st.session_state.pdf_bytes = raw
        st.session_state.field_idx = 0
        st.session_state.bt_data = {}
        st.session_state.skipped = []
        st.session_state.assigned = []
        st.session_state.done = False

        # Just read fields directly from the PDF, no registry needed
        import fitz
        from io import BytesIO

        doc = fitz.open(stream=raw, filetype="pdf")
        fields_list = []
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            for widget in page.widgets():
                field_name = widget.field_name
                rect = widget.rect
                field_type = widget.field_type_string
                field_value = widget.field_value

                existing_field = next((f for f in fields_list if f["name"] == field_name), None)

                if existing_field:
                    if "widgets" not in existing_field:
                        existing_field["widgets"] = [{
                            "page": existing_field["page"],
                            "coords": existing_field["coords"],
                        }]
                    existing_field["widgets"].append({
                        "page": page_num,
                        "coords": {
                            "x0": rect.x0,
                            "y0": rect.y0,
                            "x1": rect.x1,
                            "y1": rect.y1,
                            "canvas_top": rect.y0
                        }
                    })
                else:
                    fields_list.append({
                        "name": field_name,
                        "field_kind": field_type,
                        "page": page_num,
                        "coords": {
                            "x0": rect.x0,
                            "y0": rect.y0,
                            "x1": rect.x1,
                            "y1": rect.y1,
                            "canvas_top": rect.y0
                        },
                        "value": str(field_value),
                    })

        st.session_state.all_fields = fields_list
        doc.close()
        st.rerun()


if st.session_state.pdf_bytes is None:
    st.info("👆 Upload a PDF to begin.")
    st.stop()

# ── 2. Shorthand refs ──────────────────────────────────────────────────────
pdf_bytes = st.session_state.pdf_bytes
all_fields = st.session_state.all_fields
values_map = load_values()
n_fields = len(all_fields)
idx = st.session_state.field_idx

# ── 3. Done state ──────────────────────────────────────────────────────────
if st.session_state.done or idx >= n_fields:
    st.success("✅ All fields processed!")

    col_res, col_dl = st.columns([3, 1])
    with col_res:
        st.subheader("BlueTable Summary")
        for label, key in BLUETABLE_FIELDS:
            val = st.session_state.bt_data.get(key, "")
            if val:
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
                "pdf_id",
                "all_fields",
                "field_idx",
                "bt_data",
                "skipped",
                "assigned",
                "done",
            ]:
                del st.session_state[k]
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

# ── 5. Progress bar ────────────────────────────────────────────────────────
pct = idx / n_fields
st.markdown(
    f'<div class="prog-label">Field {idx + 1} of {n_fields} &nbsp;|&nbsp; '
    f"Page {field_page} &nbsp;|&nbsp; "
    f"{len(st.session_state.assigned)} assigned &nbsp;|&nbsp; "
    f"{len(st.session_state.skipped)} skipped</div>",
    unsafe_allow_html=True,
)
st.progress(pct)

# ── 6. Two-pane layout ─────────────────────────────────────────────────────
left, right = st.columns([5, 5], gap="large")

# ── LEFT: PDF preview ──────────────────────────────────────────────────────
with left:
    st.markdown("### 📄 Source PDF")
    img = render_page_with_highlight(pdf_bytes, field_page, current_field)
    if img:
        st.image(
            img,
            use_container_width=True,
            caption=f"Page {field_page} — highlighted: {field_name}",
        )

    # Field info card
    st.markdown(
        f"""
    <div class="field-card">
      <div class="field-title">🔍 {field_name}</div>
      <div class="field-meta">Type: {field_kind} &nbsp;|&nbsp; Page: {field_page}</div>
      {"<div class='field-value'>" + source_value + "</div>" if source_value else ""}
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Navigation helpers
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("⏮ Previous", disabled=(idx == 0)):
            st.session_state.field_idx -= 1
            st.rerun()
    with nav2:
        if st.button("⏭ Skip field"):
            st.session_state.skipped.append(field_name)
            st.session_state.field_idx += 1
            if st.session_state.field_idx >= n_fields:
                st.session_state.done = True
            st.rerun()
    with nav3:
        if st.button("✅ Finish early"):
            st.session_state.done = True
            st.rerun()

# ── RIGHT: BlueTable ───────────────────────────────────────────────────────
with right:
    st.markdown("### 🔵 BlueTable")
    st.caption(
        "Click **Assign** on any row to map this PDF field's value to that BlueTable field. "
        "Use **Skip** (left panel) to move on without assigning."
    )

    # Pre-fill input: if source_value is a meaningful string, offer it
    user_value = st.text_input(
        "Value to write into BlueTable",
        value=source_value if source_value and not source_value.startswith("/") else "",
        key=f"val_input_{idx}",
        placeholder="Type or confirm the value to assign…",
    )

    st.markdown("---")

    # Render table rows
    assigned_keys = {a["bt_key"] for a in st.session_state.assigned}
    skipped_field_names = set(st.session_state.skipped)

    # Build HTML table and inline buttons side-by-side
    for label, key in BLUETABLE_FIELDS:
        existing_val = st.session_state.bt_data.get(key, "")
        is_filled = bool(existing_val)

        row_class = "filled-row" if is_filled else ""
        col_a, col_b = st.columns([4, 1])

        with col_a:
            filled_display = f" ✓ {existing_val}" if is_filled else ""
            st.markdown(
                f'<div style="padding:4px 0; font-size:0.84rem;">'
                f'<span style="color:#1a3a5c; font-weight:600;">{label}</span>'
                f'<span style="color:#28a745; font-size:0.78rem;">{filled_display}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

        with col_b:
            btn_label = "Re-assign" if is_filled else "Assign"
            if st.button(btn_label, key=f"assign_{key}_{idx}"):
                val_to_write = user_value or source_value
                st.session_state.bt_data[key] = val_to_write
                st.session_state.assigned.append(
                    {
                        "field_name": field_name,
                        "bt_key": key,
                        "bt_label": label,
                        "value": val_to_write,
                        "field_idx": idx,
                    }
                )
                # Auto-advance to next field
                st.session_state.field_idx += 1
                if st.session_state.field_idx >= n_fields:
                    st.session_state.done = True
                st.rerun()

    st.markdown("---")

    # Bulk-skip: click outside / dedicated skip zone
    st.markdown("**Outside the table — skip zone:**")
    if st.button("🚫 Skip this field (no assignment)", use_container_width=True):
        st.session_state.skipped.append(field_name)
        st.session_state.field_idx += 1
        if st.session_state.field_idx >= n_fields:
            st.session_state.done = True
        st.rerun()

    # Jump-to control
    st.markdown("---")

    # We use a distinct key based on idx so that Streamlit doesn't cache the old value
    # when we programmatically change st.session_state.field_idx.
    jump_to = st.number_input(
        "Jump to field #",
        min_value=1,
        max_value=n_fields,
        value=idx + 1,
        step=1,
        key=f"jump_{idx}",
    )
    if st.button("Go"):
        st.session_state.field_idx = jump_to - 1
        st.rerun()
