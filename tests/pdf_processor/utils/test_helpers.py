import pytest
from pdf_processor.utils.helpers import rect_to_dict

def test_rect_to_dict_none():
    """Test passing None returns None."""
    assert rect_to_dict(None) is None

def test_rect_to_dict_basic():
    """Test passing a valid 4-element list of coordinates."""
    rect = [10.5, 20.2, 110.5, 120.2]
    expected = {
        "x0": 10.5,
        "y0": 20.2,
        "x1": 110.5,
        "y1": 120.2,
        "width": 100.0,
        "height": 100.0,
    }
    assert rect_to_dict(rect) == expected

def test_rect_to_dict_with_page_height():
    """Test passing a valid rect and page_height adds canvas properties."""
    rect = [10.5, 20.2, 110.5, 120.2]
    page_height = 800.0
    expected = {
        "x0": 10.5,
        "y0": 20.2,
        "x1": 110.5,
        "y1": 120.2,
        "width": 100.0,
        "height": 100.0,
        "canvas_top": 679.8,     # 800.0 - 120.2
        "canvas_bottom": 779.8,  # 800.0 - 20.2
    }
    assert rect_to_dict(rect, page_height=page_height) == expected

def test_rect_to_dict_invalid_size():
    """Test passing a list with incorrect number of elements returns None."""
    # Too few
    assert rect_to_dict([10, 20, 100]) is None
    # Too many
    assert rect_to_dict([10, 20, 100, 200, 300]) is None

def test_rect_to_dict_invalid_elements():
    """Test passing non-convertible elements returns None."""
    assert rect_to_dict(["a", "b", "c", "d"]) is None
    assert rect_to_dict([10, 20, "c", 100]) is None

def test_rect_to_dict_invalid_type():
    """Test passing a completely invalid type returns None."""
    assert rect_to_dict("not a list or tuple") is None
    assert rect_to_dict({"x": 10, "y": 20}) is None
