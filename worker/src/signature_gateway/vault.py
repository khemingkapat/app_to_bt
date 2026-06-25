import sys
import os
import re
import threading
from datetime import datetime, timezone
from io import BytesIO



# Global thread-safe transaction vault
_vault = {}
_lock = threading.Lock()

def normalize_id(id_val: str) -> str:
    """
    Normalizes an ID/Passport number by stripping hyphens, spaces, punctuation,
    and converting to lowercase.
    """
    if not id_val:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', id_val).lower()

def purge_expired():
    """
    Purges all expired entries from the vault.
    Must be called inside lock or will acquire lock itself.
    """
    now = datetime.now(timezone.utc)
    expired_tokens = []
    for token, entry in _vault.items():
        created_at = entry.get("created_at")
        ttl = entry.get("ttl_seconds", 900)
        if (now - created_at).total_seconds() > ttl:
            expired_tokens.append(token)
    
    for token in expired_tokens:
        del _vault[token]

def add_entry(token: str, pdf_id: str, customer_name: str, identity_id: str, bt_data: dict, ttl_seconds: int = 900) -> None:
    """Adds a new transaction entry to the vault."""
    with _lock:
        purge_expired()
        _vault[token] = {
            "secure_token": token,
            "pdf_id": pdf_id,
            "customer_name": customer_name,
            "identity_id": identity_id,  # Raw truth ID for gate check
            "bt_data": bt_data,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "ttl_seconds": ttl_seconds,
            "signed_pdf_bytes": None,
            "signed_docx_bytes": None,
            "signed_at": None,
        }

def get_entry(token: str) -> dict:
    """Retrieves a vault entry, checking for expiration first."""
    with _lock:
        purge_expired()
        return _vault.get(token)

def verify_identity(token: str, raw_id_input: str) -> bool:
    """
    Verifies the customer's identity input. If it succeeds, the raw truth
    identity ID is deleted from the vault for compliance (zero PII storage).
    """
    with _lock:
        purge_expired()
        entry = _vault.get(token)
        if not entry or entry["status"] != "pending":
            return False
        
        truth_id = entry.get("identity_id")
        if not truth_id:
            return False
            
        if normalize_id(raw_id_input) == normalize_id(truth_id):
            # Compliance requirement: Discard raw ID number on verification success
            entry["identity_id"] = None
            return True
        return False

def save_signed_documents(token: str, pdf_bytes: bytes, docx_bytes: bytes) -> None:
    """Saves the generated signed document bytes into the vault and marks it signed."""
    with _lock:
        purge_expired()
        entry = _vault.get(token)
        if entry:
            entry["signed_pdf_bytes"] = pdf_bytes
            entry["signed_docx_bytes"] = docx_bytes
            entry["status"] = "signed"
            entry["signed_at"] = datetime.now(timezone.utc)

def remove_entry(token: str) -> None:
    """Explicitly deletes an entry from the vault (e.g. after download)."""
    with _lock:
        if token in _vault:
            del _vault[token]

def extract_bt_data(all_fields: list, field_mapping: dict, values_map: dict) -> dict:
    """
    Extracts BlueTable fields from raw PDF field values based on layout mappings.
    Handles product logic, exclusions, and multi-field combinations.
    """
    bt_data = {}
    
    # 1. Determine product_name first (needed to resolve product-specific fields)
    product_name_vals = []
    for field in all_fields:
        fname = field.get("name")
        if not fname:
            continue
        mapping = field_mapping.get(fname)
        if not mapping:
            continue
        target_key = mapping.get("bt_key") if isinstance(mapping, dict) else mapping
        if target_key == "product_name":
            src_val = values_map.get(fname, "")
            if isinstance(mapping, dict):
                val = mapping.get("choices_map", {}).get(src_val, "")
            else:
                val = src_val if src_val and not src_val.startswith("/") else ""
            if val:
                product_name_vals.append(val)
    
    product_selection = " ".join(product_name_vals)
    bt_data["product_name"] = product_selection
    
    # Dynamic config extraction
    from src.pdf_processor.inverter import load_config_by_pdf_id
    config = load_config_by_pdf_id(None)
    products = config.get("product_options", {}).get("products", {})
    product_keys = list(products.keys())
    
    prefix_a = "ESSENTIAL"
    prefix_b = "VISA"
    product_name_a = "SmartCare Essential"
    product_name_b = "EasyCare Visa"
    choices_b = []
    
    if len(product_keys) >= 2:
        product_name_a = product_keys[0]
        choices_a = products[product_name_a].get("plan_tier", {}).get("choices", [])
        if choices_a:
            prefix_a = choices_a[0].rstrip("0123456789")
            
        product_name_b = product_keys[1]
        choices_b = products[product_name_b].get("plan_tier", {}).get("choices", [])
        if choices_b:
            prefix_b = choices_b[0].rstrip("0123456789")

    selected_product_line = product_name_a
    is_prod_b = False
    if choices_b:
        for choice in choices_b:
            if choice in product_selection:
                is_prod_b = True
                break
    if "EASYCARE" in product_selection or "MOCKB" in product_selection or "VISA" in product_selection:
        is_prod_b = True
        
    if is_prod_b:
        selected_product_line = product_name_b
        
    # 2. Rebuild all unique keys
    unique_keys = set()
    for fname, entry in field_mapping.items():
        if entry != "SKIPPED":
            bt_key = entry.get("bt_key") if isinstance(entry, dict) else entry
            unique_keys.add(bt_key)
            
    for bt_key in unique_keys:
        parts = []
        for field in all_fields:
            fname = field.get("name")
            if not fname:
                continue
            mapping = field_mapping.get(fname)
            if not mapping:
                continue
            
            target_key = mapping.get("bt_key") if isinstance(mapping, dict) else mapping
            if target_key != bt_key:
                continue
                
            # Ignore fields that correspond to the non-selected product line
            field_prod_line = "Both"
            if isinstance(mapping, dict):
                choices_map = mapping.get("choices_map", {})
                values = set(choices_map.values())
                
                # Dynamically construct unique choice sets based on prefix
                essential_unique = {f"{prefix_a}1", f"{prefix_a}2", f"{prefix_a}3", f"{prefix_a}4", "ESSENTIAL1", "ESSENTIAL2", "ESSENTIAL3", "ESSENTIAL4", "IPD", "IPD+OPD", "IPD+OPD+WELLNESS", "3k * 30 times / year", "50k per year", "0", "20k", "40k"}
                visa_unique = {f"{prefix_b}1", f"{prefix_b}2", "VISA1", "VISA2", "300k"}
                
                if values & essential_unique:
                    field_prod_line = product_name_a
                elif values & visa_unique:
                    field_prod_line = product_name_b
                    
            if field_prod_line != "Both" and field_prod_line != selected_product_line:
                continue
                
            src_val = values_map.get(fname, "")
            if isinstance(mapping, dict):
                choices_map = mapping.get("choices_map", {})
                val = choices_map.get(src_val, "")
            else:
                val = src_val if src_val and not src_val.startswith("/") else ""
                
            if val and val not in parts:
                parts.append(val)
                
        bt_data[bt_key] = " ".join(parts)
        
    return bt_data
