import sys
from pathlib import Path
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
