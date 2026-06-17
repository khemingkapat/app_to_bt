import sys
import os
import unittest
from datetime import datetime, timezone
from io import BytesIO

# Add the signature_gateway directory and project root to path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_sg_dir = os.path.abspath(os.path.join(_current_dir, ".."))
_project_root = os.path.abspath(os.path.join(_sg_dir, ".."))

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _sg_dir not in sys.path:
    sys.path.insert(0, _sg_dir)

import vault

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

if __name__ == "__main__":
    unittest.main()
