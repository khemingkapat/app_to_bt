from pypdf import PdfReader

# Load your structured PDF application form
reader = PdfReader("resources/FilledApplication.pdf")

# Get all interactive form fields
fields = reader.get_fields()

# Print every field name found in the document
if fields is not None:
    for field_name, value in fields.items():
        print(f"{field_name} : {value}")
