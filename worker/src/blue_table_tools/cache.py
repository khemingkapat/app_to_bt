import json
import os
import shutil
from src.pdf_processor.engine import IO_LOCK

def ensure_cache_file(cache_path: str):
    """Ensures that the cache_path file exists, copying from .example.json if missing."""
    with IO_LOCK:
        # Resolve parent path when running inside worker/ directory
        if not os.path.exists(cache_path) and not cache_path.startswith("/"):
            parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", cache_path))
            if os.path.exists(os.path.dirname(parent_path)):
                cache_path = parent_path

        if not os.path.exists(cache_path):
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write("{}")
            except Exception:
                pass


def load_cache(pdf_id: str, cache_path: str = "outputs/assignment_cache.json") -> dict:
    """Loads the assignment cache (field_mappings) for a specific pdf_id."""
    if not pdf_id:
        return {}

    with IO_LOCK:
        # Resolve parent path when running inside worker/ directory
        if not os.path.exists(cache_path) and not cache_path.startswith("/"):
            parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", cache_path))
            if os.path.exists(os.path.dirname(parent_path)):
                cache_path = parent_path

        ensure_cache_file(cache_path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    global_cache = json.load(f)
                    entry = global_cache.get(pdf_id, {})
                    if isinstance(entry, dict) and "field_mappings" in entry:
                        return entry.get("field_mappings", {})
                    # Backward-compatibility for old flat format
                    return entry if isinstance(entry, dict) else {}
            except Exception:
                return {}
        return {}


def save_cache(pdf_id: str, field_mapping: dict, cache_path: str = "outputs/assignment_cache.json"):
    """Saves the assignment cache incrementally, preserving the product_config link."""
    if not pdf_id:
        return

    with IO_LOCK:
        # Resolve parent path when running inside worker/ directory
        if not os.path.exists(cache_path) and not cache_path.startswith("/"):
            parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", cache_path))
            if os.path.exists(os.path.dirname(parent_path)):
                cache_path = parent_path

        ensure_cache_file(cache_path)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        global_cache = {}
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                try:
                    global_cache = json.load(f)
                except Exception:
                    pass

        entry = global_cache.get(pdf_id, {})
        if not isinstance(entry, dict) or "field_mappings" not in entry:
            # If it was flat, extract product config if possible, or use default
            prod_config = "health_and_accident_insurance.json"
            if isinstance(entry, dict) and "product_config" in entry:
                prod_config = entry["product_config"]
            entry = {
                "product_config": prod_config,
                "field_mappings": {}
            }

        entry["field_mappings"] = field_mapping
        global_cache[pdf_id] = entry

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(global_cache, f, indent=4, ensure_ascii=False)


def get_product_config_name(pdf_id: str, cache_path: str = "outputs/assignment_cache.json") -> str:
    """Gets the product config filename associated with a pdf_id, or None if not found."""
    if not pdf_id:
        return None

    with IO_LOCK:
        # Resolve parent path when running inside worker/ directory
        if not os.path.exists(cache_path) and not cache_path.startswith("/"):
            parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", cache_path))
            if os.path.exists(os.path.dirname(parent_path)):
                cache_path = parent_path

        ensure_cache_file(cache_path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    global_cache = json.load(f)
                    entry = global_cache.get(pdf_id, {})
                    if isinstance(entry, dict):
                        return entry.get("product_config")
            except Exception:
                pass
        return None
