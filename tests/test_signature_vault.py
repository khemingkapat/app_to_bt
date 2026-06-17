import sys
import os
import unittest
from datetime import datetime, timezone
from io import BytesIO

# Import vault from the package
from src.signature_gateway import vault

class TestSignatureGatewayVault(unittest.TestCase):
    def setUp(self):
        # Clear vault entries before each test
        vault._vault.clear()

    def test_normalize_id(self):
        self.assertEqual(vault.normalize_id("1-2345-67890-12-3"), "1234567890123")
        self.assertEqual(vault.normalize_id("A.123-456 B"), "a123456b")
        self.assertEqual(vault.normalize_id(""), "")
        self.assertEqual(vault.normalize_id(None), "")

    def test_add_and_get_entry(self):
        token = "test_token_123"
        vault.add_entry(
            token=token,
            pdf_id="test_pdf",
            customer_name="John Doe",
            identity_id="123456789",
            bt_data={"name": "John Doe", "id_card_no": "123456789"},
            ttl_seconds=60
        )
        
        entry = vault.get_entry(token)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["customer_name"], "John Doe")
        self.assertEqual(entry["identity_id"], "123456789")
        self.assertEqual(entry["status"], "pending")

    def test_verify_identity_success_clears_pii(self):
        token = "test_token_456"
        vault.add_entry(
            token=token,
            pdf_id="test_pdf",
            customer_name="Jane Doe",
            identity_id="987-654-321",
            bt_data={"name": "Jane Doe", "id_card_no": "987-654-321"},
            ttl_seconds=60
        )
        
        # Verify with formatting differences
        result = vault.verify_identity(token, "987654321 ")
        self.assertTrue(result)
        
        # Verify that the raw truth ID has been deleted for compliance
        entry = vault.get_entry(token)
        self.assertIsNone(entry["identity_id"])

    def test_verify_identity_fail(self):
        token = "test_token_789"
        vault.add_entry(
            token=token,
            pdf_id="test_pdf",
            customer_name="Bob Smith",
            identity_id="555-555",
            bt_data={"name": "Bob Smith", "id_card_no": "555-555"},
            ttl_seconds=60
        )
        
        result = vault.verify_identity(token, "12345")
        self.assertFalse(result)
        
        # Verify that the raw truth ID is still retained after a failure
        entry = vault.get_entry(token)
        self.assertEqual(entry["identity_id"], "555-555")

    def test_save_signed_documents(self):
        token = "test_token_signed"
        vault.add_entry(
            token=token,
            pdf_id="test_pdf",
            customer_name="Alice Brown",
            identity_id="111-222",
            bt_data={"name": "Alice Brown", "id_card_no": "111-222"},
            ttl_seconds=60
        )
        
        pdf_bytes = b"mock_pdf_bytes"
        docx_bytes = b"mock_docx_bytes"
        vault.save_signed_documents(token, pdf_bytes, docx_bytes)
        
        entry = vault.get_entry(token)
        self.assertEqual(entry["status"], "signed")
        self.assertEqual(entry["signed_pdf_bytes"], pdf_bytes)
        self.assertEqual(entry["signed_docx_bytes"], docx_bytes)
        self.assertIsNotNone(entry["signed_at"])

    def test_remove_entry(self):
        token = "test_token_to_remove"
        vault.add_entry(
            token=token,
            pdf_id="test_pdf",
            customer_name="Charlie Green",
            identity_id="333",
            bt_data={"name": "Charlie Green"},
            ttl_seconds=60
        )
        
        vault.remove_entry(token)
        self.assertIsNone(vault.get_entry(token))

    def test_stamp_signature_on_pdf_dynamic_alignment(self):
        from src.signature_gateway.pdf_stamping import stamp_signature_on_pdf
        from PIL import Image
        import fitz
        
        # Create a blank 5-page document (since Text94 defaults to page 5)
        doc = fitz.open()
        for _ in range(5):
            doc.new_page()
        pdf_bytes = doc.write()
        
        # Create a mock 10x10 PNG
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        sig_img_bytes = img_bytes.getvalue()
        
        # Registry mapping with a custom signature field
        registry_dict = {
            "test_pdf": {
                "fields": [
                    {
                        "name": "CustomSignatureField",
                        "page": 2,
                        "coords": {
                            "canvas_top": 100,
                            "canvas_bottom": 120,
                            "x0": 50,
                            "x1": 150
                        }
                    }
                ]
            }
        }
        
        # Case 1: Mapped signature field (CustomSignatureField)
        cache_mapping = {
            "CustomSignatureField": "signature",
            "Text2": "name"
        }
        
        # Stamp it
        output_pdf = stamp_signature_on_pdf(
            pdf_bytes=pdf_bytes,
            sig_img_bytes=sig_img_bytes,
            pdf_id="test_pdf",
            registry_dict=registry_dict,
            cache_mapping=cache_mapping
        )
        self.assertIsNotNone(output_pdf)

if __name__ == "__main__":
    unittest.main()
