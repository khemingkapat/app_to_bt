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

class DocumentServiceServicer(document_pb2_grpc.DocumentServiceServicer):
    """
    Mock implementation of DocumentService for initial scaffolding and testing.
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
        return document_pb2.GeneratePdfResponse(
            pdf_bytes=request.pdf_bytes
        )

    def GenerateDocx(self, request, context):
        print("Received GenerateDocx request")
        return document_pb2.GenerateDocxResponse(
            docx_bytes=request.docx_bytes
        )

    def StampSignature(self, request, context):
        print("Received StampSignature request")
        return document_pb2.StampSignatureResponse(
            pdf_bytes=request.pdf_bytes
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
