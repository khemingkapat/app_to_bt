import json
import os

def load_cache(pdf_id: str, cache_path: str = "outputs/assignment_cache.json") -> dict:
    """Loads the assignment cache for a specific pdf_id."""
    if not pdf_id:
        return {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                global_cache = json.load(f)
                return global_cache.get(pdf_id, {})
        except Exception:
            return {}
    return {}


def save_cache(pdf_id: str, field_mapping: dict, cache_path: str = "outputs/assignment_cache.json"):
    """Saves the assignment cache incrementally."""
    if not pdf_id:
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    global_cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                global_cache = json.load(f)
            except Exception:
                pass

    global_cache[pdf_id] = field_mapping

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(global_cache, f, indent=4, ensure_ascii=False)
