import sys
import threading
import os
import json
import pytest
from pathlib import Path

# Fix sys.path to allow imports from src/
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))

from blue_table_tools.cache import save_cache, load_cache, get_product_config_name
from pdf_processor.engine import update_pdf_registry

TEST_CACHE_FILE = "outputs/test_assignment_cache.json"
TEST_REGISTRY_FILE = "outputs/test_pdf_registry.json"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: ensure outputs directory exists
    os.makedirs("outputs", exist_ok=True)
    # Clear existing test files
    if os.path.exists(TEST_CACHE_FILE):
        os.remove(TEST_CACHE_FILE)
    if os.path.exists(TEST_REGISTRY_FILE):
        os.remove(TEST_REGISTRY_FILE)
    yield
    # Teardown: clear test files
    if os.path.exists(TEST_CACHE_FILE):
        os.remove(TEST_CACHE_FILE)
    if os.path.exists(TEST_REGISTRY_FILE):
        os.remove(TEST_REGISTRY_FILE)

def test_concurrent_cache_access():
    num_threads = 10
    num_iterations = 50
    pdf_id = "test_pdf_123"

    def worker_task(thread_id):
        for i in range(num_iterations):
            # Concurrent write
            mapping = {f"field_{thread_id}_{i}": f"value_{thread_id}_{i}"}
            save_cache(pdf_id, mapping, cache_path=TEST_CACHE_FILE)

            # Concurrent read
            cached = load_cache(pdf_id, cache_path=TEST_CACHE_FILE)
            assert isinstance(cached, dict)

            # Concurrent config name read
            config_name = get_product_config_name(pdf_id, cache_path=TEST_CACHE_FILE)
            # It might be None if no save has completed yet for this ID,
            # but in our loop we just saved it. However, it might be None if another
            # thread just wiped the file or something (which shouldn't happen with locks).
            # save_cache sets a default if missing.
            assert config_name is not None

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_task, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Final verification
    with open(TEST_CACHE_FILE, "r") as f:
        data = json.load(f)
        assert pdf_id in data
        assert "field_mappings" in data[pdf_id]

def test_concurrent_registry_access():
    # Find a PDF in the parent resources directory
    pdf_path = "../resources/OriginalApplication.pdf"
    if not os.path.exists(pdf_path):
         pdf_path = "resources/OriginalApplication.pdf" # try from root
         if not os.path.exists(pdf_path):
            pytest.skip(f"OriginalApplication.pdf not found at {pdf_path}")

    num_threads = 5
    num_iterations = 10

    def worker_task():
        for _ in range(num_iterations):
            update_pdf_registry(pdf_path, registry_path=TEST_REGISTRY_FILE)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_task)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Final verification
    with open(TEST_REGISTRY_FILE, "r") as f:
        data = json.load(f)
        assert len(data) > 0
