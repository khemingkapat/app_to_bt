import json
import os
from io import BytesIO
from typing import Union
from pypdf import PdfReader, PdfWriter

CONFIG_FILE = "./config/health_and_accident.json"

# TODO: Add support for secure PDF signature stamps and digital watermarking on filled applications.


def load_product_config(config_path: str = CONFIG_FILE) -> dict:
    """Loads the product configuration schema."""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(f"Configuration file not found at: {config_path}")


def parse_date_part(date_str: str, part: str) -> str:
    """
    Parses a date string (YYYY-MM-DD or DD/MM/YYYY) and returns the requested part.
    part can be 'DD', 'MM', or 'YYYY'.
    """
    if not date_str:
        return ""

    # Try separating by dashes or slashes
    parts = []
    if "-" in date_str:
        parts = date_str.split("-")
        # Check if YYYY is first or last
        if len(parts[0]) == 4:
            # YYYY-MM-DD
            year, month, day = parts[0], parts[1], parts[2]
        else:
            # DD-MM-YYYY
            day, month, year = parts[0], parts[1], parts[2]
    elif "/" in date_str:
        parts = date_str.split("/")
        if len(parts[2]) == 4:
            # DD/MM/YYYY
            day, month, year = parts[0], parts[1], parts[2]
        else:
            # YYYY/MM/DD
            year, month, day = parts[0], parts[1], parts[2]
    else:
        return date_str  # Return as is if unparseable

    if part == "DD":
        return day.zfill(2)
    elif part == "MM":
        return month.zfill(2)
    elif part == "YYYY":
        return year
    return date_str


def map_customer_data_to_pdf(customer_data: dict, config: dict) -> dict:
    """
    Maps standard customer data fields to physical PDF AcroForm field values based on schema.
    Handles split fields like DOB.
    """
    pdf_values = {}
    field_mappings = config.get("field_mappings", {})

    for pdf_field, mapping in field_mappings.items():
        bt_key = mapping.get("bt_key")
        label = mapping.get("label", "").upper()

        if bt_key not in customer_data:
            continue

        value = customer_data[bt_key]
        if value is None:
            value = ""

        # Handle date parts for DOB fields
        if "dob" in bt_key or "date" in bt_key:
            date_str = str(value)
            if "DAY" in label or "(DD)" in label:
                pdf_values[pdf_field] = parse_date_part(date_str, "DD")
            elif "MONTH" in label or "(MM)" in label:
                pdf_values[pdf_field] = parse_date_part(date_str, "MM")
            elif "YEAR" in label or "(YYYY)" in label:
                pdf_values[pdf_field] = parse_date_part(date_str, "YYYY")
            else:
                pdf_values[pdf_field] = date_str
        else:
            pdf_values[pdf_field] = str(value)

    return pdf_values


def fill_acroform_pdf(
    input_pdf: Union[str, BytesIO], customer_data: dict, config_path: str = CONFIG_FILE
) -> BytesIO:
    """
    Reads an interactive AcroForm PDF, populates its fields with customer data
    using the config schema, and returns a pre-filled PDF as a BytesIO stream.
    """
    config = load_product_config(config_path)
    pdf_values = map_customer_data_to_pdf(customer_data, config)

    # Load input PDF
    if isinstance(input_pdf, str):
        reader = PdfReader(input_pdf)
    else:
        input_pdf.seek(0)
        reader = PdfReader(input_pdf)

    writer = PdfWriter()
    writer.append(reader)

    # Update form fields page by page
    # pypdf requires specifying page when updating field values
    for page in writer.pages:
        # We can pass the whole dict; pypdf will only update fields matching names on that page
        writer.update_page_form_field_values(page, pdf_values)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream
