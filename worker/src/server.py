import sys
import os
import json
from io import BytesIO
from pathlib import Path
from concurrent import futures
import grpc
import signal

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

class DocumentServiceServicer(document_pb2_grpc.DocumentServiceServicer):
    """
    Implementation of DocumentService for processing and generating documents.
    """
    def ProcessPdf(self, request, context):
        print("Received ProcessPdf request")
        pdf_file = BytesIO(request.pdf_bytes)
        pdf_id, registry_dict, values_dict = process_pdf(pdf_file)

        return document_pb2.ProcessPdfResponse(
            pdf_id=pdf_id,
            values=values_dict,
            registry_json=json.dumps(registry_dict)
        )

    def GeneratePdf(self, request, context):
        print("Received GeneratePdf request")
        pdf_file = BytesIO(request.pdf_bytes)
        # request.form_data is a gRPC MapComposite object, which behaves like a dict
        output_pdf = fill_acroform_pdf(pdf_file, request.form_data)
        return document_pb2.GeneratePdfResponse(
            pdf_bytes=output_pdf.getvalue()
        )

    def GenerateDocx(self, request, context):
        print("Received GenerateDocx request")
        docx_file = BytesIO(request.docx_bytes)
        # Convert gRPC map to a plain dict just in case the generator expects it
        output_docx = fill_blue_table_docx(docx_file, dict(request.form_data))
        return document_pb2.GenerateDocxResponse(
            docx_bytes=output_docx.getvalue()
        )

    def StampSignature(self, request, context):
        print("Received StampSignature request")

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

def serve():
    """
    Starts the gRPC server and listens on port 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
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
