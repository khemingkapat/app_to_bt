import sys
import math
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Setup paths
worker_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(worker_dir))
sys.path.insert(0, str(worker_dir / "src"))

from pdf_processor.engine import process_pdf

@pytest.fixture
def mock_pdf_stuff():
    with patch("pdf_processor.engine.PdfReader") as m_reader, \
         patch("pdf_processor.engine.get_pdf_file_id") as m_id, \
         patch("pdf_processor.engine.get_page_dimensions") as m_dim, \
         patch("pdf_processor.engine.get_word_anchors") as m_anchors, \
         patch("pdf_processor.engine.walk_fields") as m_walk, \
         patch("pdf_processor.engine.resolve") as m_resolve:

        reader = MagicMock()
        m_reader.return_value = reader
        m_id.return_value = "TEST_PDF_ID"
        m_dim.return_value = (600, 800)
        m_anchors.return_value = ["Anchor"]
        m_resolve.side_effect = lambda x: x

        yield {
            "reader": reader,
            "m_walk": m_walk,
            "m_resolve": m_resolve
        }

def test_proximity_matching_checkbox(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    # Mock one page
    page = MagicMock()
    reader.pages = [page]

    # Mock a checkbox field
    m_walk.return_value = [
        {
            "field_kind": "checkbox",
            "name": "Check1",
            "value": "",
            "page": 1,
            "coords": {"x0": 100, "y0": 100, "x1": 110, "y1": 110} # Center: 105, 105
        }
    ]

    # Mock a Stamp annotation near the checkbox
    stamp_annot = {
        "/Subtype": "/Stamp",
        "/Rect": [102, 102, 108, 108] # Center: 105, 105. Dist: 0
    }
    page.get.return_value = [stamp_annot]

    pdf_id, reg, values = process_pdf("fake.pdf")

    assert values.get("Check1") == "/Yes"

def test_proximity_matching_radio(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    page = MagicMock()
    reader.pages = [page]

    # Mock a radio field
    m_walk.return_value = [
        {
            "field_kind": "radio",
            "name": "Radio1",
            "value": "",
            "page": 1,
            "widgets": [
                {
                    "page": 1,
                    "choice_value": "Option1",
                    "coords": {"x0": 200, "y0": 200, "x1": 210, "y1": 210} # Center: 205, 205
                },
                {
                    "page": 1,
                    "choice_value": "Option2",
                    "coords": {"x0": 300, "y0": 300, "x1": 310, "y1": 310} # Center: 305, 305
                }
            ]
        }
    ]

    # Mock an Ink annotation near Option2
    ink_annot = {
        "/Subtype": "/Ink",
        "/Rect": [302, 302, 308, 308] # Center: 305, 305. Dist: 0
    }
    page.get.return_value = [ink_annot]

    pdf_id, reg, values = process_pdf("fake.pdf")

    assert values.get("Radio1") == "Option2"

def test_proximity_matching_threshold(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    page = MagicMock()
    reader.pages = [page]

    # Mock a checkbox field
    m_walk.return_value = [
        {
            "field_kind": "checkbox",
            "name": "Check1",
            "value": "",
            "page": 1,
            "coords": {"x0": 100, "y0": 100, "x1": 110, "y1": 110} # Center: 105, 105
        }
    ]

    # Mock a Stamp annotation FAR from the checkbox (> 30 pts)
    # Center: 150, 150. Dist: sqrt(45^2 + 45^2) = 63.6
    stamp_annot = {
        "/Subtype": "/Stamp",
        "/Rect": [145, 145, 155, 155]
    }
    page.get.return_value = [stamp_annot]

    pdf_id, reg, values = process_pdf("fake.pdf")

    assert values.get("Check1") == ""

def test_proximity_matching_wrong_page(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    page1 = MagicMock()
    page2 = MagicMock()
    reader.pages = [page1, page2]

    # Mock a checkbox on page 2
    m_walk.return_value = [
        {
            "field_kind": "checkbox",
            "name": "Check1",
            "value": "",
            "page": 2,
            "coords": {"x0": 100, "y0": 100, "x1": 110, "y1": 110}
        }
    ]

    # Mock a Stamp annotation on page 1 at the same coordinates
    page1.get.return_value = [{
        "/Subtype": "/Stamp",
        "/Rect": [100, 100, 110, 110]
    }]
    page2.get.return_value = []

    pdf_id, reg, values = process_pdf("fake.pdf")

    assert values.get("Check1") == ""

def test_annotation_choice_mapping_with_metadata(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    # Mock metadata containing 'stamp'
    reader.metadata = {"/stamp": "true"}

    page = MagicMock()
    reader.pages = [page]

    # Mock a radio field
    m_walk.return_value = [
        {
            "field_kind": "radio",
            "name": "RadioGrp",
            "value": "",
            "page": 1,
            "widgets": [
                {
                    "page": 1,
                    "choice_value": "ValA",
                    "coords": {"x0": 100, "canvas_top": 100, "x1": 110, "canvas_bottom": 110, "y0": 100, "y1": 110}
                },
                {
                    "page": 1,
                    "choice_value": "ValB",
                    "coords": {"x0": 200, "canvas_top": 200, "x1": 210, "canvas_bottom": 210, "y0": 200, "y1": 210}
                }
            ]
        }
    ]

    # Mock extract_pdf_annotations to return one annotation matching ValB coordinates
    mock_annots = [
        {
            "page": 1,
            "rect": [190, 190, 220, 220],
            "matrix": [[120 if (12 <= y < 18 and 12 <= x < 18) else 255 for x in range(30)] for y in range(30)]
        }
    ]

    with patch("pdf_processor.annotation_matcher.extract_pdf_annotations", return_value=mock_annots):
        pdf_id, reg, values = process_pdf("fake.pdf")

    assert values.get("RadioGrp") == "ValB"

def test_annotation_choice_mapping_without_metadata(mock_pdf_stuff):
    reader = mock_pdf_stuff["reader"]
    m_walk = mock_pdf_stuff["m_walk"]

    # Metadata does not contain stamp or annotation
    reader.metadata = {"/Author": "Tester"}

    page = MagicMock()
    reader.pages = [page]

    # Mock a radio field
    m_walk.return_value = [
        {
            "field_kind": "radio",
            "name": "RadioGrp",
            "value": "",
            "page": 1,
            "widgets": [
                {
                    "page": 1,
                    "choice_value": "ValA",
                    "coords": {"x0": 100, "canvas_top": 100, "x1": 110, "canvas_bottom": 110, "y0": 100, "y1": 110}
                }
            ]
        }
    ]

    mock_annots = [
        {
            "page": 1,
            "rect": [90, 90, 120, 120],
            "matrix": [[120 for x in range(30)] for y in range(30)]
        }
    ]

    with patch("pdf_processor.annotation_matcher.extract_pdf_annotations", return_value=mock_annots):
        pdf_id, reg, values = process_pdf("fake.pdf")

    # Since metadata check fails, flow shouldn't execute and RadioGrp should be empty/unchanged
    assert values.get("RadioGrp") == ""


