import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest

from src.blue_table_tools.actions import manual_edit_field


def test_manual_edit_field_existing_assignment():
    """
    Test that manual_edit_field updates an existing assignment and bt_data
    when the bt_key is already present in the assigned list.
    """
    bt_key = "key1"
    bt_label = "Label 1"
    edited_val = "new value"
    bt_data = {
        "key1": "old value",
        "key2": "other value",
    }
    assigned = [
        {"bt_key": "key2", "value": "other value", "field_name": "Field 2", "bt_label": "Label 2", "field_idx": 1},
        {"bt_key": "key1", "value": "old value", "field_name": "Field 1", "bt_label": "Label 1", "field_idx": 0},
        {"bt_key": "key1", "value": "very old value", "field_name": "Field 1", "bt_label": "Label 1", "field_idx": 0},
    ]

    updated_bt_data, updated_assigned = manual_edit_field(bt_key, bt_label, edited_val, bt_data, assigned)

    # Check bt_data is updated
    assert updated_bt_data["key1"] == "new value"
    assert updated_bt_data["key2"] == "other value"

    # Check assigned is updated correctly (only the last occurrence of key1 should be updated based on the loop)
    assert updated_assigned[0] == {"bt_key": "key2", "value": "other value", "field_name": "Field 2", "bt_label": "Label 2", "field_idx": 1}
    assert updated_assigned[1] == {"bt_key": "key1", "value": "old value", "field_name": "Field 1", "bt_label": "Label 1", "field_idx": 0}
    assert updated_assigned[2] == {"bt_key": "key1", "value": "new value", "field_name": "Field 1", "bt_label": "Label 1", "field_idx": 0}

def test_manual_edit_field_new_assignment():
    """
    Test that manual_edit_field appends a new assignment to the assigned list
    and updates bt_data when the bt_key is not yet assigned.
    """
    bt_key = "key3"
    bt_label = "Label 3"
    edited_val = "fresh value"
    bt_data = {
        "key1": "old value",
        "key2": "other value",
    }
    assigned = [
        {"bt_key": "key2", "value": "other value", "field_name": "Field 2", "bt_label": "Label 2", "field_idx": 1},
        {"bt_key": "key1", "value": "old value", "field_name": "Field 1", "bt_label": "Label 1", "field_idx": 0},
    ]

    updated_bt_data, updated_assigned = manual_edit_field(bt_key, bt_label, edited_val, bt_data, assigned)

    # Check bt_data is updated
    assert updated_bt_data["key3"] == "fresh value"
    assert "key1" in updated_bt_data and updated_bt_data["key1"] == "old value"

    # Check assigned has the new manual edit entry
    assert len(updated_assigned) == 3
    new_assignment = updated_assigned[-1]
    assert new_assignment == {
        "field_name": "Manual Edit",
        "bt_key": "key3",
        "bt_label": "Label 3",
        "value": "fresh value",
        "field_idx": -1,
    }
import pytest

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.blue_table_tools.actions import clear_field

def test_clear_field_existing_key():
    bt_data = {"key1": "value1", "key2": "value2"}
    assigned = [
        {"bt_key": "key1", "field_name": "Field_1"},
        {"bt_key": "key2", "field_name": "Field_2"},
    ]
    field_mapping = {"Field_1": "key1", "Field_2": "key2"}

    updated_bt_data, updated_assigned, updated_mapping = clear_field(
        "key1", bt_data, assigned, field_mapping
    )

    assert updated_bt_data == {"key1": "", "key2": "value2"}
    assert updated_assigned == [{"bt_key": "key2", "field_name": "Field_2"}]
    assert updated_mapping == {"Field_2": "key2"}

def test_clear_field_non_existing_key():
    bt_data = {"key1": "value1"}
    assigned = [{"bt_key": "key1", "field_name": "Field_1"}]
    field_mapping = {"Field_1": "key1"}

    updated_bt_data, updated_assigned, updated_mapping = clear_field(
        "non_existent_key", bt_data, assigned, field_mapping
    )

    assert updated_bt_data == {"key1": "value1"}
    assert updated_assigned == [{"bt_key": "key1", "field_name": "Field_1"}]
    assert updated_mapping == {"Field_1": "key1"}

def test_clear_field_multiple_mappings():
    bt_data = {"key1": "value1"}
    assigned = [
        {"bt_key": "key1", "field_name": "Field_1A"},
        {"bt_key": "key1", "field_name": "Field_1B"},
    ]
    field_mapping = {"Field_1A": "key1", "Field_1B": "key1"}

    updated_bt_data, updated_assigned, updated_mapping = clear_field(
        "key1", bt_data, assigned, field_mapping
    )

    assert updated_bt_data == {"key1": ""}
    assert updated_assigned == []
    assert updated_mapping == {}
