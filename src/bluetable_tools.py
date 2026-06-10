import json
import os

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


def load_cache(pdf_id: str, cache_path: str = "outputs/assignment_cache.json") -> dict:
    """Loads the assignment cache for a specific pdf_id."""
    if not pdf_id:
        return {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                global_cache = json.load(f)
                return global_cache.get(pdf_id, {})
        except Exception:
            return {}
    return {}


def save_cache(pdf_id: str, field_mapping: dict, cache_path: str = "outputs/assignment_cache.json"):
    """Saves the assignment cache incrementally."""
    if not pdf_id:
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    global_cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                global_cache = json.load(f)
            except Exception:
                pass

    global_cache[pdf_id] = field_mapping

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(global_cache, f, indent=4, ensure_ascii=False)


def assign_field(bt_key: str, field_idx: int, src_val: str, field_name: str, bt_label: str, bt_data: dict, assigned: list, field_mapping: dict, current_input: str) -> tuple[str, dict, list, dict]:
    """
    Core logic for assigning a field value.
    Updates and returns the current_input value, bt_data dict, assigned list, and field_mapping.
    """
    val_to_write = src_val if src_val and not src_val.startswith("/") else ""
    new_val = f"{current_input}-{val_to_write}" if current_input else val_to_write

    bt_data[bt_key] = new_val
    field_mapping[field_name] = bt_key

    # Check if we are updating an existing assignment or adding a new one
    assigned.append({
        "field_name": field_name,
        "bt_key": bt_key,
        "bt_label": bt_label,
        "value": new_val,
        "field_idx": field_idx,
    })

    return new_val, bt_data, assigned, field_mapping


def clear_field(bt_key: str, bt_data: dict, assigned: list, field_mapping: dict) -> tuple[dict, list, dict]:
    """
    Core logic for clearing a field value.
    Returns updated bt_data dict, assigned list, and field_mapping.
    """
    if bt_key in bt_data:
        bt_data[bt_key] = ""

    assigned = [a for a in assigned if a.get("bt_key") != bt_key]

    keys_to_remove = []
    for pdf_field, k in field_mapping.items():
        if k == bt_key:
            keys_to_remove.append(pdf_field)

    for pdf_field in keys_to_remove:
        field_mapping.pop(pdf_field, None)

    return bt_data, assigned, field_mapping


def manual_edit_field(bt_key: str, bt_label: str, edited_val: str, bt_data: dict, assigned: list) -> tuple[dict, list]:
    """
    Core logic for handling a manual edit on a field.
    Returns updated bt_data and assigned list.
    """
    bt_data[bt_key] = edited_val
    found = False
    for j in range(len(assigned) - 1, -1, -1):
        if assigned[j]["bt_key"] == bt_key:
            assigned[j]["value"] = edited_val
            found = True
            break
    if not found:
        assigned.append({
            "field_name": "Manual Edit",
            "bt_key": bt_key,
            "bt_label": bt_label,
            "value": edited_val,
            "field_idx": -1,
        })
    return bt_data, assigned
