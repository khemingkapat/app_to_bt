import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Setup paths
worker_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(worker_dir))
sys.path.insert(0, str(worker_dir / "src"))

from pdf_processor.engine import process_pdf

@pytest.fixture
def mock_pdf_reader():
    with patch("pdf_processor.engine.PdfReader") as mock:
        reader = MagicMock()
        reader.pages = [MagicMock()]
        reader.trailer = {"/Root": {}}
        mock.return_value = reader
        yield reader

@pytest.fixture
def mock_helpers():
    with patch("pdf_processor.engine.get_pdf_file_id") as m_id, \
         patch("pdf_processor.engine.get_page_dimensions") as m_dim, \
         patch("pdf_processor.engine.get_word_anchors") as m_anchors, \
         patch("pdf_processor.engine.extract_text_from_coords") as m_extract, \
         patch("pdf_processor.engine.resolve") as m_resolve:

        m_id.return_value = "PDF_ID_1"
        m_dim.return_value = (600, 800)
        m_anchors.return_value = ["Anchor1", "Anchor2"]
        m_extract.return_value = {"field1": "value1"}
        m_resolve.return_value = {}

        yield {
            "get_pdf_file_id": m_id,
            "get_page_dimensions": m_dim,
            "get_word_anchors": m_anchors,
            "extract_text_from_coords": m_extract,
            "resolve": m_resolve
        }

def test_flattened_pdf_id_match_first(mock_pdf_reader, mock_helpers):
    """Test Case 1: Flattened PDF with known ID and matching anchors.
    Should match immediately even if another entry with matching anchors comes first in the registry.
    """
    registry = {
        "OTHER_ID": {
            "word_anchors": ["Anchor1"], # Matches
            "fields": [{"name": "field_other"}],
            "structural_hash": "hash_other"
        },
        "PDF_ID_1": {
            "word_anchors": ["Anchor1", "Anchor2"], # Matches
            "fields": [{"name": "field_correct"}],
            "structural_hash": "hash_correct"
        }
    }

    # PDF ID is PDF_ID_1. Anchors are ["Anchor1", "Anchor2"].
    # Current code would pick "OTHER_ID" because it's first in the registry and matches.
    # New code should pick "PDF_ID_1" because it checks by ID first.

    pdf_id, reg, vals = process_pdf("fake.pdf", existing_registry=registry)

    # This will fail with current code because it picks OTHER_ID
    assert pdf_id == "PDF_ID_1"
    args = mock_helpers["extract_text_from_coords"].call_args[0]
    assert args[1] == [{"name": "field_correct"}]

def test_flattened_pdf_id_mismatch_fallback_success(mock_pdf_reader, mock_helpers):
    """Test Case 2: Flattened PDF with known ID but mismatched anchors (should fallback to full scan)."""
    registry = {
        "PDF_ID_1": {
            "word_anchors": ["CompletelyDifferent"],
            "fields": [{"name": "field_wrong"}],
            "structural_hash": "hash_wrong"
        },
        "MATCHING_ID": {
            "word_anchors": ["Anchor2"],
            "fields": [{"name": "field_correct"}],
            "structural_hash": "hash_correct"
        }
    }

    # PDF ID is PDF_ID_1. Anchors are ["Anchor1", "Anchor2"].
    # PDF_ID_1 anchors in registry don't match.
    # Full scan should find MATCHING_ID because of "Anchor2".

    pdf_id, reg, vals = process_pdf("fake.pdf", existing_registry=registry)

    assert pdf_id == "MATCHING_ID"
    args = mock_helpers["extract_text_from_coords"].call_args[0]
    assert args[1] == [{"name": "field_correct"}]

def test_flattened_pdf_unknown_id_fallback_success(mock_pdf_reader, mock_helpers):
    """Test Case 3: Flattened PDF with unknown ID but matching anchors in registry (should match via fallback)."""
    registry = {
        "MATCHING_ID": {
            "word_anchors": ["Anchor1"],
            "fields": [{"name": "field_correct"}],
            "structural_hash": "hash_correct"
        }
    }

    mock_helpers["get_pdf_file_id"].return_value = "NEW_PDF_ID"

    pdf_id, reg, vals = process_pdf("fake.pdf", existing_registry=registry)

    assert pdf_id == "MATCHING_ID"
    args = mock_helpers["extract_text_from_coords"].call_args[0]
    assert args[1] == [{"name": "field_correct"}]

def test_flattened_pdf_no_match(mock_pdf_reader, mock_helpers):
    """Test Case 4: Flattened PDF with unknown ID and no matching anchors (unidentified)."""
    registry = {
        "SOME_ID": {
            "word_anchors": ["Different"],
            "fields": [{"name": "field"}],
            "structural_hash": "hash"
        }
    }

    mock_helpers["get_pdf_file_id"].return_value = "NEW_PDF_ID"

    pdf_id, reg, vals = process_pdf("fake.pdf", existing_registry=registry)

    assert pdf_id == "NEW_PDF_ID"
    assert vals == {} # No fields to extract from
    assert reg["NEW_PDF_ID"]["word_anchors"] == ["Anchor1", "Anchor2"]
