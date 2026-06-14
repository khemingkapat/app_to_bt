import os
from io import BytesIO
from pypdf import PdfReader
from src.pdf_processor.inverter import parse_date_part, map_customer_data_to_pdf, fill_acroform_pdf, load_product_config

def test_parse_date_part():
    # Test hyphen format
    assert parse_date_part("1995-12-25", "YYYY") == "1995"
    assert parse_date_part("1995-12-25", "MM") == "12"
    assert parse_date_part("1995-12-25", "DD") == "25"

    # Test slash format
    assert parse_date_part("25/12/1995", "YYYY") == "1995"
    assert parse_date_part("25/12/1995", "MM") == "12"
    assert parse_date_part("25/12/1995", "DD") == "25"

    # Empty date
    assert parse_date_part("", "DD") == ""

def test_map_customer_data_to_pdf():
    config = load_product_config()
    customer_data = {
        "name": "Jane Doe",
        "dob": "1988-04-15",
        "sp_name": "John Doe",
        "sp_dob": "1985-08-20",
        "c1_name": "Jimmy Doe",
        "c1_dob": "2015-11-05"
    }
    
    pdf_values = map_customer_data_to_pdf(customer_data, config)
    
    # Check name mapping
    assert pdf_values.get("Text2") == "Jane Doe"
    
    # Check main insured DOB mapping
    assert pdf_values.get("Text3") == "15"
    assert pdf_values.get("Text4") == "04"
    assert pdf_values.get("Text5") == "1988"
    
    # Check spouse name mapping
    assert pdf_values.get("Text23") == "John Doe"
    
    # Check spouse DOB mapping
    assert pdf_values.get("Text24") == "20"
    assert pdf_values.get("Text25") == "08"
    assert pdf_values.get("Text26") == "1985"
    
    # Check child 1 name mapping
    assert pdf_values.get("Text39") == "Jimmy Doe"

def test_fill_acroform_pdf():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    original_pdf_path = os.path.join(repo_root, "resources", "OriginalApplication.pdf")
    
    assert os.path.exists(original_pdf_path), f"Template not found at: {original_pdf_path}"
    
    customer_data = {
        "name": "Alex Mercer",
        "dob": "1990-10-31",
        "id_card_no": "1234567890123",
        "tel": "0812345678"
    }
    
    filled_pdf_stream = fill_acroform_pdf(original_pdf_path, customer_data)
    
    # Load filled PDF using PdfReader to inspect fields
    reader = PdfReader(filled_pdf_stream)
    
    # Verify that the output PDF has pages
    assert len(reader.pages) > 0
