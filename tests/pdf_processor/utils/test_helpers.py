import pytest
from unittest.mock import Mock

from src.pdf_processor.utils.helpers import get_page_dimensions

def test_get_page_dimensions_with_valid_mediabox():
    mock_page = Mock()
    mock_page.mediabox = [0, 0, 500, 600]
    width, height = get_page_dimensions(mock_page)
    assert width == 500.0
    assert height == 600.0

def test_get_page_dimensions_with_string_mediabox():
    mock_page = Mock()
    mock_page.mediabox = ["0", "0", "800.5", "1000.25"]
    width, height = get_page_dimensions(mock_page)
    assert width == 800.5
    assert height == 1000.25

def test_get_page_dimensions_with_none_page():
    width, height = get_page_dimensions(None)
    assert width == 595.27
    assert height == 842.0

def test_get_page_dimensions_with_no_mediabox():
    mock_page = Mock()
    mock_page.mediabox = None
    width, height = get_page_dimensions(mock_page)
    assert width == 595.27
    assert height == 842.0

def test_get_page_dimensions_with_non_zero_origin():
    mock_page = Mock()
    mock_page.mediabox = [50, 60, 550, 660]
    width, height = get_page_dimensions(mock_page)
    assert width == 500.0
    assert height == 600.0
