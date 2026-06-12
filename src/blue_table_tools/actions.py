from dataclasses import dataclass

@dataclass
class AssignFieldParams:
    bt_key: str
    field_idx: int
    src_val: str
    field_name: str
    bt_label: str
    bt_data: dict
    assigned: list
    field_mapping: dict
    current_input: str

def assign_field(params: AssignFieldParams) -> tuple[str, dict, list, dict]:
    """
    Core logic for assigning a field value.
    Updates and returns the current_input value, bt_data dict, assigned list, and field_mapping.
    """
    val_to_write = params.src_val if params.src_val and not params.src_val.startswith("/") else ""
    new_val = f"{params.current_input}-{val_to_write}" if params.current_input else val_to_write

    params.bt_data[params.bt_key] = new_val
    params.field_mapping[params.field_name] = params.bt_key

    # Check if we are updating an existing assignment or adding a new one
    params.assigned.append({
        "field_name": params.field_name,
        "bt_key": params.bt_key,
        "bt_label": params.bt_label,
        "value": new_val,
        "field_idx": params.field_idx,
    })

    return new_val, params.bt_data, params.assigned, params.field_mapping


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
