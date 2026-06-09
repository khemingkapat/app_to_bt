import json
import os

pdf_id = "test_pdf"
cache_path = os.path.join("outputs", f"{pdf_id}_assignment.json")
cache = {"field1": "name", "field2": "SKIPPED"}
os.makedirs("outputs", exist_ok=True)
with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(cache, f)

print(os.path.exists(cache_path))
