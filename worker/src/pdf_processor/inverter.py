import json
import os
from io import BytesIO
from typing import Union
from pypdf import PdfReader, PdfWriter

CONFIG_FILE = "./config/health_and_accident_insurance.json"

# TODO: Add support for secure PDF signature stamps and digital watermarking on filled applications.


def load_product_config(config_path: str = CONFIG_FILE) -> dict:
    """Loads the product configuration schema."""
    # Support running tests/scripts inside the worker directory
    if not os.path.exists(config_path) and not config_path.startswith("/"):
        parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", config_path))
        if os.path.exists(os.path.dirname(parent_path)):
            config_path = parent_path

    # Fallback to example file if the direct config is missing
    if not os.path.exists(config_path) and config_path.endswith(".json"):
        example_path = config_path.replace(".json", ".example.json")
        if os.path.exists(example_path):
            config_path = example_path

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


def load_config_by_pdf_id(pdf_id: str, config_dir: str = "./config") -> dict:
    """
    Finds and loads the product configuration JSON that matches the given pdf_id.
    First checks outputs/assignment_cache.json for association, then scans config_dir files.
    Falls back to loading config/health_and_accident_insurance.json if not found.
    """
    from src.blue_table_tools.cache import get_product_config_name
    
    # Resolve correct paths when running inside the worker subfolder
    if not os.path.exists(config_dir):
        parent_config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", config_dir))
        if os.path.exists(parent_config_dir):
            config_dir = parent_config_dir

    # 1. Try to find the config file associated in assignment_cache
    config_name = get_product_config_name(pdf_id)
    if config_name:
        path = os.path.join(config_dir, config_name)
        if not os.path.exists(path) and path.endswith(".json"):
            example_path = path.replace(".json", ".example.json")
            if os.path.exists(example_path):
                path = example_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # 2. Scan the config directory for a matching pdf_id field
    if pdf_id and os.path.exists(config_dir):
        for filename in sorted(os.listdir(config_dir)):
            if filename.endswith(".json"):
                path = os.path.join(config_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if cfg.get("pdf_id") == pdf_id:
                            return cfg
                except Exception:
                    pass

    # 3. Fallback to default
    default_path = os.path.join(config_dir, "health_and_accident_insurance.json")
    if not os.path.exists(default_path):
        default_path = os.path.join(config_dir, "health_and_accident_insurance.example.json")
    if os.path.exists(default_path):
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Fallback to the first available json configuration file if default doesn't exist
    if os.path.exists(config_dir):
        json_files = sorted([f for f in os.listdir(config_dir) if f.endswith(".json")])
        if json_files:
            path = os.path.join(config_dir, json_files[0])
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
            
    return {}


def map_customer_data_to_pdf(customer_data: dict, config: dict, field_mappings: dict = None) -> dict:
    """
    Maps standard customer data fields to physical PDF AcroForm field values based on schema.
    Handles split fields like DOB.
    """
    import re
    pdf_values = {}
    if field_mappings is None:
        field_mappings = config.get("field_mappings", {})

    for pdf_field, mapping in field_mappings.items():
        if isinstance(mapping, dict):
            bt_key = mapping.get("bt_key")
            label = mapping.get("label", "").upper()
        else:
            bt_key = mapping
            label = ""

        if not bt_key or bt_key not in customer_data:
            continue

        value = customer_data[bt_key]
        if value is None:
            value = ""

        # Handle date parts for DOB fields
        if "dob" in bt_key or "date" in bt_key:
            date_str = str(value)
            part = None
            if "DAY" in label or "(DD)" in label:
                part = "DD"
            elif "MONTH" in label or "(MM)" in label:
                part = "MM"
            elif "YEAR" in label or "(YYYY)" in label:
                part = "YYYY"
            else:
                # Fallback: check if there are multiple fields mapped to this bt_key
                sibling_fields = []
                for f, m in field_mappings.items():
                    k = m.get("bt_key") if isinstance(m, dict) else m
                    if k == bt_key:
                        sibling_fields.append(f)
                
                if len(sibling_fields) > 1:
                    def get_num(name):
                        nums = re.findall(r"\d+", name)
                        return int(nums[0]) if nums else 0
                    sibling_fields.sort(key=get_num)
                    try:
                        idx = sibling_fields.index(pdf_field)
                        if idx == 0:
                            part = "DD"
                        elif idx == 1:
                            part = "MM"
                        elif idx == 2:
                            part = "YYYY"
                    except ValueError:
                        pass
            
            if part:
                pdf_values[pdf_field] = parse_date_part(date_str, part)
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
    using the config schema and assignment mapping, and returns a pre-filled PDF as a BytesIO stream.
    """
    # Load input PDF
    if isinstance(input_pdf, str):
        reader = PdfReader(input_pdf)
    else:
        input_pdf.seek(0)
        reader = PdfReader(input_pdf)

    from src.pdf_processor.utils.pdf_info import get_pdf_file_id
    pdf_id = get_pdf_file_id(reader)

    # Load config dynamically by matching the pdf_id
    config = load_config_by_pdf_id(pdf_id)
    
    # Load assignment mappings from assignment_cache.json
    from src.blue_table_tools.cache import load_cache
    field_mappings = load_cache(pdf_id)

    pdf_values = map_customer_data_to_pdf(customer_data, config, field_mappings)

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
