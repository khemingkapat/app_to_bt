import sys
import os
import json
from io import BytesIO
from pathlib import Path
from concurrent import futures
import grpc
import signal
import resource

# Add worker directory to sys.path to allow importing the generated proto package
# and add worker/src to sys.path to follow the project structure
worker_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(worker_dir))
sys.path.insert(0, str(worker_dir / "src"))

from proto import document_pb2
from proto import document_pb2_grpc
from pdf_processor.engine import process_pdf
from pdf_processor.inverter import fill_acroform_pdf
from blue_table_tools.docx_generator import fill_blue_table_docx
from signature_gateway.pdf_stamping import stamp_signature_on_pdf
from pdf_processor.utils.pdf_info import get_pdf_file_id
from pdf_processor.inverter import load_config_by_pdf_id
from blue_table_tools.cache import load_cache
from pypdf import PdfReader

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024

class DocumentServiceServicer(document_pb2_grpc.DocumentServiceServicer):
    """
    Implementation of DocumentService for processing and generating documents.
    """
    def ProcessPdf(self, request, context):
        print("Received ProcessPdf request")
        if len(request.pdf_bytes) > MAX_PAYLOAD_SIZE:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Payload exceeds 5MB limit")

        pdf_file = BytesIO(request.pdf_bytes)
        pdf_id, registry_dict, values_dict = process_pdf(pdf_file)

        return document_pb2.ProcessPdfResponse(
            pdf_id=pdf_id,
            values=values_dict,
            registry_json=json.dumps(registry_dict)
        )

    def GeneratePdf(self, request, context):
        print("Received GeneratePdf request")
        if len(request.pdf_bytes) > MAX_PAYLOAD_SIZE:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Payload exceeds 5MB limit")

        pdf_file = BytesIO(request.pdf_bytes)

        pdf_id = get_pdf_file_id(PdfReader(pdf_file))
        pdf_file.seek(0)

        config = load_config_by_pdf_id(pdf_id)
        field_mappings = load_cache(pdf_id)

        # request.form_data is a gRPC MapComposite object, which behaves like a dict
        output_pdf = fill_acroform_pdf(
            pdf_file,
            request.form_data,
            config=config,
            field_mappings=field_mappings
        )
        return document_pb2.GeneratePdfResponse(
            pdf_bytes=output_pdf.getvalue()
        )

    def GenerateDocx(self, request, context):
        print("Received GenerateDocx request")
        if len(request.docx_bytes) > MAX_PAYLOAD_SIZE:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Payload exceeds 5MB limit")

        docx_file = BytesIO(request.docx_bytes)
        # Convert gRPC map to a plain dict just in case the generator expects it
        data = dict(request.form_data)

        pdf_id = data.get("pdf_id")
        config = load_config_by_pdf_id(pdf_id)

        output_docx = fill_blue_table_docx(docx_file, data, config=config)
        return document_pb2.GenerateDocxResponse(
            docx_bytes=output_docx.getvalue()
        )

    def StampSignature(self, request, context):
        print("Received StampSignature request")
        if len(request.pdf_bytes) > MAX_PAYLOAD_SIZE or len(request.signature_image_bytes) > MAX_PAYLOAD_SIZE:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Payload exceeds 5MB limit")

        registry_json = request.registry_json.strip() if request.registry_json else None
        registry_dict = json.loads(registry_json) if registry_json else None

        cache_mapping_json = request.cache_mapping_json.strip() if request.cache_mapping_json else None
        cache_mapping_dict = json.loads(cache_mapping_json) if cache_mapping_json else None

        stamped_pdf = stamp_signature_on_pdf(
            pdf_bytes=request.pdf_bytes,
            sig_img_bytes=request.signature_image_bytes,
            pdf_id=request.pdf_id,
            registry_dict=registry_dict,
            cache_mapping=cache_mapping_dict
        )

        return document_pb2.StampSignatureResponse(
            pdf_bytes=stamped_pdf
        )

def configure_resource_limits():
    """
    Configures process-level resource limits.
    """
    # Configure a soft address space memory limit of 512MB and a hard limit of 1GB
    soft_limit = 512 * 1024 * 1024
    hard_limit = 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))

def serve():
    """
    Starts the gRPC server and listens on port 50051.
    """
    configure_resource_limits()

    # Increase gRPC message size limits to 10MB to allow 5MB application-level validation
    options = [
        ('grpc.max_send_message_length', 10 * 1024 * 1024),
        ('grpc.max_receive_message_length', 10 * 1024 * 1024)
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), options=options)
    document_pb2_grpc.add_DocumentServiceServicer_to_server(
        DocumentServiceServicer(), server
    )

    port = "50051"
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Worker gRPC server started, listening on {port}")

    def stop_server(signum, frame):
        print(f"Received signal {signum}, stopping server...")
        server.stop(0)

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    server.wait_for_termination()

if __name__ == "__main__":
    serve()
