import sys
from pathlib import Path
import pytest
import grpc
from concurrent import futures
import time

# Setup paths
worker_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(worker_dir))
sys.path.insert(0, str(worker_dir / "src"))

from proto import document_pb2
from proto import document_pb2_grpc
from src.server import DocumentServiceServicer

@pytest.fixture(scope="module")
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    document_pb2_grpc.add_DocumentServiceServicer_to_server(
        DocumentServiceServicer(), server
    )
    port = server.add_insecure_port('[::]:0') # Use any available port
    server.start()
    yield f'localhost:{port}'
    server.stop(0)

@pytest.fixture(scope="module")
def grpc_stub(grpc_server):
    with grpc.insecure_channel(grpc_server) as channel:
        yield document_pb2_grpc.DocumentServiceStub(channel)

def test_process_pdf_integration(grpc_stub):
    # Load a real PDF from the resources directory
    repo_root = Path(__file__).resolve().parent.parent.parent
    pdf_path = repo_root / "resources" / "OriginalApplication.pdf"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    request = document_pb2.ProcessPdfRequest(pdf_bytes=pdf_bytes)
    response = grpc_stub.ProcessPdf(request)

    # Verify we get a valid PDF ID (SHA-256 hash usually)
    assert len(response.pdf_id) > 0
    assert response.pdf_id != "mock-pdf-id"

    # Verify we got some extracted values
    # OriginalApplication.pdf should have form fields
    assert len(response.values) > 0

    # Verify registry_json is valid JSON and contains structural data
    import json
    registry = json.loads(response.registry_json)
    assert response.pdf_id in registry
    assert "pages" in registry[response.pdf_id]
    assert "fields" in registry[response.pdf_id]

def test_generate_pdf_integration(grpc_stub):
    # Load a real PDF from the resources directory
    repo_root = Path(__file__).resolve().parent.parent.parent
    pdf_path = repo_root / "resources" / "OriginalApplication.pdf"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Form data mapping to fields in OriginalApplication.pdf
    form_data = {
        "Full Name": "John Doe",
        "Email": "john.doe@example.com"
    }

    request = document_pb2.GeneratePdfRequest(pdf_bytes=pdf_bytes, form_data=form_data)
    response = grpc_stub.GeneratePdf(request)

    assert len(response.pdf_bytes) > 0
    assert response.pdf_bytes.startswith(b"%PDF-")

def test_generate_docx_integration(grpc_stub):
    # Create a minimal DOCX in memory
    from docx import Document
    from io import BytesIO

    doc = Document()
    doc.add_heading('Test Document', 0)
    doc.add_table(rows=2, cols=2) # Add a table as the generator expects tables

    docx_stream = BytesIO()
    doc.save(docx_stream)
    docx_bytes = docx_stream.getvalue()

    request = document_pb2.GenerateDocxRequest(docx_bytes=docx_bytes, form_data={"name": "John Doe"})
    response = grpc_stub.GenerateDocx(request)

    assert len(response.docx_bytes) > 0
    # DOCX is a zip file, should start with PK
    assert response.docx_bytes.startswith(b"PK")

def test_stamp_signature_mock(grpc_stub):
    pdf_content = b"fake-pdf-content"
    request = document_pb2.StampSignatureRequest(
        pdf_bytes=pdf_content,
        signature_image_bytes=b"fake-sig",
        pdf_id="some-id",
        registry_json="{}",
        cache_mapping_json="{}"
    )
    response = grpc_stub.StampSignature(request)
    assert response.pdf_bytes == pdf_content
